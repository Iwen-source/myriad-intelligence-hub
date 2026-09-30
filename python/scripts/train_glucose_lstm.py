"""
血糖时序预测 — 双向LSTM训练脚本 (PyTorch + CUDA)
===============================================
【数据源】9位患者真实CGM连续血糖监测数据 (~8230条, 5分钟间隔)
【架构】  双层BiLSTM + 滑动窗口 (12步输入 → 1/6/12步输出)
【优化】  AdamW + ReduceLROnPlateau + EarlyStopping
【输出】  仅保留验证集损失最低的最优模型
         → glucose_lstm_30min.pth  (预测30分钟)
         → glucose_lstm_60min.pth  (预测60分钟)
         → glucose_scaler.joblib
         → glucose_info.joblib
"""

import os, sys, warnings
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from tqdm import tqdm

warnings.filterwarnings('ignore')

# ======================== 配置 ========================

DATA_DIR = r'D:\东软实习\相关性分析_胰岛素_血糖'
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

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

# 超参数
LOOKBACK = 12           # 使用过去12个点预测
STEP_SIZE = 1            # 滑动步长 (用于数据增强)
FORWARD_30 = 6           # 30分钟 = 6步
FORWARD_60 = 12          # 60分钟 = 12步

EPOCHS = 300
BATCH_SIZE = 64
LEARNING_RATE = 5e-4
WEIGHT_DECAY = 1e-5
PATIENCE = 40
HIDDEN_SIZE = 128
NUM_LAYERS = 2
DROPOUT = 0.3

GLUCOSE_FILES = [f'glucose_{i:02d}.csv' for i in range(1, 10)]


# ======================== LSTM模型定义 ========================

class GlucoseBiLSTM(nn.Module):
    """血糖预测双向LSTM"""

    def __init__(self, input_size=1, hidden_size=128, num_layers=2,
                 dropout=0.3, output_steps=1):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.output_steps = output_steps

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )

        lstm_out = hidden_size * 2  # bidir

        self.attention = nn.Sequential(
            nn.Linear(lstm_out, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
            nn.Softmax(dim=1)
        )

        self.regressor = nn.Sequential(
            nn.Linear(lstm_out, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout * 0.5),
            nn.Linear(64, 32),
            nn.ReLU(inplace=True),
            nn.Linear(32, output_steps),
        )

        self._init_weights()

    def _init_weights(self):
        for name, param in self.lstm.named_parameters():
            if 'weight_ih' in name:
                nn.init.orthogonal_(param)
            elif 'weight_hh' in name:
                nn.init.orthogonal_(param)
            elif 'bias' in name:
                nn.init.constant_(param, 0)
                # 设置遗忘门偏置为1
                n = param.size(0)
                start, end = n // 4, n // 2
                param.data[start:end].fill_(1.0)

        for m in self.regressor:
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x):
        # x: (batch, seq_len, 1)
        lstm_out, (h_n, c_n) = self.lstm(x)
        # lstm_out: (batch, seq_len, hidden*2)

        # 注意力机制
        attn_weights = self.attention(lstm_out)  # (batch, seq_len, 1)
        context = torch.sum(attn_weights * lstm_out, dim=1)  # (batch, hidden*2)

        output = self.regressor(context)
        return output


# ======================== 数据加载 ========================

def load_cgm_data():
    """加载所有患者CGM数据"""
    print("=" * 65)
    print("          血糖时序预测 — 双向LSTM训练")
    print("=" * 65)

    all_series = []
    stats = []

    for fname in GLUCOSE_FILES:
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            print(f"   [WARN] 跳过: {fname} (文件不存在)")
            continue

        df = pd.read_csv(fpath, parse_dates=[[0, 1]])
        df.rename(columns={df.columns[0]: 'datetime', 'glucose': 'glucose'}, inplace=True)
        df.sort_values('datetime', inplace=True)
        df['glucose'] = pd.to_numeric(df['glucose'], errors='coerce')
        df.dropna(subset=['glucose'], inplace=True)

        g = df['glucose'].values
        pid = fname.replace('glucose_', '').replace('.csv', '')

        stats.append({
            'patient': pid, 'count': len(g),
            'min': float(g.min()), 'max': float(g.max()),
            'mean': float(g.mean()), 'std': float(g.std())
        })
        all_series.append(g)
        print(f"   患者 {pid}: {len(g):>5} 条 | "
              f"均值={g.mean():.2f} | "
              f"[{g.min():.1f}, {g.max():.1f}] mmol/L")

    total = sum(s['count'] for s in stats)
    print(f"\n   总计: {total} 条数据 | 患者数: {len(all_series)}")
    return all_series, stats


def create_sliding_windows_multi(series_list, lookback=12, forward_steps=(6, 12), step=1):
    """
    从多个时序创建滑动窗口样本
    按患者划分: 患者1-7训练, 8-9验证
    """
    # 70/30 患者级划分
    n_patients = len(series_list)
    n_train = max(1, int(n_patients * 0.7))

    train_series = series_list[:n_train]
    val_series = series_list[n_train:]

    print(f"\n  [数据集划分 (按患者)]:")
    print(f"   训练集: 患者 {n_train} 个")
    print(f"   验证集: 患者 {n_patients - n_train} 个")

    def _build_from_list(series, prefix=""):
        X, y_30, y_60 = [], [], []
        for pid, s in enumerate(series):
            n = len(s)
            if n < lookback + max(forward_steps):
                continue
            for i in range(lookback, n - max(forward_steps), step):
                X.append(s[i - lookback:i])
                y_30.append(s[i + forward_steps[0] - 1] if i + forward_steps[0] <= n else s[-1])
                y_60.append(s[i + forward_steps[1] - 1] if i + forward_steps[1] <= n else s[-1])

        return np.array(X, dtype=np.float32), np.array(y_30, dtype=np.float32), np.array(y_60, dtype=np.float32)

    X_train, y30_train, y60_train = _build_from_list(train_series)
    X_val, y30_val, y60_val = _build_from_list(val_series)

    print(f"   训练集样本: {len(X_train)}")
    print(f"   验证集样本: {len(X_val)}")

    return (X_train, y30_train, y60_train), (X_val, y30_val, y60_val)


# ======================== 训练函数 ========================

def train_model(model, train_loader, val_loader, criterion, optimizer,
                scheduler, device, epochs, patience, model_name):
    """训练单个预测步长模型"""
    best_val_loss = float('inf')
    best_state = None
    best_epoch = 0
    patience_counter = 0
    history = {'train_loss': [], 'val_loss': []}

    print(f"\n{'=' * 55}")
    print(f"  [训练] {model_name}")
    print(f"{'=' * 55}")

    for epoch in range(1, epochs + 1):
        # ── 训练 ──
        model.train()
        train_loss = 0.0
        for X_b, y_b in train_loader:
            X_b = X_b.to(device).unsqueeze(-1)  # (batch, seq, 1)
            y_b = y_b.to(device)

            optimizer.zero_grad()
            outputs = model(X_b)
            loss = criterion(outputs, y_b.unsqueeze(-1) if outputs.size(-1) == 1 else y_b)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            train_loss += loss.item() * X_b.size(0)

        avg_train_loss = train_loss / len(train_loader.dataset)

        # ── 验证 ──
        model.eval()
        val_loss = 0.0
        all_preds, all_targets = [], []

        with torch.no_grad():
            for X_b, y_b in val_loader:
                X_b = X_b.to(device).unsqueeze(-1)
                y_b = y_b.to(device)
                outputs = model(X_b)
                loss = criterion(outputs, y_b.unsqueeze(-1) if outputs.size(-1) == 1 else y_b)
                val_loss += loss.item() * X_b.size(0)

                preds = outputs.squeeze().cpu().numpy()
                if outputs.size(-1) == 1:
                    all_preds.extend([preds]) if isinstance(preds, np.float32) else all_preds.extend(preds.flatten())
                all_targets.extend(y_b.cpu().numpy())

        avg_val_loss = val_loss / len(val_loader.dataset)

        if isinstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
            scheduler.step(avg_val_loss)
        else:
            scheduler.step()

        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(avg_val_loss)

        # 显示进度
        if epoch % 10 == 0 or epoch == 1 or epoch == epochs:
            print(f"   Epoch {epoch:3d}/{epochs} | "
                  f"Train Loss: {avg_train_loss:.4f} | "
                  f"Val Loss: {avg_val_loss:.4f} | "
                  f"LR: {optimizer.param_groups[0]['lr']:.2e}")

        # 保存最优
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_state = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': avg_val_loss,
            }
            best_epoch = epoch
            patience_counter = 0
        else:
            patience_counter += 1

        if patience_counter >= patience:
            print(f"   [Early stopping] at epoch {epoch}")
            break

    print(f"\n   [完成] {model_name} ！最佳 Epoch {best_epoch}, Val Loss: {best_val_loss:.4f}")
    return best_state, best_val_loss, best_epoch, history


# ======================== 主流程 ========================

def train():
    # ── 加载数据 ──
    all_series, stats = load_cgm_data()

    # ── 创建滑动窗口 ──
    (X_train, y30_train, y60_train), (X_val, y30_val, y60_val) = \
        create_sliding_windows_multi(all_series, LOOKBACK, (FORWARD_30, FORWARD_60), STEP_SIZE)

    # ── 标准化 (对每个样本独立归一化更合理) ──
    # 使用全局scaler
    scaler_30 = StandardScaler()
    scaler_60 = StandardScaler()

    # Reshape for scaler: (n_samples, lookback)
    X_train_flat = X_train.reshape(X_train.shape[0], -1)
    X_val_flat = X_val.reshape(X_val.shape[0], -1)

    X_train_scaled = scaler_30.fit_transform(X_train_flat).reshape(X_train.shape)
    X_val_scaled = scaler_30.transform(X_val_flat).reshape(X_val.shape)

    # 对y也做标准化 (反标准化时恢复)
    y30_mean, y30_std = y30_train.mean(), y30_train.std() + 1e-8
    y60_mean, y60_std = y60_train.mean(), y60_train.std() + 1e-8

    y30_train_norm = (y30_train - y30_mean) / y30_std
    y30_val_norm = (y30_val - y30_mean) / y30_std
    y60_train_norm = (y60_train - y60_mean) / y60_std
    y60_val_norm = (y60_val - y60_mean) / y60_std

    # ── DataLoader ──
    train_30_loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_train_scaled), torch.FloatTensor(y30_train_norm)),
        batch_size=BATCH_SIZE, shuffle=True
    )
    val_30_loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_val_scaled), torch.FloatTensor(y30_val_norm)),
        batch_size=BATCH_SIZE, shuffle=False
    )
    train_60_loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_train_scaled), torch.FloatTensor(y60_train_norm)),
        batch_size=BATCH_SIZE, shuffle=True
    )
    val_60_loader = DataLoader(
        TensorDataset(torch.FloatTensor(X_val_scaled), torch.FloatTensor(y60_val_norm)),
        batch_size=BATCH_SIZE, shuffle=False
    )

    # ── 训练30分钟预测模型 ──
    model_30 = GlucoseBiLSTM(
        input_size=1, hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS, dropout=DROPOUT, output_steps=1
    ).to(DEVICE)

    n_params_30 = sum(p.numel() for p in model_30.parameters())
    print(f"\n  30分钟模型参数量: {n_params_30:,}")

    criterion_30 = nn.MSELoss()
    optimizer_30 = optim.AdamW(model_30.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler_30 = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer_30, mode='min', factor=0.5, patience=15, min_lr=1e-6
    )

    best_30_state, best_30_loss, best_30_epoch, hist_30 = train_model(
        model_30, train_30_loader, val_30_loader, criterion_30,
        optimizer_30, scheduler_30, DEVICE, EPOCHS, PATIENCE, "30分钟预测模型"
    )

    # ── 训练60分钟预测模型 ──
    model_60 = GlucoseBiLSTM(
        input_size=1, hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS, dropout=DROPOUT, output_steps=1
    ).to(DEVICE)

    n_params_60 = sum(p.numel() for p in model_60.parameters())
    print(f"  60分钟模型参数量: {n_params_60:,}")

    criterion_60 = nn.MSELoss()
    optimizer_60 = optim.AdamW(model_60.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler_60 = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer_60, mode='min', factor=0.5, patience=15, min_lr=1e-6
    )

    best_60_state, best_60_loss, best_60_epoch, hist_60 = train_model(
        model_60, train_60_loader, val_60_loader, criterion_60,
        optimizer_60, scheduler_60, DEVICE, EPOCHS, PATIENCE, "60分钟预测模型"
    )

    # ── 评估 ──
    print(f"\n{'=' * 65}")
    print("                   模型评估")
    print(f"{'=' * 65}")

    def evaluate_model(model, state_dict, loader, y_mean, y_std, desc=""):
        model.load_state_dict(state_dict['model_state_dict'])
        model.eval()
        all_preds, all_targets = [], []
        with torch.no_grad():
            for X_b, y_b in loader:
                X_b = X_b.to(DEVICE).unsqueeze(-1)
                outputs = model(X_b).squeeze().cpu().numpy()
                if outputs.ndim == 0:
                    outputs = np.array([outputs])
                preds = outputs * y_std + y_mean
                targets = y_b.numpy() * y_std + y_mean
                all_preds.extend(preds.flatten())
                all_targets.extend(targets.flatten())

        all_preds = np.array(all_preds)
        all_targets = np.array(all_targets)

        mae = mean_absolute_error(all_targets, all_preds)
        rmse = np.sqrt(mean_squared_error(all_targets, all_preds))
        r2 = r2_score(all_targets, all_preds)

        print(f"\n  {desc}:")
        print(f"    MAE:  {mae:.3f} mmol/L")
        print(f"    RMSE: {rmse:.3f} mmol/L")
        print(f"    R2:   {r2:.4f}")

        return {'mae': float(mae), 'rmse': float(rmse), 'r2': float(r2)}

    metrics_30 = evaluate_model(model_30, best_30_state, val_30_loader,
                                 y30_mean, y30_std, "30分钟血糖预测")
    metrics_60 = evaluate_model(model_60, best_60_state, val_60_loader,
                                 y60_mean, y60_std, "60分钟血糖预测")

    # ── 保存模型 ──
    print(f"\n  [保存模型文件...]")

    model_30_path = os.path.join(OUTPUT_DIR, 'glucose_lstm_30min.pth')
    model_60_path = os.path.join(OUTPUT_DIR, 'glucose_lstm_60min.pth')
    scaler_path = os.path.join(OUTPUT_DIR, 'glucose_scaler.joblib')
    info_path = os.path.join(OUTPUT_DIR, 'glucose_info.joblib')

    torch.save({
        'model_state_dict': best_30_state['model_state_dict'],
        'input_size': 1,
        'hidden_size': HIDDEN_SIZE,
        'num_layers': NUM_LAYERS,
        'dropout': DROPOUT,
        'output_steps': 1,
        'lookback': LOOKBACK,
        'forward_steps': FORWARD_30,
        'y_mean': float(y30_mean),
        'y_std': float(y30_std),
        'val_loss': best_30_loss,
    }, model_30_path)

    torch.save({
        'model_state_dict': best_60_state['model_state_dict'],
        'input_size': 1,
        'hidden_size': HIDDEN_SIZE,
        'num_layers': NUM_LAYERS,
        'dropout': DROPOUT,
        'output_steps': 1,
        'lookback': LOOKBACK,
        'forward_steps': FORWARD_60,
        'y_mean': float(y60_mean),
        'y_std': float(y60_std),
        'val_loss': best_60_loss,
    }, model_60_path)

    # 保存scaler (共享)
    scaler_info = {
        'x_mean': X_train_flat.mean(axis=0).tolist(),
        'x_std': X_train_flat.std(axis=0).tolist(),
        'lookback': LOOKBACK,
    }
    joblib.dump(scaler_info, scaler_path)

    # 模型信息
    info = {
        'name': '9患者真实CGM血糖数据 (PyTorch BiLSTM)',
        'model_type': 'PyTorch Bidirectional LSTM with Attention',
        'architecture': {
            'type': 'GlucoseBiLSTM',
            'lookback': LOOKBACK,
            'hidden_size': HIDDEN_SIZE,
            'num_layers': NUM_LAYERS,
            'bidirectional': True,
            'attention': True,
            'dropout': DROPOUT,
        },
        'data': {
            'source': '9 patients real CGM data',
            'patients': len(all_series),
            'total_readings': sum(s['count'] for s in stats),
            'patient_stats': stats,
        },
        'training': {
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'batch_size': BATCH_SIZE,
            'learning_rate': LEARNING_RATE,
            'weight_decay': WEIGHT_DECAY,
            'early_stopping_patience': PATIENCE,
        },
        'models': {
            '30min': {
                'file': 'glucose_lstm_30min.pth',
                'forward_steps': FORWARD_30,
                'best_epoch': best_30_epoch,
                'performance': metrics_30,
            },
            '60min': {
                'file': 'glucose_lstm_60min.pth',
                'forward_steps': FORWARD_60,
                'best_epoch': best_60_epoch,
                'performance': metrics_60,
            },
        },
        'training_date': datetime.now().isoformat(),
        'device': str(DEVICE),
        'is_real_data': True,
    }
    joblib.dump(info, info_path)

    print(f"   → {model_30_path}")
    print(f"   → {model_60_path}")
    print(f"   → {scaler_path}")
    print(f"   → {info_path}")

    print(f"\n[完成] 血糖预测LSTM训练完成！\n")


if __name__ == '__main__':
    train()
