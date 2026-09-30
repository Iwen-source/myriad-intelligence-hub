#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
训练脚本 3/3：CT报告分类器 (CT Report Classifier) - 加速 & 可恢复版
============================================================================
改进点:
  1. 混合精度训练 (AMP)
  2. DataLoader 多线程 + pin_memory
  3. 自动保存/恢复检查点 (每20轮完整状态)
  4. 支持从中断处继续训练
============================================================================
"""

import os
import sys
import glob
import json
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
import pandas as pd
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, classification_report

# MONAI 预处理
from monai.transforms import (
    Compose, LoadImaged, EnsureChannelFirstd, ScaleIntensityd,
    Orientationd, Spacingd, ToTensord,
    RandFlipd, RandRotate90d, RandZoomd,
    SpatialPadd, CenterSpatialCropD,
)

# ─── 路径配置 ──────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)        # python/
_DATA_DIR = os.path.join(_PROJECT_DIR, "..", "data", "ct", "cq500")

VOLUMES_DIR = os.path.join(_DATA_DIR, "volumes")
READS_CSV   = os.path.join(_DATA_DIR, "metadata", "reads.csv")
PROB_CSV    = os.path.join(_DATA_DIR, "metadata", "prediction_probabilities.csv")

MODEL_OUTPUT_DIR = os.path.join(_PROJECT_DIR, "models")
os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)

OUTPUT_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, "logs_ct_report"))
LOG_DIR    = os.path.join(OUTPUT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ─── 日志 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "train_classifier.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# 1. 数据加载与标签工程
# ═══════════════════════════════════════════════════════════════════════════
LABEL_PAIRS = [
    ("ICH", "R1:ICH", "R2:ICH", "R3:ICH"),
    ("IPH", "R1:IPH", "R2:IPH", "R3:IPH"),
    ("IVH", "R1:IVH", "R2:IVH", "R3:IVH"),
    ("SDH", "R1:SDH", "R2:SDH", "R3:SDH"),
    ("EDH", "R1:EDH", "R2:EDH", "R3:EDH"),
    ("SAH", "R1:SAH", "R2:SAH", "R3:SAH"),
    ("LeftBleed",  "R1:BleedLocation-Left",  "R2:BleedLocation-Left",  "R3:BleedLocation-Left"),
    ("RightBleed", "R1:BleedLocation-Right", "R2:BleedLocation-Right", "R3:BleedLocation-Right"),
    ("ChronicBleed", "R1:ChronicBleed", "R2:ChronicBleed", "R3:ChronicBleed"),
    ("Fracture",     "R1:Fracture",     "R2:Fracture",     "R3:Fracture"),
    ("CalvarialFracture",  "R1:CalvarialFracture",  "R2:CalvarialFracture",  "R3:CalvarialFracture"),
    ("OtherFracture", "R1:OtherFracture", "R2:OtherFracture", "R3:OtherFracture"),
    ("MassEffect",    "R1:MassEffect",    "R2:MassEffect",    "R3:MassEffect"),
    ("MidlineShift",  "R1:MidlineShift",  "R2:MidlineShift",  "R3:MidlineShift"),
]
LABEL_NAMES = [p[0] for p in LABEL_PAIRS]


def load_labels_and_match_ct():
    if not os.path.isfile(READS_CSV):
        logger.error(f"reads.csv 不存在: {READS_CSV}")
        return [], []

    df = pd.read_csv(READS_CSV)
    logger.info(f"reads.csv: {len(df)} 行")

    records = []
    missing = 0
    for _, row in df.iterrows():
        case_name = str(row["name"]).strip()
        # 多数投票
        labels = []
        for label_name, *cols in LABEL_PAIRS:
            votes = [int(row.get(col, 0)) for col in cols if col in row]
            labels.append(1 if sum(votes) >= 2 else 0)
        label_vec = np.array(labels, dtype=np.float32)

        vol_path = os.path.join(VOLUMES_DIR, f"{case_name}.nii.gz")
        if os.path.isfile(vol_path):
            records.append((vol_path, label_vec, case_name))
        else:
            missing += 1

    logger.info(f"匹配 CT+标签: {len(records)} 例, 未匹配: {missing}")

    labels_arr = np.array([r[1] for r in records])
    for i, name in enumerate(LABEL_NAMES):
        pos = int(labels_arr[:, i].sum())
        logger.info(f"  {name:20s}: {pos:4d}/{len(records)} ({pos/len(records)*100:.1f}%)")

    label_map = {str(i): name for i, name in enumerate(LABEL_NAMES)}
    with open(os.path.join(MODEL_OUTPUT_DIR, "ct_report_label_map.json"), "w", encoding="utf-8") as f:
        json.dump(label_map, f, ensure_ascii=False, indent=2)
    logger.info(f"标签映射已保存 ({len(LABEL_NAMES)} 类)")

    return records, LABEL_NAMES


# ═══════════════════════════════════════════════════════════════════════════
# 2. 数据集 (预加载预处理后的张量以加速，或保持动态加载)
# ═══════════════════════════════════════════════════════════════════════════
def _load_volume(vol_path):
    transform = Compose([
        LoadImaged(keys=["image"]),
        EnsureChannelFirstd(keys=["image"]),
        ScaleIntensityd(keys=["image"], minv=0, maxv=1),
        Orientationd(keys=["image"], axcodes="RAS"),
        Spacingd(keys=["image"], pixdim=(2.0, 2.0, 2.5), mode="bilinear"),
        SpatialPadd(keys=["image"], spatial_size=(128, 128, 96)),
        CenterSpatialCropD(keys=["image"], roi_size=(128, 128, 96)),
        ToTensord(keys=["image"]),
    ])
    return transform({"image": vol_path})["image"]


class CTReportDataset(Dataset):
    def __init__(self, records, is_train=True):
        self.records = records
        self.is_train = is_train
        self.aug = None
        if is_train:
            self.aug = Compose([
                RandFlipd(keys=["image"], spatial_axis=[0, 1, 2], prob=0.5),
                RandRotate90d(keys=["image"], spatial_axes=(0, 1), prob=0.3),
                RandZoomd(keys=["image"], min_zoom=0.95, max_zoom=1.05, prob=0.3),
            ])

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        vol_path, labels, _ = self.records[idx]
        img = _load_volume(vol_path)
        if self.aug and self.is_train:
            img = self.aug({"image": img})["image"]
        return img, torch.from_numpy(labels)


# ═══════════════════════════════════════════════════════════════════════════
# 3. 模型 (不变)
# ═══════════════════════════════════════════════════════════════════════════
class _ConvBlock3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch), nn.ReLU(inplace=True),
            nn.Conv3d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class CTReportClassifier3D(nn.Module):
    def __init__(self, in_channels=1, num_classes=14, dropout=0.3):
        super().__init__()
        self.enc1 = _ConvBlock3D(in_channels, 32)
        self.enc2 = _ConvBlock3D(32, 64)
        self.enc3 = _ConvBlock3D(64, 128)
        self.enc4 = _ConvBlock3D(128, 256)
        self.pool = nn.MaxPool3d(2)
        self.gpool = nn.AdaptiveAvgPool3d(1)
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout * 0.5),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        x = self.pool(self.enc1(x))
        x = self.pool(self.enc2(x))
        x = self.pool(self.enc3(x))
        x = self.pool(self.enc4(x))
        x = self.gpool(x).flatten(1)
        return self.classifier(x)


# ═══════════════════════════════════════════════════════════════════════════
# 4. 评估指标
# ═══════════════════════════════════════════════════════════════════════════
def compute_metrics(y_true, y_pred_probs, threshold=0.5):
    y_pred = (y_pred_probs >= threshold).astype(np.float32)
    acc = accuracy_score(y_true.flatten(), y_pred.flatten())
    f1_micro = f1_score(y_true, y_pred, average="micro", zero_division=0)
    f1_macro = f1_score(y_true, y_pred, average="macro", zero_division=0)
    aucs = []
    for i in range(y_true.shape[1]):
        try:
            if len(np.unique(y_true[:, i])) > 1:
                aucs.append(roc_auc_score(y_true[:, i], y_pred_probs[:, i]))
        except:
            pass
    return acc, f1_micro, f1_macro, np.mean(aucs) if aucs else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# 5. 检查点保存与恢复
# ═══════════════════════════════════════════════════════════════════════════
def save_checkpoint(epoch, model, optimizer, scheduler, best_f1, is_best=False):
    ckpt_path = os.path.join(MODEL_OUTPUT_DIR, f"clf_checkpoint_epoch{epoch:04d}.pth")
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict(),
        'best_f1': best_f1,
    }, ckpt_path)
    logger.info(f"检查点已保存: {ckpt_path}")
    if is_best:
        best_path = os.path.join(MODEL_OUTPUT_DIR, "ct_report_classifier.pth")
        torch.save(model.state_dict(), best_path)
        logger.info(f"最佳模型已保存 (F1={best_f1:.4f}): {best_path}")


def load_latest_checkpoint(model, optimizer, scheduler, device):
    ckpt_files = glob.glob(os.path.join(MODEL_OUTPUT_DIR, "clf_checkpoint_epoch*.pth"))
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
    best_f1 = checkpoint.get('best_f1', 0.0)

    logger.info(f"恢复检查点: {latest} (epoch {epoch_num}, best_f1={best_f1:.4f})")
    return epoch_num, best_f1


# ═══════════════════════════════════════════════════════════════════════════
# 6. 主函数
# ═══════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="CT 报告分类器训练 (加速+可恢复)")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--batch_size", type=int, default=1, help="批大小 (3D数据吃显存, 默认1; 12G+显存可试2~4)")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--val_split", type=float, default=0.2)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--num_workers", type=int, default=0, help="数据加载线程数 (3D数据吃内存, 默认0=单线程; 内存32G+可试2)")
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
    records, label_names = load_labels_and_match_ct()
    if len(records) == 0:
        logger.error("无有效数据!")
        return

    train_rec, val_rec = train_test_split(
        records, test_size=args.val_split, random_state=42,
        stratify=[r[1][0] for r in records]
    )
    logger.info(f"训练: {len(train_rec)} | 验证: {len(val_rec)}")

    # ── 2. Dataset & DataLoader (多线程) ──
    train_ds = CTReportDataset(train_rec, is_train=True)
    val_ds   = CTReportDataset(val_rec, is_train=False)
    use_workers = args.num_workers if args.num_workers >= 0 else 0
    if use_workers > 0:
        logger.warning(f"num_workers={use_workers}: 确保系统内存充足(≥32GB)")
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=use_workers,
        pin_memory=(use_workers==0),
        prefetch_factor=2 if use_workers > 0 else None,
        persistent_workers=(use_workers > 0),
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=use_workers,
        pin_memory=(use_workers==0),
        prefetch_factor=2 if use_workers > 0 else None,
        persistent_workers=(use_workers > 0),
    )

    # ── 3. 模型 ──
    model = CTReportClassifier3D(in_channels=1, num_classes=len(label_names)).to(device)
    logger.info(f"参数量: {sum(p.numel() for p in model.parameters()):,}")

    # 计算正样本权重 (平衡多标签损失)
    all_labels = np.array([r[1] for r in train_rec])
    pos_ratios = all_labels.mean(axis=0)
    pos_weight = torch.tensor([
        max(1.0, (1.0 - r) / max(r, 0.01)) for r in pos_ratios
    ]).to(device)
    logger.info(f"正样本权重: {pos_weight.cpu().numpy().round(2)}")

    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = GradScaler()

    # ── 4. 恢复检查点 ──
    start_epoch = 1
    best_f1 = 0.0
    if args.resume:
        epoch_loaded, best_f1 = load_latest_checkpoint(model, optimizer, scheduler, device)
        if epoch_loaded > 0:
            start_epoch = epoch_loaded + 1
            logger.info(f"从 epoch {start_epoch} 继续训练，当前最佳 F1 = {best_f1:.4f}")
        else:
            logger.info("未发现检查点，从头训练")

    # ── 5. CSV 日志 ──
    csv_path = os.path.join(LOG_DIR, "training_metrics.csv")
    file_exists = os.path.isfile(csv_path)
    csv_file = open(csv_path, "a", newline="")
    csv_writer = csv.writer(csv_file)
    if not file_exists:
        csv_writer.writerow(["epoch", "train_loss", "val_loss", "acc", "f1_micro", "f1_macro", "auc", "lr"])

    # ── 6. 训练循环 (带中断处理) ──
    logger.info("开始训练 (混合精度 + 中断恢复)")
    start_t = time.time()
    try:
        for epoch in range(start_epoch, args.epochs + 1):
            # 训练阶段
            model.train()
            train_loss = 0.0
            pbar = tqdm(train_loader, desc=f"E{epoch} Train", leave=False)
            for imgs, lbls in pbar:
                imgs, lbls = imgs.to(device, non_blocking=True), lbls.to(device, non_blocking=True)
                optimizer.zero_grad(set_to_none=True)

                with autocast():
                    preds = model(imgs)
                    loss = criterion(preds, lbls)

                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()

                train_loss += loss.item()
                pbar.set_postfix(loss=loss.item())
            train_loss /= len(train_loader)

            # 验证阶段
            model.eval()
            val_loss = 0.0
            all_true, all_pred = [], []
            with torch.no_grad():
                pbar = tqdm(val_loader, desc=f"E{epoch} Val", leave=False)
                for imgs, lbls in pbar:
                    imgs, lbls = imgs.to(device, non_blocking=True), lbls.to(device, non_blocking=True)
                    with autocast():
                        preds = model(imgs)
                        loss = criterion(preds, lbls)
                    val_loss += loss.item()
                    all_true.append(lbls.cpu().numpy())
                    all_pred.append(torch.sigmoid(preds).cpu().numpy())
                    pbar.set_postfix(loss=loss.item())
            val_loss /= len(val_loader)
            y_true = np.vstack(all_true)
            y_pred = np.vstack(all_pred)
            acc, f1_micro, f1_macro, mean_auc = compute_metrics(y_true, y_pred)

            scheduler.step()
            lr_now = scheduler.get_last_lr()[0]

            logger.info(f"E{epoch:3d}/{args.epochs} | Train L:{train_loss:.4f} | "
                        f"Val L:{val_loss:.4f} | Acc:{acc:.4f} F1μ:{f1_micro:.4f} "
                        f"F1M:{f1_macro:.4f} AUC:{mean_auc:.4f} | LR:{lr_now:.2e}")

            csv_writer.writerow([epoch, round(train_loss,4), round(val_loss,4),
                                 round(acc,4), round(f1_micro,4), round(f1_macro,4),
                                 round(mean_auc,4), lr_now])
            csv_file.flush()

            if f1_micro > best_f1:
                best_f1 = f1_micro
                save_checkpoint(epoch, model, optimizer, scheduler, best_f1, is_best=True)

            if epoch % 20 == 0:
                save_checkpoint(epoch, model, optimizer, scheduler, best_f1, is_best=False)

            if device.type == 'cuda' and epoch % 5 == 0:
                torch.cuda.empty_cache()

    except KeyboardInterrupt:
        logger.warning("用户中断训练，紧急保存当前状态...")
        save_checkpoint(epoch, model, optimizer, scheduler, best_f1, is_best=False)
        raise
    except Exception as e:
        logger.error(f"训练异常: {e}")
        save_checkpoint(epoch, model, optimizer, scheduler, best_f1, is_best=False)
        raise
    finally:
        csv_file.close()
        final_ckpt = os.path.join(MODEL_OUTPUT_DIR, "clf_checkpoint_final.pth")
        torch.save({
            'epoch': args.epochs,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'scheduler_state_dict': scheduler.state_dict(),
            'best_f1': best_f1,
        }, final_ckpt)
        logger.info(f"最终检查点: {final_ckpt}")

    total_t = time.time() - start_t
    logger.info(f"完成! {total_t:.0f}s ({total_t/60:.1f}min)")
    logger.info(f"最佳 F1: {best_f1:.4f}")
    logger.info(f"模型: {os.path.join(MODEL_OUTPUT_DIR, 'ct_report_classifier.pth')}")
    logger.info(f"训练指标: {csv_path}")


if __name__ == "__main__":
    main()