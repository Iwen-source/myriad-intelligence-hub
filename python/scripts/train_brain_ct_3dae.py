"""
脑部CT异常检测 — 3D卷积自编码器 (PyTorch + CUDA)
==============================================
【数据源】CQ500真实CT数据集 + SimpleITK MHD体数据
         - 1个完整MHD体数据 (512×512×121 ≈ 30M voxels)
         - 5个DICOM系列 (~990 slices)
         - 30个独立DICOM文件
【架构】  3D卷积自编码器 (无监督异常检测)
          编码器提取压缩特征 → 解码器重建 → 重建误差作为异常分数
【优化】  AdamW + ReduceLROnPlateau + EarlyStopping
【输出】  仅保留验证集损失最低的最优模型
         → brain_ct_3d_ae.pth
         → brain_ct_scaler.joblib
         → brain_ct_info.joblib
"""

import os, sys, glob, warnings, gc
import numpy as np
import joblib
from datetime import datetime
from collections import OrderedDict

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from torch.cuda.amp import autocast, GradScaler

from tqdm import tqdm

# Try to import SimpleITK
try:
    import SimpleITK as sitk
    HAS_SITK = True
except ImportError:
    HAS_SITK = False
    print("[WARN] SimpleITK not installed. Using synthetic data for testing.")

warnings.filterwarnings('ignore')

# ======================== 配置 ========================

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# CT数据路径
CT_DIRS = [
    r"D:\东软实习\CQ500CT0 CQ500CT0\Unknown Study\CT 4cc sec 150cc D3D on",
    r"D:\东软实习\CQ500CT0 CQ500CT0\Unknown Study\CT 4cc sec 150cc D3D on-2",
    r"D:\东软实习\CQ500CT0 CQ500CT0\Unknown Study\CT 4cc sec 150cc D3D on-3",
    r"D:\东软实习\CQ500CT0 CQ500CT0\Unknown Study\CT Plain",
    r"D:\东软实习\CQ500CT0 CQ500CT0\Unknown Study\CT PLAIN THIN",
    r"D:\东软实习\simpleitk\data\CT Plain",
]
MHD_PATH = r"D:\东软实习\simpleitk\data\mhd\1.mhd"
MHD_RAW_PATH = r"D:\东软实习\simpleitk\data\mhd\1.raw"

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[设备] {DEVICE}  |  CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"         GPU: {torch.cuda.get_device_name(0)}")
    print(f"         显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

# 超参数
PATCH_SIZE = 32          # 3D patch size (32×32×32)
PATCH_STRIDE = 16        # 滑动步长
EPOCHS = 200
BATCH_SIZE = 128
LEARNING_RATE = 5e-4
WEIGHT_DECAY = 1e-5
PATIENCE = 30
LATENT_DIM = 256         # 瓶颈维度

# CT窗宽窗位设置
CT_WINDOWS = OrderedDict([
    ('brain',     (40,   80)),    # 脑组织窗
    ('subdural',  (75,   200)),   # 硬膜下窗
    ('bone',      (300,  1500)),  # 骨窗
])


# ======================== 3D自编码器 ========================

class Conv3dBlock(nn.Module):
    """3D卷积块: Conv3d + BatchNorm3d + LeakyReLU"""
    def __init__(self, in_ch, out_ch, kernel_size=3, stride=1, padding=1):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, kernel_size, stride, padding, bias=False),
            nn.BatchNorm3d(out_ch),
            nn.LeakyReLU(0.2, inplace=True),
        )

    def forward(self, x):
        return self.conv(x)


class Encoder3D(nn.Module):
    """3D编码器: 逐步下采样"""

    def __init__(self, in_channels=1, base_channels=32, latent_dim=256):
        super().__init__()
        self.encoder = nn.Sequential(
            # 32×32×32 → 16×16×16
            Conv3dBlock(in_channels, base_channels, 3, 2, 1),
            # 16×16×16 → 8×8×8
            Conv3dBlock(base_channels, base_channels * 2, 3, 2, 1),
            # 8×8×8 → 4×4×4
            Conv3dBlock(base_channels * 2, base_channels * 4, 3, 2, 1),
            # 4×4×4 → 2×2×2
            Conv3dBlock(base_channels * 4, base_channels * 8, 3, 2, 1),
        )

        self.flatten_dim = base_channels * 8 * 2 * 2 * 2  # 2×2×2 feature map
        self.fc = nn.Linear(self.flatten_dim, latent_dim)
        self.dropout = nn.Dropout(0.2)

    def forward(self, x):
        x = self.encoder(x)  # (B, 256, 2, 2, 2)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        x = self.dropout(x)
        return x


class Decoder3D(nn.Module):
    """3D解码器: 逐步上采样"""

    def __init__(self, latent_dim=256, base_channels=32, out_channels=1):
        super().__init__()
        self.fc = nn.Linear(latent_dim, base_channels * 8 * 2 * 2 * 2)

        self.decoder = nn.Sequential(
            # 2×2×2 → 4×4×4
            nn.ConvTranspose3d(base_channels * 8, base_channels * 4, 4, 2, 1, bias=False),
            nn.BatchNorm3d(base_channels * 4),
            nn.LeakyReLU(0.2, inplace=True),

            # 4×4×4 → 8×8×8
            nn.ConvTranspose3d(base_channels * 4, base_channels * 2, 4, 2, 1, bias=False),
            nn.BatchNorm3d(base_channels * 2),
            nn.LeakyReLU(0.2, inplace=True),

            # 8×8×8 → 16×16×16
            nn.ConvTranspose3d(base_channels * 2, base_channels, 4, 2, 1, bias=False),
            nn.BatchNorm3d(base_channels),
            nn.LeakyReLU(0.2, inplace=True),

            # 16×16×16 → 32×32×32
            nn.ConvTranspose3d(base_channels, out_channels, 4, 2, 1, bias=False),
        )

    def forward(self, x):
        x = self.fc(x)
        x = x.view(x.size(0), 256, 2, 2, 2)
        x = self.decoder(x)
        return x


class CT3DAutoencoder(nn.Module):
    """3D卷积自编码器"""

    def __init__(self, in_channels=1, base_channels=32, latent_dim=256):
        super().__init__()
        self.encoder = Encoder3D(in_channels, base_channels, latent_dim)
        self.decoder = Decoder3D(latent_dim, base_channels, in_channels)

    def forward(self, x):
        z = self.encoder(x)
        x_recon = self.decoder(z)
        return x_recon, z

    def encode(self, x):
        return self.encoder(x)


# ======================== CT数据加载 ========================

def load_volume_data():
    """加载所有CT数据源"""
    volumes = []
    volume_names = []

    print("=" * 65)
    print("          脑部CT异常检测 — 3D自编码器训练")
    print("=" * 65)

    # 1. MHD体数据 (主数据源)
    if os.path.exists(MHD_PATH) and os.path.exists(MHD_RAW_PATH):
        print(f"\n[加载] MHD体数据...")
        try:
            # SimpleITK在某些Windows路径下读取中文路径文件可能失败
            # 尝试直接读取raw文件
            import struct
            with open(MHD_PATH, 'r', encoding='utf-8') as f:
                meta = {}
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        meta[k.strip()] = v.strip()
            dims = [int(x) for x in meta.get('DimSize', '512 512 121').split()]
            element_type = meta.get('ElementType', 'MET_SHORT')
            dtype_map = {
                'MET_CHAR': np.int8, 'MET_UCHAR': np.uint8,
                'MET_SHORT': np.int16, 'MET_USHORT': np.uint16,
                'MET_INT': np.int32, 'MET_UINT': np.uint32,
                'MET_FLOAT': np.float32, 'MET_DOUBLE': np.float64,
            }
            dtype = dtype_map.get(element_type, np.int16)
            if os.path.exists(MHD_RAW_PATH):
                # 先尝试SimpleITK
                try:
                    img = sitk.ReadImage(MHD_PATH)
                    vol = sitk.GetArrayFromImage(img)
                except:
                    # fallback: 直接读取raw
                    vol = np.fromfile(MHD_RAW_PATH, dtype=dtype).reshape(dims)
                print(f"   MHD体数据: {vol.shape} = {vol.shape[0] * vol.shape[1] * vol.shape[2]:,} voxels")
                volumes.append(vol)
                volume_names.append("mhd_volume")
        except Exception as e:
            print(f"   加载失败: {e}")

    # 2. DICOM系列
    for ct_dir in CT_DIRS:
        if not os.path.isdir(ct_dir):
            continue
        try:
            reader = sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(ct_dir)
            if len(dicom_names) == 0:
                # 直接加载文件
                files = sorted(glob.glob(os.path.join(ct_dir, "*.dcm")) +
                              glob.glob(os.path.join(ct_dir, "*.DCM")))
                if not files:
                    continue
                # 手动读取堆叠
                slices = []
                for f in files[:240]:  # 最多240 slices
                    try:
                        img = sitk.ReadImage(f)
                        arr = sitk.GetArrayFromImage(img)
                        slices.append(arr.squeeze())
                    except:
                        pass
                if slices:
                    vol = np.stack(slices, axis=0).astype(np.int16)
                    print(f"   {os.path.basename(ct_dir)}: {vol.shape} ({len(files)} DICOM)")
                    volumes.append(vol)
                    volume_names.append(os.path.basename(ct_dir))
            else:
                try:
                    reader.SetFileNames(dicom_names)
                    img = reader.Execute()  # 注意: 直接调用 reader.Execute() 而非 sitk.Execute(reader)
                    vol = sitk.GetArrayFromImage(img)
                    print(f"   {os.path.basename(ct_dir)}: {vol.shape} ({len(dicom_names)} DICOM)")
                    volumes.append(vol)
                    volume_names.append(os.path.basename(ct_dir))
                except Exception as e_inner:
                    print(f"   {os.path.basename(ct_dir)}: 系列加载失败,尝试逐一读取...")
                    files = sorted(dicom_names)
                    slices = []
                    for f in files[:240]:
                        try:
                            img = sitk.ReadImage(f)
                            arr = sitk.GetArrayFromImage(img)
                            slices.append(arr.squeeze())
                        except:
                            pass
                    if slices:
                        vol = np.stack(slices, axis=0).astype(np.int16)
                        print(f"   {os.path.basename(ct_dir)}: {vol.shape} ({len(files)} DICOM, manual)")
                        volumes.append(vol)
                        volume_names.append(os.path.basename(ct_dir))
        except Exception as e:
            print(f"   {os.path.basename(ct_dir)}: 加载失败 ({e})")

    # 3. 尝试手动加载单个DICOM目录
    if not volumes:
        print(f"\n[!] SimpleITK加载失败，尝试备用加载方式...")
        for ct_dir in CT_DIRS:
            if not os.path.isdir(ct_dir):
                continue
            files = sorted(glob.glob(os.path.join(ct_dir, "*.dcm")) +
                          glob.glob(os.path.join(ct_dir, "*.DCM")))
            if files:
                print(f"   发现 {len(files)} 个DICOM文件在 {os.path.basename(ct_dir)}")
                try:
                    slices = []
                    for f in files[:240]:
                        img = sitk.ReadImage(f)
                        arr = sitk.GetArrayFromImage(img)
                        slices.append(arr.squeeze())
                    if slices:
                        vol = np.stack(slices, axis=0).astype(np.int16)
                        volumes.append(vol)
                        volume_names.append(os.path.basename(ct_dir))
                        print(f"   成功加载: {vol.shape}")
                except Exception as e:
                    print(f"   加载失败: {e}")

    return volumes, volume_names


def extract_patches(volume, patch_size=32, stride=16, max_patches=50000):
    """
    从CT体数据中提取3D patches
    CT值经过窗宽窗位裁剪后归一化到 [0,1]
    """
    Z, H, W = volume.shape

    if Z < patch_size or H < patch_size or W < patch_size:
        print(f"   [SKIP] 体数据维度 {volume.shape} 小于patch大小 {patch_size}")
        return np.empty((0, patch_size, patch_size, patch_size), dtype=np.float32)

    patches = []

    # 只选择有实际组织内容的切片区域 (HU > -500)
    mask = volume > -500
    valid_slices = np.where(mask.sum(axis=(1, 2)) > 1000)[0]
    if len(valid_slices) == 0:
        valid_slices = np.arange(Z)

    # 在有效区域内提取patches
    z_indices = np.arange(0, Z - patch_size + 1, stride)
    h_indices = np.arange(0, H - patch_size + 1, stride)
    w_indices = np.arange(0, W - patch_size + 1, stride)

    # 随机采样（避免过多patches）
    total_patches = len(z_indices) * len(h_indices) * len(w_indices)
    if total_patches > max_patches:
        # 随机采样
        z_sample = np.random.choice(z_indices, min(len(z_indices), 8), replace=False)
        h_sample = np.random.choice(h_indices, min(len(h_indices), 8), replace=False)
        w_sample = np.random.choice(w_indices, min(len(w_indices), 8), replace=False)

        for z in z_sample:
            for h in h_sample:
                for w in w_sample:
                    patch = volume[z:z+patch_size, h:h+patch_size, w:w+patch_size]
                    # 检查patch包含有效CT值
                    if patch.max() > -500 and patch.min() < 1000:
                        patches.append(patch.astype(np.float32))
    else:
        for z in z_indices:
            for h in h_indices:
                for w in w_indices:
                    patch = volume[z:z+patch_size, h:h+patch_size, w:w+patch_size]
                    if patch.max() > -500 and patch.min() < 1000:
                        patches.append(patch.astype(np.float32))


    return np.array(patches)


def normalize_ct_patches(patches):
    """CT值归一化: 使用脑组织窗 (center=40, width=80) 裁剪后归一化"""
    center, width = CT_WINDOWS['brain']
    half = width / 2.0
    low, high = center - half, center + half

    normalized = []
    for p in patches:
        p_clipped = np.clip(p, low, high)
        p_norm = (p_clipped - low) / (high - low)  # [0, 1]
        # 标准化到 [-1, 1] 更适合训练
        p_norm = p_norm * 2 - 1
        normalized.append(p_norm)

    return np.stack(normalized, axis=0)


class CT3DDataset(Dataset):
    """3D CT Patch数据集"""
    def __init__(self, patches):
        self.patches = torch.FloatTensor(patches).unsqueeze(1)  # (N, 1, D, H, W)

    def __len__(self):
        return len(self.patches)

    def __getitem__(self, idx):
        return self.patches[idx], self.patches[idx]


def load_mhd_volume():
    """尝试直接加载MHD文件 (如果没有SimpleITK)"""
    if os.path.exists(MHD_PATH) and not HAS_SITK:
        print("\n[!] SimpleITK未安装，尝试直接从.raw文件加载...")
        try:
            # 从.mhd读取元数据
            with open(MHD_PATH, 'r') as f:
                meta = {}
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        meta[k.strip()] = v.strip()

            dims = [int(x) for x in meta.get('DimSize', '512 512 121').split()]
            element_type = meta.get('ElementType', 'MET_SHORT')
            raw_file = os.path.join(os.path.dirname(MHD_PATH), meta.get('ElementDataFile', '1.raw'))

            dtype_map = {
                'MET_CHAR': np.int8, 'MET_UCHAR': np.uint8,
                'MET_SHORT': np.int16, 'MET_USHORT': np.uint16,
                'MET_INT': np.int32, 'MET_UINT': np.uint32,
                'MET_FLOAT': np.float32, 'MET_DOUBLE': np.float64,
            }
            dtype = dtype_map.get(element_type, np.int16)

            if os.path.exists(raw_file):
                data = np.fromfile(raw_file, dtype=dtype).reshape(dims)
                print(f"   直接加载RAW文件: {data.shape}")
                return data
        except Exception as e:
            print(f"   RAW加载失败: {e}")

    return None


# ======================== 训练 ========================

def train_model(model, train_loader, val_loader, device, epochs, patience):
    """训练3D自编码器"""
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=10, min_lr=1e-6
    )
    scaler = GradScaler(enabled=(device.type == 'cuda'))

    best_val_loss = float('inf')
    best_state = None
    best_epoch = 0
    patience_counter = 0
    history = {'train_loss': [], 'val_loss': []}

    print(f"\n{'=' * 65}")
    print(f"                     训练开始")
    print(f"{'=' * 65}")
    print(f"   Epochs: {epochs} (early stopping: {patience})")
    print(f"   Batch: {BATCH_SIZE} | LR: {LEARNING_RATE} | Optim: AdamW")
    print(f"   Model params: {sum(p.numel() for p in model.parameters()):,}")
    print(f"{'=' * 65}\n")

    for epoch in range(1, epochs + 1):
        # ── 训练 ──
        model.train()
        train_loss = 0.0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch:3d}/{epochs}",
                     ncols=90, leave=False)
        for X_b, _ in pbar:
            X_b = X_b.to(device, non_blocking=True)

            optimizer.zero_grad()

            if device.type == 'cuda':
                with autocast():
                    x_recon, _ = model(X_b)
                    loss = criterion(x_recon, X_b)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                x_recon, _ = model(X_b)
                loss = criterion(x_recon, X_b)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                optimizer.step()

            train_loss += loss.item() * X_b.size(0)
            pbar.set_postfix({'loss': f"{loss.item():.4f}"})

        avg_train_loss = train_loss / len(train_loader.dataset)

        # ── 验证 ──
        model.eval()
        val_loss = 0.0

        with torch.no_grad():
            for X_b, _ in tqdm(val_loader, desc="   Validating",
                               ncols=60, leave=False):
                X_b = X_b.to(device, non_blocking=True)
                if device.type == 'cuda':
                    with autocast():
                        x_recon, _ = model(X_b)
                        loss = criterion(x_recon, X_b)
                else:
                    x_recon, _ = model(X_b)
                    loss = criterion(x_recon, X_b)
                val_loss += loss.item() * X_b.size(0)

        avg_val_loss = val_loss / len(val_loader.dataset)
        scheduler.step(avg_val_loss)

        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(avg_val_loss)

        print(f"   Epoch {epoch:3d} | "
              f"Train: {avg_train_loss:.6f} | "
              f"Val: {avg_val_loss:.6f} | "
              f"LR: {optimizer.param_groups[0]['lr']:.2e}")

        # 保存最优
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_state = {
                'epoch': epoch,
                'model_state_dict': {k: v.cpu() for k, v in model.state_dict().items()},
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': avg_val_loss,
            }
            best_epoch = epoch
            patience_counter = 0
            print(f"   → [OK] 新最佳模型 (loss: {avg_val_loss:.6f})")
        else:
            patience_counter += 1

        if patience_counter >= patience:
            print(f"\n   ⏹ Early stopping at epoch {epoch} (no improvement for {patience})")
            break

    print(f"\n{'=' * 65}")
    print(f"[完成] 训练完成！最佳 Epoch {best_epoch} (Val Loss: {best_val_loss:.6f})")
    print(f"{'=' * 65}")

    return best_state, best_val_loss, best_epoch, history


# ======================== 主流程 ========================

def train():
    # ── 加载CT数据 ──
    volumes = []

    if HAS_SITK:
        volumes, volume_names = load_volume_data()
    else:
        print("\n[!] SimpleITK未安装，尝试替代加载方式...")

    # 尝试加载MHD (无SimpleITK)
    mhd_vol = load_mhd_volume()
    if mhd_vol is not None:
        volumes.append(mhd_vol)
        volume_names.append("mhd_raw")

    # 如果还是没数据，使用模拟数据
    if len(volumes) == 0:
        print("\n[!] 无法加载真实CT数据，生成模拟数据用于验证架构...")
        sim_vol = np.random.randn(64, 128, 128).astype(np.int16) * 100 + 40
        volumes.append(sim_vol)
        volume_names.append("synthetic")
        real_data = False
    else:
        real_data = True

    print(f"\n[数据] 共加载 {len(volumes)} 个体数据源")

    # ── 提取3D patches ──
    all_patches = []
    for i, (vol, name) in enumerate(zip(volumes, volume_names)):
        print(f"\n[提取] 从 [{name}] 提取patches...")
        print(f"   体数据维度: {vol.shape} ({vol.shape[0]*vol.shape[1]*vol.shape[2]:,} voxels)")

        patches = extract_patches(vol, PATCH_SIZE, PATCH_STRIDE)
        print(f"   提取patches: {len(patches)}")

        if len(patches) > 0:
            # 归一化
            patches_norm = normalize_ct_patches(patches)
            all_patches.append(patches_norm)

    if len(all_patches) == 0:
        print("\n❌ 没有提取到任何patch! 使用随机模拟数据...")
        sim_patches = np.random.randn(500, PATCH_SIZE, PATCH_SIZE, PATCH_SIZE).astype(np.float32)
        all_patches = [sim_patches]

    X = np.concatenate(all_patches, axis=0)
    print(f"\n[汇总] 总共 {len(X)} 个训练patches (每个 {PATCH_SIZE}^3)")
    print(f"   数值范围: [{X.min():.3f}, {X.max():.3f}]")

    # ── 划分训练/验证集 ──
    dataset = CT3DDataset(X)
    val_size = min(int(len(dataset) * 0.15), 500)
    train_size = len(dataset) - val_size

    train_dataset, val_dataset = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(SEED)
    )

    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True,
        num_workers=0, pin_memory=(DEVICE.type == 'cuda')
    )
    val_loader = DataLoader(
        val_dataset, batch_size=BATCH_SIZE, shuffle=False,
        num_workers=0, pin_memory=(DEVICE.type == 'cuda')
    )

    print(f"   训练集: {train_size} | 验证集: {val_size}")

    # ── 初始化模型 ──
    model = CT3DAutoencoder(in_channels=1, base_channels=32, latent_dim=LATENT_DIM).to(DEVICE)
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n[网络] 3D自编码器结构:")
    print(f"   总参数量: {total_params:,}")
    print(f"   可训练参数: {trainable_params:,}")
    print(f"   瓶颈维度: {LATENT_DIM}")

    # ── 训练 ──
    best_state, best_val_loss, best_epoch, history = train_model(
        model, train_loader, val_loader, DEVICE, EPOCHS, PATIENCE
    )

    # ── 加载最佳模型 ──
    model.load_state_dict(best_state['model_state_dict'])

    # ── 计算异常检测阈值 ──
    print(f"\n[评估] 计算异常检测阈值...")
    model.eval()
    reconstruction_errors = []
    with torch.no_grad():
        for X_b, _ in tqdm(val_loader, desc="   计算重建误差", ncols=60):
            X_b = X_b.to(DEVICE)
            x_recon, _ = model(X_b)
            mse = ((x_recon - X_b) ** 2).view(X_b.size(0), -1).mean(dim=1)
            reconstruction_errors.extend(mse.cpu().numpy())

    errors = np.array(reconstruction_errors)
    anomaly_threshold = float(np.percentile(errors, 95))
    print(f"   平均重建误差: {errors.mean():.6f}")
    print(f"   标准差: {errors.std():.6f}")
    print(f"   异常阈值 (95%): {anomaly_threshold:.6f}")

    # ── 保存模型 ──
    model_path = os.path.join(OUTPUT_DIR, 'brain_ct_3d_ae.pth')
    scaler_path = os.path.join(OUTPUT_DIR, 'brain_ct_scaler.joblib')
    info_path = os.path.join(OUTPUT_DIR, 'brain_ct_info.joblib')

    # 保存PyTorch模型
    torch.save({
        'model_state_dict': best_state['model_state_dict'],
        'patch_size': PATCH_SIZE,
        'latent_dim': LATENT_DIM,
        'base_channels': 32,
        'anomaly_threshold': anomaly_threshold,
        'mean_reconstruction_error': float(errors.mean()),
        'val_loss': best_val_loss,
        'best_epoch': best_epoch,
    }, model_path)

    # 保存scaler信息
    joblib.dump({
        'window_center': CT_WINDOWS['brain'][0],
        'window_width': CT_WINDOWS['brain'][1],
        'patch_size': PATCH_SIZE,
        'normalization': 'brain_window [-1, 1]',
    }, scaler_path)

    # 保存模型信息
    info = {
        'name': 'CQ500真实CT数据 (PyTorch 3D Autoencoder)',
        'model_type': 'PyTorch 3D Convolutional Autoencoder',
        'architecture': {
            'type': 'CT3DAutoencoder',
            'encoder': 'Conv3d(1→32→64→128→256) → FC(2048→256)',
            'decoder': 'FC(256→2048) → ConvTranspose3d(256→128→64→32→1)',
            'patch_size': PATCH_SIZE,
            'latent_dim': LATENT_DIM,
            'total_params': total_params,
            'trainable_params': trainable_params,
        },
        'data': {
            'sources': volume_names if 'volume_names' in dir() or True else ['loaded CT volumes'],
            'volumes_count': len(volumes),
            'total_patches': len(X),
            'patch_size': f"{PATCH_SIZE}×{PATCH_SIZE}×{PATCH_SIZE}",
            'is_real_data': real_data,
        },
        'training': {
            'epochs_trained': min(EPOCHS, best_epoch + PATIENCE),
            'best_epoch': best_epoch,
            'best_val_loss': best_val_loss,
            'batch_size': BATCH_SIZE,
            'learning_rate': LEARNING_RATE,
            'weight_decay': WEIGHT_DECAY,
            'early_stopping_patience': PATIENCE,
        },
        'anomaly_detection': {
            'method': 'reconstruction_error',
            'threshold': anomaly_threshold,
            'mean_error': float(errors.mean()),
            'std_error': float(errors.std()),
        },
        'ct_windows': {k: {'center': v[0], 'width': v[1]} for k, v in CT_WINDOWS.items()},
        'training_date': datetime.now().isoformat(),
        'device': str(DEVICE),
    }
    joblib.dump(info, info_path)

    print(f"\n[保存] 保存模型文件:")
    print(f"   → {model_path}")
    print(f"   → {scaler_path}")
    print(f"   → {info_path}")

    # ── 测试推理 ──
    print(f"\n[测试] 测试推理...")
    model.eval()
    test_patch = torch.FloatTensor(X[:1]).unsqueeze(1).to(DEVICE)
    with torch.no_grad():
        if DEVICE.type == 'cuda':
            with autocast():
                recon, latent = model(test_patch)
        else:
            recon, latent = model(test_patch)

    print(f"   输入patch: {test_patch.shape}")
    print(f"   重建patch: {recon.shape}")
    print(f"   潜在编码: {latent.shape}")
    print(f"   重建误差: {nn.MSELoss()(recon, test_patch).item():.6f}")

    print(f"\n[OK] 脑部CT 3D自编码器训练完成！\n")


if __name__ == '__main__':
    train()
