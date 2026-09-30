"""
CQ500 脑CT伪影分割模型训练脚本
使用完整数据集：490 例 CT 体数据 + 490 个伪影掩码

用法:
    python train_artifact_segmentation.py                      # 全量训练
    python train_artifact_segmentation.py --epochs 100         # 自定义 epoch
    python train_artifact_segmentation.py --resume best.pth    # 断点续训

输出:
    - best_artifact_unet.pth        # 最佳模型权重
    - training_history.csv          # 训练日志
    - training_metrics.png          # 训练曲线图
"""

import os, sys, json, time, argparse
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
import numpy as np
import nibabel as nib
from glob import glob
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# ==================== 配置 ====================
DATA_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'data', 'ct', 'cq500')
VOLUMES_DIR = os.path.join(DATA_ROOT, 'volumes')
MASKS_DIR = os.path.join(DATA_ROOT, 'masks')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models')

parser = argparse.ArgumentParser()
parser.add_argument('--epochs', type=int, default=80)
parser.add_argument('--batch-size', type=int, default=2)
parser.add_argument('--lr', type=float, default=1e-3)
parser.add_argument('--resume', type=str, default=None)
parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu')
parser.add_argument('--target-shape', type=int, nargs=3, default=(128, 128, 64))
parser.add_argument('--val-ratio', type=float, default=0.15)
args = parser.parse_args()

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==================== 3D UNet 模型 ====================
class DoubleConv3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch), nn.ReLU(inplace=True),
            nn.Conv3d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x): return self.conv(x)


class Down3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.pool = nn.MaxPool3d(2)
        self.conv = DoubleConv3D(in_ch, out_ch)

    def forward(self, x): return self.conv(self.pool(x))


class Up3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.up = nn.ConvTranspose3d(in_ch, in_ch // 2, 2, 2)
        self.conv = DoubleConv3D(in_ch, out_ch)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        d = x2.size()[2] - x1.size()[2]
        h = x2.size()[3] - x1.size()[3]
        w = x2.size()[4] - x1.size()[4]
        x1 = nn.functional.pad(x1, [w//2, w-w//2, h//2, h-h//2, d//2, d-d//2])
        return self.conv(torch.cat([x2, x1], dim=1))


class UNet3D(nn.Module):
    def __init__(self, in_ch=1, out_ch=1, base_ch=16):
        super().__init__()
        self.inc = DoubleConv3D(in_ch, base_ch)
        self.down1 = Down3D(base_ch, base_ch * 2)
        self.down2 = Down3D(base_ch * 2, base_ch * 4)
        self.down3 = Down3D(base_ch * 4, base_ch * 8)
        self.up1 = Up3D(base_ch * 8, base_ch * 4)
        self.up2 = Up3D(base_ch * 4, base_ch * 2)
        self.up3 = Up3D(base_ch * 2, base_ch)
        self.outc = nn.Conv3d(base_ch, out_ch, 1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x = self.up1(x4, x3)
        x = self.up2(x, x2)
        x = self.up3(x, x1)
        return self.outc(x)


# ==================== 数据集 ====================
class CQ500ArtifactDataset(Dataset):
    def __init__(self, file_list, volumes_dir, masks_dir, target_shape):
        self.files = file_list
        self.volumes_dir = volumes_dir
        self.masks_dir = masks_dir
        self.target_shape = target_shape

    def __len__(self): return len(self.files)

    def __getitem__(self, idx):
        fname = self.files[idx]
        ct_path = os.path.join(self.volumes_dir, fname)
        mask_path = os.path.join(self.masks_dir, fname)

        ct_img = nib.load(ct_path)
        mask_img = nib.load(mask_path)

        ct_data = ct_img.get_fdata().astype(np.float32)
        mask_data = mask_img.get_fdata().astype(np.float32)

        # HU 值裁剪到 [-1000, 2000]
        ct_data = np.clip(ct_data, -1000, 2000)
        # 归一化到 [0, 1]
        ct_data = (ct_data + 1000) / 3000.0

        # 二值化掩码
        mask_data = (mask_data > 0).astype(np.float32)

        # 重采样到目标尺寸
        ct_data = self._resize_volume(ct_data, self.target_shape)
        mask_data = self._resize_volume(mask_data, self.target_shape)

        # 添加通道维度
        ct_tensor = torch.from_numpy(ct_data).unsqueeze(0)
        mask_tensor = torch.from_numpy(mask_data).unsqueeze(0)

        return ct_tensor, mask_tensor

    @staticmethod
    def _resize_volume(volume, target_shape):
        import scipy.ndimage
        """使用 scipy 重采样到目标尺寸"""
        zoom_factors = [t / s for t, s in zip(target_shape, volume.shape)]
        return scipy.ndimage.zoom(volume, zoom_factors, order=1 if volume.ndim == 3 else 0)


# ==================== 损失函数 ====================
class DiceBCELoss(nn.Module):
    def __init__(self, pos_weight=None):
        super().__init__()
        self.dice_weight = 0.7
        self.bce_weight = 0.3
        if pos_weight is not None:
            pos_weight = torch.clamp(pos_weight, max=30.0)
            self.bce = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        else:
            self.bce = nn.BCEWithLogitsLoss()

    def forward(self, pred, target):
        pred_sig = torch.sigmoid(pred)
        intersection = (pred_sig * target).sum()
        dice_loss = 1 - (2. * intersection + 1) / (pred_sig.sum() + target.sum() + 1)
        bce_loss = self.bce(pred, target)
        return self.dice_weight * dice_loss + self.bce_weight * bce_loss, dice_loss.detach(), bce_loss.detach()


# ==================== 评估指标 ====================
def calculate_metrics(pred_logits, target, threshold=0.35):
    pred = (torch.sigmoid(pred_logits) > threshold).float()
    pred = pred.contiguous().view(-1)
    target = target.contiguous().view(-1)
    intersection = (pred * target).sum().item()
    sum_pred = pred.sum().item()
    sum_target = target.sum().item()

    dice = (2 * intersection + 1e-6) / (sum_pred + sum_target + 1e-6)
    iou = (intersection + 1e-6) / (sum_pred + sum_target - intersection + 1e-6)
    recall = (intersection + 1e-6) / (sum_target + 1e-6)
    precision = (intersection + 1e-6) / (sum_pred + 1e-6)
    return dice, iou, recall, precision


# ==================== 主训练流程 ====================
def main():
    print("=" * 60)
    print("CQ500 颅脑CT伪影分割训练")
    print(f"设备: {args.device}")
    print(f"数据: {VOLUMES_DIR}")
    print(f"掩码: {MASKS_DIR}")
    print(f"目标尺寸: {args.target_shape}")
    print(f"Epochs: {args.epochs} | Batch: {args.batch_size} | LR: {args.lr}")
    print("=" * 60)

    # 1. 获取文件列表
    all_files = sorted(glob(os.path.join(VOLUMES_DIR, "CQ500-CT-*.nii.gz")))
    all_files = [os.path.basename(f) for f in all_files]

    # 检查是否有对应掩码
    valid_files = [f for f in all_files if os.path.exists(os.path.join(MASKS_DIR, f))]
    print(f"找到 {len(all_files)} 个体数据, {len(valid_files)} 个有对应掩码")

    if len(valid_files) == 0:
        print("错误: 未找到掩码文件! 请确认 masks 目录存在且包含对应 .nii.gz")
        sys.exit(1)

    # 2. 划分训练/验证集
    train_files, val_files = train_test_split(valid_files, test_size=args.val_ratio, random_state=42)
    print(f"训练集: {len(train_files)} | 验证集: {len(val_files)}")

    # 3. 创建数据加载器
    train_ds = CQ500ArtifactDataset(train_files, VOLUMES_DIR, MASKS_DIR, args.target_shape)
    val_ds = CQ500ArtifactDataset(val_files, VOLUMES_DIR, MASKS_DIR, args.target_shape)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=1, shuffle=False, num_workers=0, pin_memory=True)

    # 4. 计算正样本权重 (处理类别不平衡)
    print("\n计算类别权重...")
    total_pos = 0
    total_neg = 0
    for f in tqdm(train_files[:50]):  # 采样50个估算
        try:
            m = nib.load(os.path.join(MASKS_DIR, f)).get_fdata()
            total_pos += (m > 0).sum()
            total_neg += (m <= 0).sum()
        except:
            continue

    pos_weight = total_neg / (total_pos + 1e-8)
    pos_weight = min(pos_weight, 30.0)
    print(f"正样本权重: {pos_weight:.4f}")

    # 5. 初始化模型
    device = torch.device(args.device)
    model = UNet3D(in_ch=1, out_ch=1, base_ch=16).to(device)
    criterion = DiceBCELoss(pos_weight=torch.tensor([pos_weight]).to(device))
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    start_epoch = 0
    best_dice = 0.0
    history = []

    # 断点续训
    if args.resume and os.path.exists(args.resume):
        print(f"加载断点: {args.resume}")
        ckpt = torch.load(args.resume, map_location=device)
        model.load_state_dict(ckpt['model'])
        optimizer.load_state_dict(ckpt['optimizer'])
        start_epoch = ckpt['epoch']
        best_dice = ckpt.get('best_dice', 0.0)

    # 6. 训练循环
    print(f"\n开始训练, 共 {args.epochs} 个 epoch...")
    for epoch in range(start_epoch, args.epochs):
        model.train()
        train_loss, train_dice, train_bce = 0, 0, 0

        for ct, mask in tqdm(train_loader, desc=f"Epoch {epoch+1}/{args.epochs} [Train]"):
            ct, mask = ct.to(device), mask.to(device)

            optimizer.zero_grad()
            pred = model(ct)
            loss, ld, lb = criterion(pred, mask)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_dice += ld.item()
            train_bce += lb.item()

        train_loss /= len(train_loader)
        train_dice /= len(train_loader)
        train_bce /= len(train_loader)

        # 验证
        model.eval()
        val_dice, val_iou, val_recall, val_precision = 0, 0, 0, 0
        with torch.no_grad():
            for ct, mask in tqdm(val_loader, desc=f"Epoch {epoch+1}/{args.epochs} [Val]"):
                ct, mask = ct.to(device), mask.to(device)
                pred = model(ct)
                d, i, r, p = calculate_metrics(pred, mask)
                val_dice += d
                val_iou += i
                val_recall += r
                val_precision += p

        val_dice /= len(val_loader)
        val_iou /= len(val_loader)
        val_recall /= len(val_loader)
        val_precision /= len(val_loader)

        print(f"Epoch {epoch+1}: Loss={train_loss:.4f} | DiceLoss={train_dice:.4f} | "
              f"BCE={train_bce:.4f} | Val Dice={val_dice:.4f} | "
              f"IoU={val_iou:.4f} | Recall={val_recall:.4f} | Prec={val_precision:.4f}")

        history.append({
            'epoch': epoch + 1, 'loss': train_loss, 'dice_loss': train_dice,
            'bce_loss': train_bce, 'val_dice': val_dice, 'val_iou': val_iou,
            'val_recall': val_recall, 'val_precision': val_precision
        })

        # 保存最佳模型
        if val_dice > best_dice:
            best_dice = val_dice
            torch.save({
                'epoch': epoch + 1,
                'model': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'best_dice': best_dice,
                'config': vars(args),
            }, os.path.join(OUTPUT_DIR, 'best_artifact_unet.pth'))
            print(f"  最佳模型已保存! Dice={val_dice:.4f}")

        scheduler.step()

    # 7. 保存最终模型和训练历史
    final_path = os.path.join(OUTPUT_DIR, 'artifact_unet_final.pth')
    torch.save({
        'epoch': args.epochs,
        'model': model.state_dict(),
        'best_dice': best_dice,
        'config': vars(args),
    }, final_path)

    import csv
    with open(os.path.join(OUTPUT_DIR, 'training_history.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=history[0].keys())
        w.writeheader()
        w.writerows(history)

    print(f"\n训练完成!")
    print(f"最佳 Val Dice: {best_dice:.4f}")
    print(f"模型保存至: {OUTPUT_DIR}")

    # 8. 绘制训练曲线（可选，需要 matplotlib）
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        epochs_list = [h['epoch'] for h in history]
        plt.figure(figsize=(12, 4))
        plt.subplot(1, 2, 1)
        plt.plot(epochs_list, [h['loss'] for h in history], label='Total Loss')
        plt.plot(epochs_list, [h['dice_loss'] for h in history], label='Dice Loss')
        plt.plot(epochs_list, [h['bce_loss'] for h in history], label='BCE Loss')
        plt.xlabel('Epoch'); plt.ylabel('Loss'); plt.legend(); plt.grid(True, alpha=0.3)
        plt.title('Training Loss')

        plt.subplot(1, 2, 2)
        plt.plot(epochs_list, [h['val_dice'] for h in history], label='Dice')
        plt.plot(epochs_list, [h['val_iou'] for h in history], label='IoU')
        plt.plot(epochs_list, [h['val_recall'] for h in history], label='Recall')
        plt.plot(epochs_list, [h['val_precision'] for h in history], label='Precision')
        plt.xlabel('Epoch'); plt.ylabel('Score'); plt.legend(); plt.grid(True, alpha=0.3)
        plt.title('Validation Metrics')

        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'training_metrics.png'), dpi=150)
        print(f"训练曲线已保存至: {os.path.join(OUTPUT_DIR, 'training_metrics.png')}")
    except ImportError:
        print("提示: 安装 matplotlib 可自动生成训练曲线图")

    print(f"\n使用训练好的模型进行推理:")
    print(f"  python inference.py --weights {os.path.join(OUTPUT_DIR, 'best_artifact_unet.pth')} --input <ct_file>")


if __name__ == '__main__':
    main()
