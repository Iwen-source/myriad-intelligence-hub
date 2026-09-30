#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
训练脚本 2/3：金属伪影检查 (Metal Artifact Detection & Segmentation) - 加速 & 可恢复版
============================================================================
改进点:
  1. 混合精度训练 (AMP)
  2. DataLoader 多线程 (num_workers=4) + pin_memory
  3. 自动保存/恢复检查点 (每10轮完整状态)
  4. 支持从中断处继续训练
============================================================================
"""

import os
import sys
import glob
import time
import logging
import argparse
import csv

import torch
import torch.nn as nn
import torch.optim as optim
from torch.cuda.amp import GradScaler, autocast
from torch.utils.data import DataLoader, Dataset

import numpy as np
import nibabel as nib
import pandas as pd
from tqdm import tqdm
from sklearn.model_selection import train_test_split

# MONAI 预处理
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd, ScaleIntensityd,
    Orientationd, Spacingd, ToTensord,
    RandFlipd, RandRotate90d, RandZoomd, RandAffined,
    SpatialPadd, CenterSpatialCropD,
)

# ─── 路径配置 ──────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)        # python/
_DATA_DIR = os.path.join(_PROJECT_DIR, "..", "data", "ct", "cq500")

VOLUMES_DIR = os.path.join(_DATA_DIR, "volumes")
MASKS_DIR   = os.path.join(_DATA_DIR, "masks")
ANNOT_CSV   = os.path.join(_DATA_DIR, "artifact_annotations")

MODEL_OUTPUT_DIR = os.path.join(_PROJECT_DIR, "models")
os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)

OUTPUT_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, "logs_ct_artifact"))
LOG_DIR    = os.path.join(OUTPUT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ─── 日志 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "train_artifact.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# 1. 数据加载
# ═══════════════════════════════════════════════════════════════════════════
def collect_all_artifact_pairs():
    pairs = []
    vol_files = sorted(glob.glob(os.path.join(VOLUMES_DIR, "CQ500-CT-*.nii.gz")))
    mask_dict = {}
    for mf in sorted(glob.glob(os.path.join(MASKS_DIR, "CQ500-CT-*.nii.gz"))):
        mask_dict[os.path.basename(mf)] = mf

    for vf in vol_files:
        basename = os.path.basename(vf)
        if basename in mask_dict:
            pairs.append((vf, mask_dict[basename]))

    if os.path.isdir(ANNOT_CSV):
        csv_files = sorted(glob.glob(os.path.join(ANNOT_CSV, "*.csv")))
        for csv_f in csv_files:
            logger.info(f"  标注CSV: {os.path.basename(csv_f)}")

    logger.info(f"★ 总计: {len(pairs)} 对 CT+伪影掩码")
    return pairs


# ═══════════════════════════════════════════════════════════════════════════
# 2. 数据集类
# ═══════════════════════════════════════════════════════════════════════════
class CTArtifactDataset3D(Dataset):
    def __init__(self, pairs, target_spacing=(2.0, 2.0, 2.5),
                 target_size=(128, 128, 64), is_train=True):
        self.pairs = pairs
        self.is_train = is_train
        self.target_spacing = target_spacing
        self.target_size = target_size
        self.transform = self._build_transform()

    def _build_transform(self):
        common = [
            LoadImaged(keys=["image", "label"]),
            EnsureChannelFirstd(keys=["image", "label"]),
            ScaleIntensityd(keys=["image"], minv=0, maxv=1),
            Orientationd(keys=["image", "label"], axcodes="RAS"),
            Spacingd(keys=["image", "label"], pixdim=self.target_spacing,
                     mode=("bilinear", "nearest")),
            SpatialPadd(keys=["image", "label"], spatial_size=self.target_size),
            CenterSpatialCropD(keys=["image", "label"], roi_size=self.target_size),
        ]
        if self.is_train:
            aug = [
                RandFlipd(keys=["image", "label"], spatial_axis=[0, 1, 2], prob=0.5),
                RandRotate90d(keys=["image", "label"], spatial_axes=(0, 1), prob=0.5),
                RandZoomd(keys=["image", "label"], min_zoom=0.9, max_zoom=1.1, prob=0.5),
                RandAffined(keys=["image", "label"],
                            rotate_range=(-0.1, 0.1), shear_range=(-0.05, 0.05),
                            translate_range=5, prob=0.3),
            ]
            return Compose(common + aug + [ToTensord(keys=["image", "label"])])
        else:
            return Compose(common + [ToTensord(keys=["image", "label"])])

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        ct_path, mask_path = self.pairs[idx]
        data = {"image": ct_path, "label": mask_path}
        data = self.transform(data)
        data["label"] = (data["label"] > 0.5).float()
        return data["image"], data["label"]


# ═══════════════════════════════════════════════════════════════════════════
# 3. 模型 (同原版)
# ═══════════════════════════════════════════════════════════════════════════
class DoubleConv3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch), nn.ReLU(inplace=True),
            nn.Conv3d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.conv(x)


class Down3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.pool = nn.MaxPool3d(2)
        self.conv = DoubleConv3D(in_ch, out_ch)

    def forward(self, x):
        return self.conv(self.pool(x))


class Up3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.up = nn.ConvTranspose3d(in_ch, in_ch // 2, 2, 2)
        self.conv = DoubleConv3D(in_ch, out_ch)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        d = x2.size(2) - x1.size(2)
        h = x2.size(3) - x1.size(3)
        w = x2.size(4) - x1.size(4)
        x1 = nn.functional.pad(x1, [w//2, w-w//2, h//2, h-h//2, d//2, d-d//2])
        return self.conv(torch.cat([x2, x1], dim=1))


class ArtifactUNet3D(nn.Module):
    def __init__(self, in_channels=1, out_channels=1, init_features=16):
        super().__init__()
        self.inc   = DoubleConv3D(in_channels, init_features)
        self.down1 = Down3D(init_features, init_features * 2)
        self.down2 = Down3D(init_features * 2, init_features * 4)
        self.down3 = Down3D(init_features * 4, init_features * 8)
        self.up1   = Up3D(init_features * 8, init_features * 4)
        self.up2   = Up3D(init_features * 4, init_features * 2)
        self.up3   = Up3D(init_features * 2, init_features)
        self.outc  = nn.Conv3d(init_features, out_channels, kernel_size=1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x = self.up1(x4, x3)
        x = self.up2(x, x2)
        x = self.up3(x, x1)
        return self.outc(x)


# ═══════════════════════════════════════════════════════════════════════════
# 4. 评估指标
# ═══════════════════════════════════════════════════════════════════════════
def dice_coef(pred, target, smooth=1e-6):
    p = pred.contiguous().view(-1)
    t = target.contiguous().view(-1)
    return (2.0 * (p * t).sum() + smooth) / (p.sum() + t.sum() + smooth)


def iou_score(pred, target, smooth=1e-6):
    p = pred.contiguous().view(-1)
    t = target.contiguous().view(-1)
    inter = (p * t).sum()
    return (inter + smooth) / (p.sum() + t.sum() - inter + smooth)


# ═══════════════════════════════════════════════════════════════════════════
# 5. 训练 / 验证 (支持混合精度)
# ═══════════════════════════════════════════════════════════════════════════
def train_epoch(model, loader, criterion, optimizer, scaler, device, epoch):
    model.train()
    total_loss = total_dice = 0
    num = len(loader)
    pbar = tqdm(loader, desc=f"E{epoch} Train", leave=False)
    for img, mask in pbar:
        img, mask = img.to(device, non_blocking=True), mask.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)

        with autocast():
            pred = model(img)
            loss = criterion(pred, mask)

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        bin_p = (torch.sigmoid(pred) > 0.5).float()
        d = dice_coef(bin_p, mask)
        total_loss += loss.item()
        total_dice += d.item()
        pbar.set_postfix(loss=loss.item(), dice=d.item())
    return total_loss / num, total_dice / num


def val_epoch(model, loader, criterion, device, epoch):
    model.eval()
    total_loss = total_dice = total_iou = 0
    num = len(loader)
    with torch.no_grad():
        pbar = tqdm(loader, desc=f"E{epoch} Val", leave=False)
        for img, mask in pbar:
            img, mask = img.to(device, non_blocking=True), mask.to(device, non_blocking=True)
            with autocast():
                pred = model(img)
                loss = criterion(pred, mask)
            bin_p = (torch.sigmoid(pred) > 0.5).float()
            total_loss += loss.item()
            total_dice += dice_coef(bin_p, mask).item()
            total_iou  += iou_score(bin_p, mask).item()
            pbar.set_postfix(loss=loss.item(), dice=dice_coef(bin_p, mask).item())
    return total_loss / num, total_dice / num, total_iou / num


# ═══════════════════════════════════════════════════════════════════════════
# 6. 检查点保存与恢复
# ═══════════════════════════════════════════════════════════════════════════
def save_checkpoint(epoch, model, optimizer, scheduler, best_dice, is_best=False):
    ckpt_path = os.path.join(MODEL_OUTPUT_DIR, f"artifact_checkpoint_epoch{epoch:04d}.pth")
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
        'best_dice': best_dice,
    }, ckpt_path)
    logger.info(f"检查点已保存: {ckpt_path}")
    if is_best:
        best_path = os.path.join(MODEL_OUTPUT_DIR, "ct_metal_unet.pth")
        torch.save(model.state_dict(), best_path)
        logger.info(f"最佳模型已保存 (Dice={best_dice:.4f}): {best_path}")


def load_latest_checkpoint(model, optimizer, scheduler, device):
    ckpt_files = glob.glob(os.path.join(MODEL_OUTPUT_DIR, "artifact_checkpoint_epoch*.pth"))
    if not ckpt_files:
        return 0, 0.0

    def get_epoch(f):
        basename = os.path.basename(f)
        try:
            return int(basename.split('_')[-1].split('.')[0])
        except:
            return 0
    latest = max(ckpt_files, key=get_epoch)
    epoch_num = get_epoch(latest)

    checkpoint = torch.load(latest, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
    best_dice = checkpoint.get('best_dice', 0.0)

    logger.info(f"恢复检查点: {latest} (epoch {epoch_num}, best_dice={best_dice:.4f})")
    return epoch_num, best_dice


# ═══════════════════════════════════════════════════════════════════════════
# 7. 主函数
# ═══════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="CT 金属伪影分割训练 (加速+可恢复)")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=1, help="批大小 (3D数据吃显存, 默认1; 12G+显存可试2~4)")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val_split", type=float, default=0.2)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--num_workers", type=int, default=0,
                        help="数据加载线程数 (3D数据吃内存, 默认0=单线程; 内存32G+可试2)")
    parser.add_argument("--resume", action="store_true", default=True, help="自动恢复检查点")
    args = parser.parse_args()

    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    logger.info(f"设备: {device}  (GPU可用: {torch.cuda.is_available()})")
    if device.type == 'cuda':
        logger.info(f"GPU型号: {torch.cuda.get_device_name(0)}")
        logger.info(f"显存总量: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    logger.info(f"配置: epochs={args.epochs}, batch={args.batch_size}, lr={args.lr}, "
                f"val_split={args.val_split}, num_workers={args.num_workers}")

    # ── 1. 数据 ──
    all_pairs = collect_all_artifact_pairs()
    if len(all_pairs) == 0:
        logger.error("未找到数据!")
        return

    train_pairs, val_pairs = train_test_split(all_pairs, test_size=args.val_split, random_state=42)
    logger.info(f"训练: {len(train_pairs)} | 验证: {len(val_pairs)}")

    # ── 2. Dataset & DataLoader (多线程) ──
    train_ds = CTArtifactDataset3D(train_pairs, is_train=True)
    val_ds   = CTArtifactDataset3D(val_pairs, is_train=False)
    use_workers = args.num_workers if args.num_workers >= 0 else 0
    if use_workers > 0:
        logger.warning(f"num_workers={use_workers}: 确保系统内存充足(≥32GB)")
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=use_workers, pin_memory=(use_workers==0),
        prefetch_factor=2 if use_workers > 0 else None,
        persistent_workers=(use_workers > 0)
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=use_workers, pin_memory=(use_workers==0),
        prefetch_factor=2 if use_workers > 0 else None,
        persistent_workers=(use_workers > 0)
    )

    # ── 3. 模型 ──
    model = ArtifactUNet3D(in_channels=1, out_channels=1).to(device)
    logger.info(f"参数量: {sum(p.numel() for p in model.parameters()):,}")

    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([3.0]).to(device))
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = GradScaler()

    # ── 4. 恢复检查点 ──
    start_epoch = 1
    best_dice = 0.0
    if args.resume:
        epoch_loaded, best_dice = load_latest_checkpoint(model, optimizer, scheduler, device)
        if epoch_loaded > 0:
            start_epoch = epoch_loaded + 1
            logger.info(f"从 epoch {start_epoch} 继续训练，当前最佳 Dice = {best_dice:.4f}")
        else:
            logger.info("未发现检查点，从头训练")

    # ── 5. CSV 日志 ──
    csv_path = os.path.join(LOG_DIR, "training_metrics.csv")
    file_exists = os.path.isfile(csv_path)
    csv_file = open(csv_path, "a", newline="")
    csv_writer = csv.writer(csv_file)
    if not file_exists:
        csv_writer.writerow(["epoch", "train_loss", "train_dice", "val_loss", "val_dice", "val_iou", "lr"])

    # ── 6. 训练循环 (带中断处理) ──
    logger.info("开始训练 (混合精度 + 中断恢复)")
    start_t = time.time()
    try:
        for epoch in range(start_epoch, args.epochs + 1):
            t_loss, t_dice = train_epoch(model, train_loader, criterion, optimizer, scaler, device, epoch)
            v_loss, v_dice, v_iou = val_epoch(model, val_loader, criterion, device, epoch)
            scheduler.step()
            lr_now = scheduler.get_last_lr()[0]

            logger.info(f"E{epoch:3d}/{args.epochs} | Train L:{t_loss:.4f} D:{t_dice:.4f} | "
                        f"Val L:{v_loss:.4f} D:{v_dice:.4f} IoU:{v_iou:.4f} | LR:{lr_now:.2e}")

            csv_writer.writerow([epoch, round(t_loss,4), round(t_dice,4),
                                 round(v_loss,4), round(v_dice,4), round(v_iou,4), lr_now])
            csv_file.flush()

            if v_dice > best_dice:
                best_dice = v_dice
                save_checkpoint(epoch, model, optimizer, scheduler, best_dice, is_best=True)

            if epoch % 10 == 0:
                save_checkpoint(epoch, model, optimizer, scheduler, best_dice, is_best=False)

            if device.type == 'cuda' and epoch % 5 == 0:
                torch.cuda.empty_cache()

    except KeyboardInterrupt:
        logger.warning("用户中断训练，紧急保存当前状态...")
        save_checkpoint(epoch, model, optimizer, scheduler, best_dice, is_best=False)
        raise
    except Exception as e:
        logger.error(f"训练异常: {e}")
        save_checkpoint(epoch, model, optimizer, scheduler, best_dice, is_best=False)
        raise
    finally:
        csv_file.close()
        final_ckpt = os.path.join(MODEL_OUTPUT_DIR, "artifact_checkpoint_final.pth")
        torch.save({
            'epoch': args.epochs,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'best_dice': best_dice,
        }, final_ckpt)
        logger.info(f"最终检查点: {final_ckpt}")

    total_t = time.time() - start_t
    logger.info(f"完成! {total_t:.0f}s ({total_t/60:.1f}min)")
    logger.info(f"最佳 Dice: {best_dice:.4f}")
    logger.info(f"模型: {os.path.join(MODEL_OUTPUT_DIR, 'ct_metal_unet.pth')}")
    logger.info(f"训练指标: {csv_path}")


if __name__ == "__main__":
    main()