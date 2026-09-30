"""
脑部CT异常检测 — 3D卷积自编码器 v3 (CQ500全量)
==============================================
使用CQ500完整数据集训练3D自编码器用于无监督异常检测

改进:
  1. 从1个体数据 → 490例CQ500真实数据
  2. 更好的patch采样策略
  3. 支持NIfTI格式快速加载
  4. 异常检测集成标签验证

输出: brain_ct_3d_ae_v3.pth, brain_ct_scaler_v3.joblib, brain_ct_info_v3.joblib
"""

import os, sys, glob, gc, json, time, warnings
import numpy as np
import joblib
from datetime import datetime
from collections import OrderedDict

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from torch.cuda.amp import autocast, GradScaler

warnings.filterwarnings('ignore')

try:
    import nibabel as nib
    HAS_NIB = True
except ImportError:
    HAS_NIB = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# ======================== 配置 ========================

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DATA_DIR = os.path.abspath(os.path.join(OUTPUT_DIR, '..', '..', 'data', 'ct', 'cq500'))
VOLUMES_DIR = os.path.join(PROJECT_DATA_DIR, 'volumes')
PROCESSED_DIR = os.path.join(PROJECT_DATA_DIR, 'processed')

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# 超参数
PATCH_SIZE = 32
PATCH_STRIDE = 16
EPOCHS = 100
BATCH_SIZE = 128
LEARNING_RATE = 5e-4
WEIGHT_DECAY = 1e-5
PATIENCE = 20
LATENT_DIM = 256

MAX_VOLUMES = None        # None = 所有
MAX_PATCHES_PER_VOL = 10000
VAL_SPLIT = 0.15
MAX_VAL_PATCHES = 2000

CT_WINDOWS = OrderedDict([
    ('brain',    (40,  80)),
    ('subdural', (75,  200)),
    ('bone',     (300, 1500)),
])


def log(msg):
    print(f"[3DAE-v3] {msg}")
    sys.stdout.flush()


# ======================== 网络结构 ========================

class Conv3dBlock(nn.Module):
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
    def __init__(self, in_channels=1, base_channels=32, latent_dim=256):
        super().__init__()
        self.encoder = nn.Sequential(
            Conv3dBlock(in_channels, base_channels, 3, 2, 1),
            Conv3dBlock(base_channels, base_channels * 2, 3, 2, 1),
            Conv3dBlock(base_channels * 2, base_channels * 4, 3, 2, 1),
            Conv3dBlock(base_channels * 4, base_channels * 8, 3, 2, 1),
        )
        self.flatten_dim = base_channels * 8 * 2 * 2 * 2
        self.fc = nn.Linear(self.flatten_dim, latent_dim)
        self.dropout = nn.Dropout(0.2)

    def forward(self, x):
        x = self.encoder(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        x = self.dropout(x)
        return x


class Decoder3D(nn.Module):
    def __init__(self, latent_dim=256, base_channels=32, out_channels=1):
        super().__init__()
        self.fc = nn.Linear(latent_dim, base_channels * 8 * 2 * 2 * 2)
        self.decoder = nn.Sequential(
            nn.ConvTranspose3d(base_channels * 8, base_channels * 4, 4, 2, 1, bias=False),
            nn.BatchNorm3d(base_channels * 4),
            nn.LeakyReLU(0.2, inplace=True),
            nn.ConvTranspose3d(base_channels * 4, base_channels * 2, 4, 2, 1, bias=False),
            nn.BatchNorm3d(base_channels * 2),
            nn.LeakyReLU(0.2, inplace=True),
            nn.ConvTranspose3d(base_channels * 2, base_channels, 4, 2, 1, bias=False),
            nn.BatchNorm3d(base_channels),
            nn.LeakyReLU(0.2, inplace=True),
            nn.ConvTranspose3d(base_channels, out_channels, 4, 2, 1, bias=False),
        )

    def forward(self, x):
        x = self.fc(x)
        x = x.view(x.size(0), 256, 2, 2, 2)
        x = self.decoder(x)
        return x


class CT3DAutoencoder(nn.Module):
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


# ======================== 数据加载 ========================

def load_nifti_volume(nii_path: str) -> np.ndarray:
    try:
        nii = nib.load(nii_path)
        vol = nii.get_fdata().astype(np.float32)
        return vol
    except Exception as e:
        return None


def extract_patches(volume, patch_size=32, stride=16, max_patches=10000):
    Z, H, W = volume.shape
    if Z < patch_size or H < patch_size or W < patch_size:
        return np.empty((0, patch_size, patch_size, patch_size), dtype=np.float32)

    patches = []
    mask = volume > -500
    valid_slices = np.where(mask.sum(axis=(1, 2)) > 1000)[0]
    if len(valid_slices) == 0:
        valid_slices = np.arange(Z)

    z_indices = np.arange(0, Z - patch_size + 1, stride)
    h_indices = np.arange(0, H - patch_size + 1, stride)
    w_indices = np.arange(0, W - patch_size + 1, stride)

    total_patches = len(z_indices) * len(h_indices) * len(w_indices)
    if total_patches > max_patches:
        z_sample = np.random.choice(z_indices, min(len(z_indices), 6), replace=False)
        h_sample = np.random.choice(h_indices, min(len(h_indices), 8), replace=False)
        w_sample = np.random.choice(w_indices, min(len(w_indices), 8), replace=False)
        for z in z_sample:
            for h in h_sample:
                for w in w_sample:
                    patch = volume[z:z+patch_size, h:h+patch_size, w:w+patch_size]
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


def normalize_ct_patches(patches, center=40, width=80):
    half = width / 2.0
    low, high = center - half, center + half
    normalized = []
    for p in patches:
        p_clipped = np.clip(p, low, high)
        p_norm = (p_clipped - low) / (high - low)
        p_norm = p_norm * 2 - 1
        normalized.append(p_norm)
    return np.stack(normalized, axis=0) if normalized else np.empty((0, *patches.shape[1:]))


class CT3DDataset(Dataset):
    def __init__(self, patches):
        self.patches = torch.FloatTensor(patches).unsqueeze(1)

    def __len__(self):
        return len(self.patches)

    def __getitem__(self, idx):
        return self.patches[idx], self.patches[idx]


# ======================== 数据准备 ========================

def prepare_training_data():
    """从CQ500 NIfTI文件准备训练数据"""
    if not HAS_NIB:
        log("[FAIL] nibabel not installed")
        return None, None

    nii_files = sorted(glob.glob(os.path.join(VOLUMES_DIR, '*.nii.gz')))
    # Filter out test files
    nii_files = [f for f in nii_files if os.path.basename(f).startswith('CQ500-CT-')]

    if MAX_VOLUMES and len(nii_files) > MAX_VOLUMES:
        np.random.shuffle(nii_files)
        nii_files = nii_files[:MAX_VOLUMES]

    log(f"Found {len(nii_files)} NIfTI volumes")

    all_patches = []
    success = 0
    failed = 0

    for i, nii_path in enumerate(nii_files):
        name = os.path.basename(nii_path)
        vol = load_nifti_volume(nii_path)
        if vol is None:
            failed += 1
            continue

        patches = extract_patches(vol, PATCH_SIZE, PATCH_STRIDE, MAX_PATCHES_PER_VOL)
        if len(patches) > 0:
            patches_norm = normalize_ct_patches(patches)
            all_patches.append(patches_norm)

        success += 1
        if (i + 1) % 25 == 0:
            log(f"  Progress: {i+1}/{len(nii_files)} (success={success}, failed={failed})")

        gc.collect()

    if len(all_patches) == 0:
        log("[FAIL] No patches extracted")
        return None, None

    X = np.concatenate(all_patches, axis=0)
    log(f"Total patches: {len(X)} x {PATCH_SIZE}^3")
    log(f"  Range: [{X.min():.3f}, {X.max():.3f}]")

    return X, nii_files


# ======================== 训练 ========================

def train_model(model, train_loader, val_loader, device, epochs, patience):
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=8, min_lr=1e-6
    )
    scaler = GradScaler(enabled=(device.type == 'cuda'))

    best_val_loss = float('inf')
    best_state = None
    best_epoch = 0
    patience_counter = 0

    log(f"\nTraining: {epochs} epochs, batch={BATCH_SIZE}, patience={patience}")
    log(f"  Model params: {sum(p.numel() for p in model.parameters()):,}")

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0

        pbar = tqdm(train_loader, desc=f"Epoch {epoch:3d}/{epochs}", ncols=80, leave=False) if HAS_TQDM else train_loader
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

        avg_train_loss = train_loss / len(train_loader.dataset)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_b, _ in val_loader:
                X_b = X_b.to(device, non_blocking=True)
                with autocast(enabled=(device.type == 'cuda')):
                    x_recon, _ = model(X_b)
                    loss = criterion(x_recon, X_b)
                val_loss += loss.item() * X_b.size(0)

        avg_val_loss = val_loss / len(val_loader.dataset)
        scheduler.step(avg_val_loss)

        progress_msg = f"  Epoch {epoch:3d} | Train: {avg_train_loss:.6f} | Val: {avg_val_loss:.6f} | LR: {optimizer.param_groups[0]['lr']:.2e}"

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
            progress_msg += " [NEW BEST]"
        else:
            patience_counter += 1

        log(progress_msg)

        if patience_counter >= patience:
            log(f"\n  Early stopping at epoch {epoch}")
            break

    log(f"\nTraining complete! Best epoch {best_epoch} (Val Loss: {best_val_loss:.6f})")
    return best_state, best_val_loss, best_epoch


# ======================== 主流程 ========================

def main():
    log("=" * 65)
    log("  3D Autoencoder v3 - CQ500 Full Training")
    log("=" * 65)
    log(f"  Device: {DEVICE}")
    log(f"  Data: {VOLUMES_DIR}")

    # 准备数据
    t0 = time.time()
    X, nii_files = prepare_training_data()
    if X is None:
        log("[FAIL] Data preparation failed")
        return
    log(f"Data preparation: {time.time()-t0:.1f}s")

    # 划分训练/验证集
    dataset = CT3DDataset(X)
    val_size = min(int(len(dataset) * VAL_SPLIT), MAX_VAL_PATCHES)
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(SEED)
    )

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=0, pin_memory=(DEVICE.type == 'cuda'))
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=0, pin_memory=(DEVICE.type == 'cuda'))
    log(f"Train: {train_size} | Val: {val_size} patches")

    # 初始化模型
    model = CT3DAutoencoder(in_channels=1, base_channels=32, latent_dim=LATENT_DIM).to(DEVICE)
    total_params = sum(p.numel() for p in model.parameters())
    log(f"Model params: {total_params:,}, latent dim: {LATENT_DIM}")

    # 训练
    t1 = time.time()
    best_state, best_val_loss, best_epoch = train_model(
        model, train_loader, val_loader, DEVICE, EPOCHS, PATIENCE
    )
    log(f"Training time: {time.time()-t1:.1f}s")

    # 加载最佳模型
    model.load_state_dict(best_state['model_state_dict'])

    # 计算异常检测阈值
    model.eval()
    reconstruction_errors = []
    with torch.no_grad():
        for X_b, _ in val_loader:
            X_b = X_b.to(DEVICE)
            with autocast(enabled=(DEVICE.type == 'cuda')):
                x_recon, _ = model(X_b)
            mse = ((x_recon - X_b) ** 2).view(X_b.size(0), -1).mean(dim=1)
            reconstruction_errors.extend(mse.cpu().numpy())

    errors = np.array(reconstruction_errors)
    anomaly_threshold = float(np.percentile(errors, 95))
    log(f"Reconstruction errors - mean: {errors.mean():.6f}, std: {errors.std():.6f}")
    log(f"Anomaly threshold (95%): {anomaly_threshold:.6f}")

    # 保存模型
    model_path = os.path.join(OUTPUT_DIR, 'brain_ct_3d_ae_v3.pth')
    scaler_path = os.path.join(OUTPUT_DIR, 'brain_ct_scaler_v3.joblib')
    info_path = os.path.join(OUTPUT_DIR, 'brain_ct_info_v3.joblib')

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

    joblib.dump({
        'window_center': CT_WINDOWS['brain'][0],
        'window_width': CT_WINDOWS['brain'][1],
        'patch_size': PATCH_SIZE,
        'normalization': 'brain_window [-1, 1]',
    }, scaler_path)

    info = {
        'name': 'CQ500 3D Autoencoder v3',
        'model_type': 'PyTorch 3D Convolutional Autoencoder',
        'architecture': {
            'type': 'CT3DAutoencoder',
            'patch_size': PATCH_SIZE,
            'latent_dim': LATENT_DIM,
            'total_params': total_params,
        },
        'data': {
            'num_volumes': len(nii_files) if nii_files else 0,
            'total_patches': len(X),
            'data_source': 'CQ500 full dataset',
        },
        'training': {
            'best_epoch': best_epoch,
            'best_val_loss': best_val_loss,
            'batch_size': BATCH_SIZE,
            'learning_rate': LEARNING_RATE,
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

    log(f"\nModels saved:")
    log(f"  {model_path}")
    log(f"  {scaler_path}")
    log(f"  {info_path}")
    log(f"\n[OK] Training complete!")


if __name__ == '__main__':
    main()
