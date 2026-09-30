"""
脑部CT异常检测 3D ResNet-AE v2
================================
【改进】3D ResNet编码器 + 密集跳跃连接解码器 + 多尺度特征
【数据】MHD体数据 + 5个DICOM序列 (共~1138张CT切片)
【架构】3D ResNet-18风格编码器 + 注意力门控解码器
【优化】AdamW + 余弦退火 + 结构相似性损失(SSIM) + L1混合损失
【输出】仅保留最优模型 -> brain_ct_ae.pth
"""

import os, sys, json, warnings, copy
import numpy as np
import joblib
from datetime import datetime
from collections import OrderedDict

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split

from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── 配置 ──
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[设备] {DEVICE} | CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"       GPU: {torch.cuda.get_device_name(0)}")
    print(f"       显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

PATCH_SIZE = 48               # 3D patch size: 48x48x48
STRIDE = 24                    # 重叠步长
BATCH_SIZE = 32
EPOCHS = 300
LEARNING_RATE = 2e-4
WEIGHT_DECAY = 1e-5
PATIENCE = 60
HIDDEN_CHANNELS = [32, 64, 128, 256, 512]

# 数据路径
MHD_DIR = r'D:\东软实习\simpleitk\data\mhd'
DICOM_BASE = r'D:\东软实习\CQ500CT0 CQ500CT0\Unknown Study'
DICOM_SIMPLEITK = r'D:\东软实习\simpleitk\data\CT Plain'


# ── 3D卷积残差块 ──
class Conv3DBlock(nn.Module):
    def __init__(self, in_ch, out_ch, stride=1):
        super().__init__()
        self.conv = nn.Sequential(OrderedDict([
            ('conv1', nn.Conv3d(in_ch, out_ch, 3, stride, padding=1, bias=False)),
            ('bn1', nn.BatchNorm3d(out_ch)),
            ('relu1', nn.LeakyReLU(0.2, inplace=True)),
            ('conv2', nn.Conv3d(out_ch, out_ch, 3, 1, padding=1, bias=False)),
            ('bn2', nn.BatchNorm3d(out_ch)),
        ]))
        self.shortcut = nn.Sequential()
        if stride != 1 or in_ch != out_ch:
            self.shortcut = nn.Sequential(
                nn.Conv3d(in_ch, out_ch, 1, stride, bias=False),
                nn.BatchNorm3d(out_ch)
            )

    def forward(self, x):
        return F.leaky_relu(self.conv(x) + self.shortcut(x), 0.2, inplace=True)


class UpConv3D(nn.Module):
    """上采样+卷积"""
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.up = nn.ConvTranspose3d(in_ch, out_ch, 2, stride=2)
        self.conv = Conv3DBlock(out_ch * 2, out_ch)

    def forward(self, x, skip):
        x = self.up(x)
        # Deal with size mismatch
        if x.shape[-3] != skip.shape[-3] or x.shape[-2] != skip.shape[-2] or x.shape[-1] != skip.shape[-1]:
            diff_d = skip.shape[-3] - x.shape[-3]
            diff_h = skip.shape[-2] - x.shape[-2]
            diff_w = skip.shape[-1] - x.shape[-1]
            x = F.pad(x, [diff_w // 2, diff_w - diff_w // 2,
                          diff_h // 2, diff_h - diff_h // 2,
                          diff_d // 2, diff_d - diff_d // 2])
        x = torch.cat([x, skip], dim=1)
        return self.conv(x)


# ── 3D ResNet Autoencoder ──
class ResNet3DAE(nn.Module):
    """
    3D ResNet风格自编码器
    编码器: ResNet-18风格 3D CNN
    解码器: 密集跳跃连接的转置卷积
    """
    def __init__(self, in_channels=1, base_ch=32):
        super().__init__()

        # ── 编码器 (ResNet-18风格) ──
        self.enc_conv1 = nn.Sequential(
            nn.Conv3d(in_channels, base_ch, 7, stride=2, padding=3, bias=False),
            nn.BatchNorm3d(base_ch),
            nn.LeakyReLU(0.2, inplace=True),
            nn.MaxPool3d(3, stride=2, padding=1),
        )
        # 1/4 resolution

        self.enc_layer1 = self._make_layer(base_ch, base_ch * 2, 2, stride=2)   # 1/8
        self.enc_layer2 = self._make_layer(base_ch * 2, base_ch * 4, 2, stride=2)  # 1/16
        self.enc_layer3 = self._make_layer(base_ch * 4, base_ch * 8, 2, stride=2)  # 1/32
        self.enc_layer4 = self._make_layer(base_ch * 8, base_ch * 16, 2, stride=2)  # 1/64

        # ── 瓶颈 ──
        self.bottleneck = nn.Sequential(
            nn.Conv3d(base_ch * 16, base_ch * 16, 3, 1, padding=1, bias=False),
            nn.BatchNorm3d(base_ch * 16),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv3d(base_ch * 16, base_ch * 8, 1, 1, bias=False),
            nn.BatchNorm3d(base_ch * 8),
            nn.LeakyReLU(0.2, inplace=True),
        )

        # ── 解码器 (U-Net风格跳跃连接) ──
        self.dec_layer4 = UpConv3D(base_ch * 8, base_ch * 4)
        self.dec_layer3 = UpConv3D(base_ch * 4, base_ch * 2)
        self.dec_layer2 = UpConv3D(base_ch * 2, base_ch)
        self.dec_layer1 = UpConv3D(base_ch, base_ch // 2)

        # ── 输出 ──
        self.output_conv = nn.Sequential(
            nn.ConvTranspose3d(base_ch // 2, base_ch // 2, 2, stride=2),
            nn.BatchNorm3d(base_ch // 2),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Conv3d(base_ch // 2, 1, 3, padding=1),
        )

    def _make_layer(self, in_ch, out_ch, n_blocks, stride=1):
        layers = [Conv3DBlock(in_ch, out_ch, stride)]
        for _ in range(1, n_blocks):
            layers.append(Conv3DBlock(out_ch, out_ch))
        return nn.Sequential(*layers)

    def encode(self, x):
        """编码：返回多尺度特征"""
        skips = []
        x = self.enc_conv1(x)
        skips.append(x)

        x = self.enc_layer1(x)
        skips.append(x)
        x = self.enc_layer2(x)
        skips.append(x)
        x = self.enc_layer3(x)
        skips.append(x)
        x = self.enc_layer4(x)
        skips.append(x)

        x = self.bottleneck(x)
        return x, skips

    def decode(self, x, skips):
        """解码：利用跳跃连接重建"""
        x = self.dec_layer4(x, skips[3])
        x = self.dec_layer3(x, skips[2])
        x = self.dec_layer2(x, skips[1])
        x = self.dec_layer1(x, skips[0])
        x = self.output_conv(x)
        return x

    def forward(self, x):
        z, skips = self.encode(x)
        recon = self.decode(z, skips)
        return recon


# ── 混合损失 (SSIM + L1) ──
def ssim_loss(pred, target, data_range=1.0, window_size=11):
    """简化的3D SSIM损失"""
    # 使用3D平均池化模拟SSIM
    C1 = (0.01 * data_range) ** 2
    C2 = (0.03 * data_range) ** 2

    mu_pred = F.avg_pool3d(pred, window_size, stride=1, padding=window_size // 2)
    mu_target = F.avg_pool3d(target, window_size, stride=1, padding=window_size // 2)

    sigma_pred = F.avg_pool3d(pred ** 2, window_size, stride=1, padding=window_size // 2) - mu_pred ** 2
    sigma_target = F.avg_pool3d(target ** 2, window_size, stride=1, padding=window_size // 2) - mu_target ** 2
    sigma_cross = F.avg_pool3d(pred * target, window_size, stride=1, padding=window_size // 2) - mu_pred * mu_target

    ssim_map = ((2 * mu_pred * mu_target + C1) * (2 * sigma_cross + C2)) / \
               ((mu_pred ** 2 + mu_target ** 2 + C1) * (sigma_pred + sigma_target + C2))
    return 1 - ssim_map.mean()


class HybridLoss(nn.Module):
    """L1 + SSIM 混合损失"""
    def __init__(self, alpha=0.85, window_size=11):
        super().__init__()
        self.alpha = alpha
        self.window_size = window_size

    def forward(self, pred, target):
        l1 = F.l1_loss(pred, target)
        ssim_val = ssim_loss(pred, target, data_range=1.0, window_size=self.window_size)
        return self.alpha * l1 + (1 - self.alpha) * ssim_val


# ── 数据加载 ──
def read_raw_mhd(mhd_path):
    """手动读取MHD文件 (解决中文路径问题)"""
    with open(mhd_path, 'r', encoding='utf-8') as f:
        meta = {}
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                meta[k.strip()] = v.strip()

    dims = [int(x) for x in meta['DimSize'].split()]
    dtype_map = {
        'MET_SHORT': np.int16,
        'MET_USHORT': np.uint16,
        'MET_FLOAT': np.float32,
        'MET_DOUBLE': np.float64,
        'MET_CHAR': np.int8,
        'MET_UCHAR': np.uint8,
    }
    np_dtype = dtype_map.get(meta.get('ElementType', 'MET_SHORT'), np.int16)

    raw_path = mhd_path.replace('.mhd', '.raw')
    if not os.path.exists(raw_path):
        raw_path = os.path.join(os.path.dirname(mhd_path), meta.get('ElementDataFile', ''))

    raw_data = np.fromfile(raw_path, dtype=np_dtype)
    volume = raw_data.reshape(dims, order='F').astype(np.float32)
    return volume


def read_dicom_series(dicom_dir):
    """使用SimpleITK读取DICOM系列"""
    try:
        import SimpleITK as sitk
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
        if not dicom_names:
            files = sorted([os.path.join(dicom_dir, f) for f in os.listdir(dicom_dir)
                           if f.endswith('.dcm')])
            if not files:
                return None
            dicom_names = files
        reader.SetFileNames(dicom_names)
        reader.MetaDataDictionaryArrayUpdateOn()
        reader.LoadPrivateTagsOn()
        image = reader.Execute()
        volume = sitk.GetArrayFromImage(image).astype(np.float32)
        return volume
    except Exception as e:
        print(f"    SimpleITK失败: {e}, 尝试pydicom...")
        try:
            import pydicom
            files = sorted([os.path.join(dicom_dir, f) for f in os.listdir(dicom_dir)
                           if f.endswith('.dcm')])
            slices = []
            for f in files:
                ds = pydicom.dcmread(f, force=True)
                slices.append(ds.pixel_array.astype(np.float32))
            return np.stack(slices, axis=0)
        except Exception as e2:
            print(f"    pydicom也失败: {e2}")
            return None


def normalize_ct(volume):
    """CT值归一化: [-1000, 2000] -> [0, 1]"""
    volume = np.clip(volume, -1000, 2000)
    volume = (volume + 1000) / 3000.0
    return volume


def load_all_ct_data():
    """加载所有可用的CT数据"""
    print("=" * 65)
    print("     脑部CT异常检测 v2 — 加载所有CT数据")
    print("=" * 65)

    all_volumes = []

    # 1. MHD体积
    mhd_file = os.path.join(MHD_DIR, '1.mhd')
    if os.path.exists(mhd_file):
        try:
            print(f"\n[MHD] 加载: {mhd_file}")
            volume = read_raw_mhd(mhd_file)
            print(f"  形状: {volume.shape}, 范围: [{volume.min():.0f}, {volume.max():.0f}]")
            all_volumes.append(('MHD', volume))
        except Exception as e:
            print(f"  [ERROR] MHD加载失败: {e}")
    else:
        print(f"\n[MHD] 未找到: {mhd_file}")

    # 2. DICOM系列 (CQ500)
    print(f"\n[DICOM] CQ500系列:")
    if os.path.exists(DICOM_BASE):
        for series_name in sorted(os.listdir(DICOM_BASE)):
            series_path = os.path.join(DICOM_BASE, series_name)
            if os.path.isdir(series_path):
                print(f"  加载: {series_name}...")
                volume = read_dicom_series(series_path)
                if volume is not None:
                    print(f"    形状: {volume.shape}, 范围: [{volume.min():.0f}, {volume.max():.0f}]")
                    all_volumes.append((series_name, volume))
                else:
                    print(f"    [跳过] 加载失败")

    # 3. SimpleITK CT Plain
    if os.path.exists(DICOM_SIMPLEITK) and os.path.isdir(DICOM_SIMPLEITK):
        print(f"\n[DICOM] SimpleITK CT Plain:")
        volume = read_dicom_series(DICOM_SIMPLEITK)
        if volume is not None:
            print(f"  形状: {volume.shape}, 范围: [{volume.min():.0f}, {volume.max():.0f}]")
            all_volumes.append(('CT_Plain_sitk', volume))
        else:
            print(f"  [跳过] 加载失败")

    print(f"\n总计加载 {len(all_volumes)} 个体数据")
    for name, vol in all_volumes:
        print(f"  {name:30s}: {vol.shape}")

    return all_volumes


# ── 3D Patch数据集 ──
class CT3DPatchDataset(Dataset):
    """从3D体积中提取重叠patch的数据集"""
    def __init__(self, volumes, patch_size=48, stride=24, augment=True):
        self.patches = []
        self.patch_sources = []

        for vol_name, volume in volumes:
            # 归一化
            vol_norm = normalize_ct(volume)
            vol_norm = vol_norm[np.newaxis, ...]  # (1, D, H, W)

            D, H, W = vol_norm.shape[1:]

            if D < patch_size or H < patch_size or W < patch_size:
                print(f"  [跳过] {vol_name}: {vol_norm.shape} 小于patch大小 {patch_size}")
                continue

            # 提取重叠patch
            z_steps = max(1, (D - patch_size) // stride + 1)
            y_steps = max(1, (H - patch_size) // stride + 1)
            x_steps = max(1, (W - patch_size) // stride + 1)

            for z in range(0, D - patch_size + 1, stride):
                for y in range(0, H - patch_size + 1, stride):
                    for x in range(0, W - patch_size + 1, stride):
                        patch = vol_norm[:, z:z+patch_size, y:y+patch_size, x:x+patch_size]
                        # 检查有效CT值范围
                        if patch.max() > -500 / 3000 + 1000/3000:  # ~0.167 (有组织)
                            self.patches.append(patch)
                            self.patch_sources.append(vol_name)

            # 如果步长较大, 也提取最后一部分
            if D - patch_size > 0 and (D - patch_size) % stride != 0:
                z = D - patch_size
                for y in range(0, H - patch_size + 1, stride):
                    for x in range(0, W - patch_size + 1, stride):
                        patch = vol_norm[:, z:z+patch_size, y:y+patch_size, x:x+patch_size]
                        if patch.max() > -500 / 3000 + 1000/3000:
                            self.patches.append(patch)
                            self.patch_sources.append(vol_name)

        self.patches = np.array(self.patches, dtype=np.float32)
        self.augment = augment

        print(f"\n[数据集] 共 {len(self.patches)} 个 {patch_size}x{patch_size}x{patch_size} patches")
        for name in set(self.patch_sources):
            cnt = self.patch_sources.count(name)
            print(f"  {name}: {cnt} patches ({cnt/len(self.patches)*100:.1f}%)")

    def __len__(self):
        return len(self.patches)

    def __getitem__(self, idx):
        patch = self.patches[idx].copy()

        if self.augment and np.random.random() > 0.3:
            # 随机翻转
            # patch shape: (1, D, H, W) - axes 1,2,3 are D,H,W
            axes = []
            if np.random.random() > 0.5:
                axes.append(1)  # 深度翻转
            if np.random.random() > 0.5:
                axes.append(2)  # 高度翻转
            if np.random.random() > 0.5:
                axes.append(3)  # 宽度翻转
            if axes:
                patch = np.flip(patch, axis=axes).copy()

            # 随机噪声
            if np.random.random() > 0.7:
                noise = np.random.normal(0, 0.01, patch.shape).astype(np.float32)
                patch = np.clip(patch + noise, 0, 1)

            # 随机对比度/亮度
            if np.random.random() > 0.8:
                alpha = np.random.uniform(0.9, 1.1)
                beta = np.random.uniform(-0.02, 0.02)
                patch = np.clip(patch * alpha + beta, 0, 1)

        return torch.FloatTensor(patch)


# ── 训练函数 ──
def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0

    for batch in loader:
        batch = batch.to(device)
        optimizer.zero_grad()
        recon = model(batch)
        loss = criterion(recon, batch)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        total_loss += loss.item() * batch.size(0)

    return total_loss / len(loader.dataset)


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0

    for batch in loader:
        batch = batch.to(device)
        recon = model(batch)
        loss = criterion(recon, batch)
        total_loss += loss.item() * batch.size(0)

    return total_loss / len(loader.dataset)


# ── 主流程 ──
def main():
    # 1. 加载所有CT数据
    all_volumes = load_all_ct_data()
    if len(all_volumes) == 0:
        print("[FATAL] 没有可用的CT数据!")
        return

    # 2. 创建Patch数据集
    dataset = CT3DPatchDataset(all_volumes, PATCH_SIZE, STRIDE, augment=True)

    if len(dataset) == 0:
        print("[FATAL] 没有有效的patch!")
        return

    # 3. 划分训练/验证集
    val_ratio = 0.15
    val_size = max(1, int(len(dataset) * val_ratio))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size],
                                    generator=torch.Generator().manual_seed(SEED))

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=0, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=0, pin_memory=True)

    print(f"\n数据划分:")
    print(f"  训练: {train_size} patches")
    print(f"  验证: {val_size} patches")
    print(f"  Batch: {BATCH_SIZE}")
    print(f"  训练步数/epoch: {len(train_loader)}")

    # 4. 初始化模型
    model = ResNet3DAE(in_channels=1, base_ch=32).to(DEVICE)

    n_params = sum(p.numel() for p in model.parameters())
    print(f"\n[模型] 3D ResNet-AE v2")
    print(f"  总参数量: {n_params:,}")
    print(f"  编码器: ResNet-18风格 3D CNN (5级)")
    print(f"  解码器: U-Net风格跳跃连接转置卷积")
    print(f"  损失函数: L1 + SSIM 混合损失")

    # 5. 优化器 & 损失
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    criterion = HybridLoss(alpha=0.85, window_size=7)
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=50, T_mult=2, eta_min=1e-7
    )

    # 6. 训练
    print(f"\n{'=' * 65}")
    print(f"  训练配置:")
    print(f"  Epochs: {EPOCHS} | Batch: {BATCH_SIZE}")
    print(f"  LR: {LEARNING_RATE} | WD: {WEIGHT_DECAY}")
    print(f"  Patch: {PATCH_SIZE}x{PATCH_SIZE}x{PATCH_SIZE} | Stride: {STRIDE}")
    print(f"  Patience: {PATIENCE}")
    print(f"{'=' * 65}\n")

    best_val_loss = float('inf')
    best_state = None
    best_epoch = 0
    patience_counter = 0
    history = []

    pbar = tqdm(range(1, EPOCHS + 1), desc="3D ResNet-AE v2", ncols=100,
                bar_format='{desc} |{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')

    for epoch in pbar:
        train_loss = train_epoch(model, train_loader, criterion, optimizer, DEVICE)
        val_loss = evaluate(model, val_loader, criterion, DEVICE)

        scheduler.step()
        history.append({'epoch': epoch, 'train_loss': train_loss, 'val_loss': val_loss})

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            patience_counter = 0
        else:
            patience_counter += 1

        pbar.set_postfix({
            'train': f'{train_loss:.5f}',
            'val': f'{val_loss:.5f}',
            'best': f'{best_val_loss:.5f}',
        }, refresh=False)

        if patience_counter >= PATIENCE:
            print(f"\n  [EarlyStop] Epoch {epoch}, 无改善 {PATIENCE} 轮")
            break

    # 加载最佳模型
    model.load_state_dict(best_state)

    print(f"\n{'=' * 65}")
    print(f"  训练完成!")
    print(f"  最佳 epoch: {best_epoch}/{epoch}")
    print(f"  最佳 val_loss: {best_val_loss:.5f}")
    print(f"{'=' * 65}")

    # 7. 保存模型
    model_path = os.path.join(OUTPUT_DIR, 'brain_ct_ae.pth')
    info_path = os.path.join(OUTPUT_DIR, 'brain_ct_info.joblib')

    torch.save({
        'model_state_dict': best_state,
        'architecture': 'ResNet3DAE',
        'config': {
            'base_channels': 32,
            'patch_size': PATCH_SIZE,
            'stride': STRIDE,
            'resnet_layers': 4,
            'encoder_type': 'ResNet-18 style 3D',
            'decoder_type': 'U-Net skip connections',
            'loss': 'Hybrid(L1+SSIM)',
        },
        'performance': {
            'best_val_loss': float(best_val_loss),
            'best_epoch': int(best_epoch),
            'n_patches_trained': len(train_ds),
            'n_patches_val': len(val_ds),
        },
        'n_params': n_params,
        'training_date': datetime.now().isoformat(),
        'device': str(DEVICE),
    }, model_path)

    print(f"\n[保存] 模型 -> {model_path}")

    # 保存元信息
    volumes_info = []
    for name, vol in all_volumes:
        volumes_info.append({
            'name': name,
            'shape': list(vol.shape),
            'min': float(vol.min()),
            'max': float(vol.max()),
            'mean': float(vol.mean()),
        })

    info = {
        'name': '脑部CT异常检测 v2 (3D ResNet-AE)',
        'model_type': '3D Residual Autoencoder',
        'architecture': {
            'type': 'ResNet3DAE',
            'encoder': '3D ResNet-18 style (5-level)',
            'decoder': 'U-Net skip connections (4-level)',
            'bottleneck': 'Conv + compression',
            'loss': 'Hybrid(L1 + SSIM)',
            'total_params': n_params,
        },
        'data': {
            'sources': volumes_info,
            'total_volumes': len(all_volumes),
            'total_slices': sum(v.shape[0] for _, v in all_volumes if v.ndim == 3),
            'patch_size': PATCH_SIZE,
            'stride': STRIDE,
            'train_patches': len(train_ds),
            'val_patches': len(val_ds),
        },
        'training': {
            'epochs_trained': epoch,
            'best_epoch': best_epoch,
            'best_val_loss': float(best_val_loss),
            'batch_size': BATCH_SIZE,
            'learning_rate': LEARNING_RATE,
            'weight_decay': WEIGHT_DECAY,
            'early_stopping_patience': PATIENCE,
        },
        'detection': {
            'method': 'patch_reconstruction_error',
            'anomaly_threshold': None,  # 需要校准
            'input_format': '3D patches or full volume slices',
        },
        'training_date': datetime.now().isoformat(),
        'device': str(DEVICE),
    }
    joblib.dump(info, info_path)

    print(f"[保存] 元信息 -> {info_path}")

    # 8. 最终验证: 计算重建误差统计
    print(f"\n{'=' * 65}")
    print(f"  重建误差分析")
    print(f"{'=' * 65}")

    model.eval()
    all_errors = []
    with torch.no_grad():
        for batch in val_loader:
            batch = batch.to(DEVICE)
            recon = model(batch)
            errors = F.l1_loss(recon, batch, reduction='none')
            all_errors.extend(errors.view(batch.size(0), -1).mean(dim=1).cpu().numpy())

    all_errors = np.array(all_errors)
    threshold = np.percentile(all_errors, 95)

    print(f"  验证集重建误差统计:")
    print(f"    均值: {all_errors.mean():.5f}")
    print(f"    标准差: {all_errors.std():.5f}")
    print(f"    最小值: {all_errors.min():.5f}")
    print(f"    最大值: {all_errors.max():.5f}")
    print(f"    95分位数 (建议异常阈值): {threshold:.5f}")

    # 更新info中的阈值
    info['detection']['anomaly_threshold'] = float(threshold)
    info['detection']['reconstruction_error_stats'] = {
        'mean': float(all_errors.mean()),
        'std': float(all_errors.std()),
        'p95': float(threshold),
    }
    joblib.dump(info, info_path)  # 重新保存

    print(f"\n[完成] 脑部CT 3D ResNet-AE v2 训练结束!\n")


if __name__ == '__main__':
    main()
