"""
CQ500 脑CT伪影分割模型训练脚本
使用完整数据集：490 例 CT 体数据 + 490 个伪影掩码
支持断点续训、自动保存、异常恢复

用法:
    python train_artifact_segmentation.py                      # 全量训练
    python train_artifact_segmentation.py --epochs 100         # 自定义 epoch
    python train_artifact_segmentation.py --resume best.pth    # 断点续训
    python train_artifact_segmentation.py --checkpoint-interval 5  # 每5轮保存检查点

输出:
    - best_artifact_unet.pth        # 最佳模型权重
    - checkpoint_epoch_*.pth        # 定期检查点
    - training_history.csv          # 训练日志
    - training_metrics.png          # 训练曲线图
"""

import os
import sys
import json
import time
import argparse
import signal
import csv
from datetime import datetime
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

# ==================== 全局配置 ====================
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
parser.add_argument('--checkpoint-interval', type=int, default=5, help='每多少轮保存一次检查点')
parser.add_argument('--gradient-accumulation', type=int, default=1, help='梯度累积步数')
parser.add_argument('--num-workers', type=int, default=0, help='数据加载线程数')
args = parser.parse_args()

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 创建日志目录
LOG_DIR = os.path.join(OUTPUT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)


# ==================== 优雅中断处理 ====================
class GracefulKiller:
    """优雅处理训练中断，保存检查点"""

    def __init__(self):
        self.kill_now = False
        self.interrupt_received = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        print("\n⚠️  收到中断信号，正在保存当前状态...")
        self.kill_now = True
        self.interrupt_received = True


# ==================== 3D UNet 模型 ====================
class DoubleConv3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv3d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch),
            nn.ReLU(inplace=True),
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
        # 处理尺寸不匹配
        diff_d = x2.size()[2] - x1.size()[2]
        diff_h = x2.size()[3] - x1.size()[3]
        diff_w = x2.size()[4] - x1.size()[4]
        x1 = nn.functional.pad(x1, [diff_w // 2, diff_w - diff_w // 2,
                                    diff_h // 2, diff_h - diff_h // 2,
                                    diff_d // 2, diff_d - diff_d // 2])
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

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        try:
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
        except Exception as e:
            print(f"⚠️  加载数据出错 {fname}: {e}")
            # 返回一个随机样本避免训练中断
            return torch.zeros((1, *self.target_shape)), torch.zeros((1, *self.target_shape))

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


# ==================== 检查点管理 ====================
def save_checkpoint(epoch, model, optimizer, scheduler, best_dice, history, is_best=False):
    """保存检查点"""
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'scheduler_state_dict': scheduler.state_dict() if scheduler else None,
        'best_dice': best_dice,
        'history': history,
        'args': vars(args),
        'timestamp': datetime.now().isoformat()
    }

    # 定期检查点
    checkpoint_path = os.path.join(OUTPUT_DIR, f'checkpoint_epoch_{epoch}.pth')
    torch.save(checkpoint, checkpoint_path)
    print(f"  💾 检查点已保存: {checkpoint_path}")

    # 删除旧的检查点（保留最近3个）
    checkpoints = sorted(glob(os.path.join(OUTPUT_DIR, 'checkpoint_epoch_*.pth')))
    for old_ckpt in checkpoints[:-3]:
        os.remove(old_ckpt)
        print(f"  🗑️  删除旧检查点: {os.path.basename(old_ckpt)}")

    # 最佳模型
    if is_best:
        best_path = os.path.join(OUTPUT_DIR, 'best_artifact_unet.pth')
        torch.save(checkpoint, best_path)
        print(f"  ⭐ 最佳模型已保存! Dice={best_dice:.4f}")


def load_checkpoint(path, model, optimizer, scheduler, device):
    """加载检查点"""
    print(f"📂 加载检查点: {path}")
    checkpoint = torch.load(path, map_location=device)

    model.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    if scheduler and checkpoint.get('scheduler_state_dict'):
        scheduler.load_state_dict(checkpoint['scheduler_state_dict'])

    epoch = checkpoint['epoch']
    best_dice = checkpoint.get('best_dice', 0.0)
    history = checkpoint.get('history', [])

    print(f"  从 Epoch {epoch} 恢复, Best Dice: {best_dice:.4f}")
    return epoch, best_dice, history


# ==================== 日志记录 ====================
class Logger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.terminal = sys.stdout
        self.log = open(log_file, 'a', encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()


# ==================== 主训练流程 ====================
def main():
    # 重定向输出到日志文件
    log_filename = f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(LOG_DIR, log_filename)
    sys.stdout = Logger(log_path)

    print("=" * 80)
    print("CQ500 颅脑CT伪影分割训练")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"设备: {args.device}")
    print(f"GPU设备数: {torch.cuda.device_count() if torch.cuda.is_available() else 0}")
    if torch.cuda.is_available():
        print(f"当前GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU内存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    print(f"数据路径: {VOLUMES_DIR}")
    print(f"掩码路径: {MASKS_DIR}")
    print(f"输出路径: {OUTPUT_DIR}")
    print(f"目标尺寸: {args.target_shape}")
    print(f"Epochs: {args.epochs} | Batch: {args.batch_size} | LR: {args.lr}")
    print(f"检查点间隔: {args.checkpoint_interval} | 梯度累积: {args.gradient_accumulation}")
    print("=" * 80)

    # 初始化优雅中断处理器
    killer = GracefulKiller()

    try:
        # 1. 获取文件列表
        all_files = sorted(glob(os.path.join(VOLUMES_DIR, "CQ500-CT-*.nii.gz")))
        all_files = [os.path.basename(f) for f in all_files]

        # 检查是否有对应掩码
        valid_files = []
        for f in all_files:
            mask_path = os.path.join(MASKS_DIR, f)
            if os.path.exists(mask_path):
                valid_files.append(f)
            else:
                print(f"⚠️  警告: {f} 没有对应的掩码文件")

        print(f"找到 {len(all_files)} 个体数据, {len(valid_files)} 个有对应掩码")

        if len(valid_files) == 0:
            print("❌ 错误: 未找到掩码文件! 请确认 masks 目录存在且包含对应 .nii.gz")
            sys.exit(1)

        # 2. 划分训练/验证集
        train_files, val_files = train_test_split(valid_files, test_size=args.val_ratio, random_state=42)
        print(f"📊 训练集: {len(train_files)} | 验证集: {len(val_files)}")

        # 3. 创建数据加载器
        train_ds = CQ500ArtifactDataset(train_files, VOLUMES_DIR, MASKS_DIR, args.target_shape)
        val_ds = CQ500ArtifactDataset(val_files, VOLUMES_DIR, MASKS_DIR, args.target_shape)

        train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                                  num_workers=args.num_workers, pin_memory=True, drop_last=True)
        val_loader = DataLoader(val_ds, batch_size=1, shuffle=False,
                                num_workers=0, pin_memory=True)

        # 4. 计算正样本权重 (处理类别不平衡)
        print("\n📊 计算类别权重...")
        total_pos = 0
        total_neg = 0
        for f in tqdm(train_files[:min(50, len(train_files))], desc="估算样本分布"):
            try:
                m = nib.load(os.path.join(MASKS_DIR, f)).get_fdata()
                total_pos += (m > 0).sum()
                total_neg += (m <= 0).sum()
            except Exception as e:
                print(f"  读取失败 {f}: {e}")
                continue

        pos_weight = total_neg / (total_pos + 1e-8)
        pos_weight = min(pos_weight, 30.0)
        print(f"  正样本权重: {pos_weight:.4f} (正:{total_pos}, 负:{total_neg})")

        # 5. 初始化模型
        device = torch.device(args.device)
        model = UNet3D(in_ch=1, out_ch=1, base_ch=16).to(device)

        # 多GPU支持
        if torch.cuda.device_count() > 1:
            print(f"🚀 使用 {torch.cuda.device_count()} 个GPU进行训练")
            model = nn.DataParallel(model)

        criterion = DiceBCELoss(pos_weight=torch.tensor([pos_weight]).to(device))
        optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

        start_epoch = 0
        best_dice = 0.0
        history = []

        # 断点续训
        if args.resume and os.path.exists(args.resume):
            epoch, best_dice, history = load_checkpoint(args.resume, model, optimizer, scheduler, device)
            start_epoch = epoch  # 从保存的epoch继续
        elif args.resume:
            print(f"⚠️  检查点不存在: {args.resume}")

        # 6. 训练循环
        print(f"\n🚀 开始训练, 共 {args.epochs} 个 epoch...")
        print("   (按 Ctrl+C 可安全保存状态并退出)\n")

        for epoch in range(start_epoch + 1, args.epochs + 1):
            # 检查中断信号
            if killer.kill_now:
                print("\n🛑 检测到中断信号，保存当前状态...")
                save_checkpoint(epoch - 1, model, optimizer, scheduler, best_dice, history)
                print("✅ 状态已保存，可以稍后使用 --resume 继续训练")
                break

            model.train()
            train_loss, train_dice, train_bce = 0, 0, 0
            optimizer.zero_grad()

            # 训练阶段
            train_pbar = tqdm(train_loader, desc=f"Epoch {epoch}/{args.epochs} [训练]")
            for batch_idx, (ct, mask) in enumerate(train_pbar):
                ct, mask = ct.to(device), mask.to(device)

                # 前向传播
                pred = model(ct)
                loss, ld, lb = criterion(pred, mask)

                # 梯度累积
                loss = loss / args.gradient_accumulation
                loss.backward()

                if (batch_idx + 1) % args.gradient_accumulation == 0:
                    # 梯度裁剪
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                    optimizer.step()
                    optimizer.zero_grad()

                train_loss += loss.item() * args.gradient_accumulation
                train_dice += ld.item()
                train_bce += lb.item()

                # 更新进度条
                train_pbar.set_postfix({
                    'loss': f'{loss.item() * args.gradient_accumulation:.4f}',
                    'dice': f'{ld.item():.4f}'
                })

            # 计算平均损失
            train_loss /= len(train_loader)
            train_dice /= len(train_loader)
            train_bce /= len(train_loader)

            # 验证阶段
            model.eval()
            val_dice, val_iou, val_recall, val_precision = 0, 0, 0, 0
            val_pbar = tqdm(val_loader, desc=f"Epoch {epoch}/{args.epochs} [验证]")

            with torch.no_grad():
                for ct, mask in val_pbar:
                    ct, mask = ct.to(device), mask.to(device)
                    pred = model(ct)
                    d, i, r, p = calculate_metrics(pred, mask)
                    val_dice += d
                    val_iou += i
                    val_recall += r
                    val_precision += p
                    val_pbar.set_postfix({'dice': f'{d:.4f}'})

            val_dice /= len(val_loader)
            val_iou /= len(val_loader)
            val_recall /= len(val_loader)
            val_precision /= len(val_loader)

            # 记录历史
            history.append({
                'epoch': epoch,
                'loss': train_loss,
                'dice_loss': train_dice,
                'bce_loss': train_bce,
                'val_dice': val_dice,
                'val_iou': val_iou,
                'val_recall': val_recall,
                'val_precision': val_precision,
                'timestamp': datetime.now().isoformat()
            })

            # 打印结果
            print(f"\n📊 Epoch {epoch}/{args.epochs}:")
            print(f"  训练 - Loss: {train_loss:.4f} | DiceLoss: {train_dice:.4f} | BCE: {train_bce:.4f}")
            print(
                f"  验证 - Dice: {val_dice:.4f} | IoU: {val_iou:.4f} | Recall: {val_recall:.4f} | Prec: {val_precision:.4f}")

            # 保存训练历史到CSV
            csv_path = os.path.join(OUTPUT_DIR, 'training_history.csv')
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['epoch', 'loss', 'dice_loss', 'bce_loss',
                                                       'val_dice', 'val_iou', 'val_recall', 'val_precision'])
                writer.writeheader()
                for h in history:
                    writer.writerow({k: h[k] for k in writer.fieldnames})

            # 更新学习率
            scheduler.step()
            current_lr = optimizer.param_groups[0]['lr']

            # 保存检查点
            is_best = val_dice > best_dice
            if is_best:
                best_dice = val_dice
                print(f"  🎉 新的最佳Dice: {best_dice:.4f}!")

            if epoch % args.checkpoint_interval == 0 or is_best:
                save_checkpoint(epoch, model, optimizer, scheduler, best_dice, history, is_best)

            # GPU内存清理
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            # 预估剩余时间
            if epoch > start_epoch + 1:
                avg_time_per_epoch = (time.time() - epoch_start_time) / (epoch - start_epoch)
                remaining_time = avg_time_per_epoch * (args.epochs - epoch)
                print(f"  ⏱️  预计剩余时间: {remaining_time / 60:.1f} 分钟")

            epoch_start_time = time.time()

        # 训练完成
        print("\n" + "=" * 80)
        print("✅ 训练完成!")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"最佳验证 Dice: {best_dice:.4f}")
        print(f"模型保存至: {OUTPUT_DIR}")
        print("=" * 80)

        # 7. 绘制训练曲线
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            epochs_list = [h['epoch'] for h in history]
            plt.figure(figsize=(14, 5))

            plt.subplot(1, 2, 1)
            plt.plot(epochs_list, [h['loss'] for h in history], label='Total Loss', linewidth=2)
            plt.plot(epochs_list, [h['dice_loss'] for h in history], label='Dice Loss', linewidth=2)
            plt.plot(epochs_list, [h['bce_loss'] for h in history], label='BCE Loss', linewidth=2)
            plt.xlabel('Epoch', fontsize=12)
            plt.ylabel('Loss', fontsize=12)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.title('Training Loss', fontsize=14)

            plt.subplot(1, 2, 2)
            plt.plot(epochs_list, [h['val_dice'] for h in history], label='Dice', linewidth=2)
            plt.plot(epochs_list, [h['val_iou'] for h in history], label='IoU', linewidth=2)
            plt.plot(epochs_list, [h['val_recall'] for h in history], label='Recall', linewidth=2)
            plt.plot(epochs_list, [h['val_precision'] for h in history], label='Precision', linewidth=2)
            plt.xlabel('Epoch', fontsize=12)
            plt.ylabel('Score', fontsize=12)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.title('Validation Metrics', fontsize=14)

            plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, 'training_metrics.png'), dpi=150)
            print(f"📈 训练曲线已保存: {os.path.join(OUTPUT_DIR, 'training_metrics.png')}")
        except ImportError:
            print("⚠️  提示: 安装 matplotlib 可自动生成训练曲线图 (pip install matplotlib)")

        # 8. 输出使用说明
        print(f"\n📖 使用训练好的模型进行推理:")
        print(f"  python inference.py --weights {os.path.join(OUTPUT_DIR, 'best_artifact_unet.pth')} --input <ct_file>")
        print(f"\n📝 如需恢复训练:")
        print(
            f"  python train_artifact_segmentation.py --resume {os.path.join(OUTPUT_DIR, 'checkpoint_epoch_latest.pth')}")

    except Exception as e:
        print(f"\n❌ 训练过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

        # 保存紧急检查点
        try:
            emergency_path = os.path.join(OUTPUT_DIR, 'emergency_checkpoint.pth')
            torch.save({
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, emergency_path)
            print(f"🆘 紧急检查点已保存: {emergency_path}")
        except:
            pass

        sys.exit(1)
    finally:
        # 恢复标准输出
        sys.stdout = sys.stdout.terminal
        print(f"\n📄 完整日志已保存至: {log_path}")


if __name__ == '__main__':
    main()