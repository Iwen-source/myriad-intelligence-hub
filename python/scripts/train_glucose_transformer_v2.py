"""
血糖预测 Transformer v2 (多任务学习)
=====================================
【改进】Transformer + 时间编码 + 多任务(30min+60min) + 患者嵌入
【数据】9名患者CGM数据 (8221条真实记录, 5分钟间隔)
【架构】Transformer Encoder + 可学习时间编码 + 双头输出
【优化】AdamW + CosineAnnealingWarmRestarts + MAE损失
【输出】同时预测30min和60min血糖 -> glucose_lstm_30min.pth / 60min.pth
"""

import os, sys, json, warnings, copy
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta
from collections import OrderedDict

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, TensorDataset

from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── 配置 ──
DATA_DIR = r'D:\东软实习\相关性分析_胰岛素_血糖'
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

# 超参数
SEQ_LEN = 24                     # 输入窗口: 24 * 5min = 2小时历史
PRED_30 = 6                      # 30min = 6步
PRED_60 = 12                     # 60min = 12步
HIDDEN_SIZE = 128
NUM_LAYERS = 4
NUM_HEADS = 8
DROPOUT = 0.15
BATCH_SIZE = 32
EPOCHS = 500
LEARNING_RATE = 5e-4
WEIGHT_DECAY = 1e-5
PATIENCE = 80

PATIENT_IDS = [f'patient_{i:02d}' for i in range(1, 10)]  # 9 patients


# ── 位置编码 ──
class PositionalEncoding(nn.Module):
    """可学习位置编码"""
    def __init__(self, d_model, max_len=500):
        super().__init__()
        self.pos_embedding = nn.Parameter(torch.randn(1, max_len, d_model) * 0.1)

    def forward(self, x):
        return x + self.pos_embedding[:, :x.size(1), :]


# ── 患者嵌入 ──
class PatientEmbedding(nn.Module):
    """可学习患者嵌入层"""
    def __init__(self, n_patients=9, embed_dim=16):
        super().__init__()
        self.embedding = nn.Embedding(n_patients, embed_dim)
        self.proj = nn.Linear(embed_dim, 1)

    def forward(self, patient_ids):
        # patient_ids: (B,)
        emb = self.embedding(patient_ids)  # (B, embed_dim)
        return self.proj(emb)              # (B, 1)


# ── Transformer预测模型 ──
class GlucoseTransformer(nn.Module):
    """
    血糖预测 Transformer
    输入: (B, S, 1) 历史血糖序列 + 患者ID
    输出: 30min预测 + 60min预测
    """
    def __init__(self, seq_len=24, pred_30=6, pred_60=12,
                 d_model=128, nhead=8, num_layers=4, dropout=0.15,
                 n_patients=9):
        super().__init__()
        self.seq_len = seq_len
        self.d_model = d_model

        # 输入投影
        self.input_proj = nn.Linear(1, d_model)
        self.pos_encoder = PositionalEncoding(d_model, seq_len)

        # 患者嵌入
        self.patient_emb = nn.Embedding(n_patients, d_model)

        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True, activation='gelu'
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # 时间特征编码
        self.time_encoder = nn.Sequential(
            nn.Linear(2, d_model // 4),  # hour_of_day, day_of_week
            nn.GELU(),
            nn.Linear(d_model // 4, d_model),
        )

        # 双头输出
        self.output_proj = nn.Linear(d_model, d_model // 2)
        self.output_act = nn.GELU()
        self.output_drop = nn.Dropout(dropout)
        self.head_30min = nn.Linear(d_model // 2, pred_30)
        self.head_60min = nn.Linear(d_model // 2, pred_60)

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight, gain=0.5)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x, patient_ids=None, time_feats=None):
        """
        x: (B, S, 1) 历史血糖值
        patient_ids: (B,) 患者ID索引
        time_feats: (B, S, 2) 时间特征 (hour, day_of_week)
        """
        B, S, _ = x.shape

        # 输入投影
        x = self.input_proj(x)  # (B, S, d_model)

        # 加位置编码
        x = self.pos_encoder(x)

        # 加时间特征编码
        if time_feats is not None:
            time_enc = self.time_encoder(time_feats)
            x = x + time_enc

        # 加患者嵌入
        if patient_ids is not None:
            pid_emb = self.patient_emb(patient_ids).unsqueeze(1)  # (B, 1, d_model)
            x = x + pid_emb

        # Transformer
        x = self.transformer(x)  # (B, S, d_model)

        # 取最后一个时间步
        x_last = x[:, -1, :]

        # 双头输出
        x = self.output_drop(self.output_act(self.output_proj(x_last)))
        pred_30 = self.head_30min(x)  # (B, 6) -> 后30分钟6个点
        pred_60 = self.head_60min(x)  # (B, 12) -> 后60分钟12个点

        return pred_30, pred_60


# ── LSTM基线模型 (保持兼容) ──
class GlucoseBiLSTM(nn.Module):
    """双向LSTM预测 (保持与旧接口兼容)"""
    def __init__(self, input_size=1, hidden_size=128, num_layers=3,
                 dropout=0.15, seq_len=24, pred_len=12, use_attention=True):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                            batch_first=True, bidirectional=True, dropout=dropout)
        lstm_out = hidden_size * 2

        self.use_attention = use_attention
        if use_attention:
            self.attention = nn.MultiheadAttention(lstm_out, num_heads=4,
                                                    batch_first=True, dropout=dropout)
        self.attention_proj = nn.Linear(lstm_out, lstm_out // 2)

        self.fc = nn.Sequential(OrderedDict([
            ('fc1', nn.Linear(lstm_out // 2, 64)),
            ('gelu', nn.GELU()),
            ('drop', nn.Dropout(dropout)),
            ('fc2', nn.Linear(64, pred_len)),
        ]))

    def forward(self, x):
        # x: (B, S, 1)
        lstm_out, _ = self.lstm(x)  # (B, S, lstm_out)
        if self.use_attention:
            attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
            lstm_out = lstm_out + attn_out  # 残差

        # 全局平均池化
        pooled = lstm_out.mean(dim=1)  # (B, lstm_out)
        pooled = self.attention_proj(pooled)
        return self.fc(pooled)


# ── 数据加载 ──
def load_all_glucose():
    """加载所有9名患者的CGM数据"""
    print("=" * 65)
    print("  血糖预测 Transformer v2 - 9名患者CGM数据集")
    print("=" * 65)

    all_dfs = []
    patient_stats = []

    for i, pid in enumerate(PATIENT_IDS):
        file_path = os.path.join(DATA_DIR, f'glucose_{i+1:02d}.csv')
        df = pd.read_csv(file_path)
        df['patient_id'] = i
        df['patient_name'] = pid

        # 解析时间
        df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        df = df.sort_values('datetime').reset_index(drop=True)

        # 只保留CGM类型数据 (忽略manual等)
        df_cgm = df[df['type'] == 'cgm'].copy()

        # 计算时间特征
        df_cgm['hour'] = df_cgm['datetime'].dt.hour
        df_cgm['day_of_week'] = df_cgm['datetime'].dt.dayofweek

        all_dfs.append(df_cgm)

        count_all = len(df)
        count_cgm = len(df_cgm)
        glucose_mean = df_cgm['glucose'].mean()
        glucose_std = df_cgm['glucose'].std()
        glucose_min = df_cgm['glucose'].min()
        glucose_max = df_cgm['glucose'].max()
        duration_h = (df_cgm['datetime'].max() - df_cgm['datetime'].min()).total_seconds() / 3600

        patient_stats.append({
            'patient': f'Patient {i+1:02d}',
            'total_records': count_all,
            'cgm_records': count_cgm,
            'mean_g': glucose_mean,
            'std_g': glucose_std,
            'min_g': glucose_min,
            'max_g': glucose_max,
            'duration_h': duration_h,
        })

        print(f"  {pid:15s}: total={count_all:5d}, cgm={count_cgm:4d}, "
              f"glucose={glucose_mean:.1f}+-{glucose_std:.1f}, "
              f"range=[{glucose_min:.1f}, {glucose_max:.1f}], "
              f"duration={duration_h:.1f}h")

    # 合并
    df_all = pd.concat(all_dfs, ignore_index=True)
    print(f"\n  总计: {len(df_all)} CGM记录, {len(PATIENT_IDS)}名患者")
    print(f"  全局血糖: mean={df_all['glucose'].mean():.2f}, "
          f"std={df_all['glucose'].std():.2f}, "
          f"range=[{df_all['glucose'].min():.2f}, {df_all['glucose'].max():.2f}]")

    return df_all, patient_stats


def create_sequences(df_all, seq_len=24, pred_30=6, pred_60=12):
    """
    为每个患者独立创建滑动窗口序列
    返回: 序列 + 目标 + 患者ID + 时间特征
    """
    X, y_30, y_60, patient_ids, time_feats = [], [], [], [], []

    for pid in range(len(PATIENT_IDS)):
        patient_data = df_all[df_all['patient_id'] == pid].reset_index(drop=True)
        glucose = patient_data['glucose'].values
        values = glucose.reshape(-1, 1)

        total_len = seq_len + pred_60  # 需要最多 pred_60 步的未来数据
        if len(values) < total_len:
            continue

        for i in range(len(values) - total_len + 1):
            seq = values[i:i + seq_len]  # 历史
            target_30 = values[i + seq_len:i + seq_len + pred_30]  # 30min
            target_60 = values[i + seq_len:i + seq_len + pred_60]  # 60min

            # 时间特征
            hour = patient_data['hour'].values[i + seq_len - 1]  # 最后一个历史时间点
            dow = patient_data['day_of_week'].values[i + seq_len - 1]
            time_f = np.array([hour / 23.0, dow / 6.0], dtype=np.float32)  # 归一化到[0,1]

            X.append(seq)
            y_30.append(target_30)
            y_60.append(target_60)
            patient_ids.append(pid)
            time_feats.append(time_f)

    X = np.array(X, dtype=np.float32)
    y_30 = np.array(y_30, dtype=np.float32).squeeze(-1)  # (N, pred_30)
    y_60 = np.array(y_60, dtype=np.float32).squeeze(-1)  # (N, pred_60)
    patient_ids = np.array(patient_ids, dtype=np.int64)
    time_feats = np.array(time_feats, dtype=np.float32)   # (N, 2)

    return X, y_30, y_60, patient_ids, time_feats


def patient_wise_split(X, y_30, y_60, patient_ids, time_feats):
    """患者级别划分: 前6人训练, 后3人验证"""
    train_mask = patient_ids < 6
    val_mask = patient_ids >= 6

    return {
        'train': (X[train_mask], y_30[train_mask], y_60[train_mask],
                  patient_ids[train_mask], time_feats[train_mask]),
        'val': (X[val_mask], y_30[val_mask], y_60[val_mask],
                patient_ids[val_mask], time_feats[val_mask]),
    }


class GlucoseDataset(Dataset):
    def __init__(self, X, y_30, y_60, patient_ids, time_feats, scaler=None, fit_scaler=False):
        if scaler is None:
            scaler = RobustScaler()
            X_reshaped = X.reshape(-1, 1)
            if fit_scaler:
                scaler.fit(X_reshaped)
            X_scaled = X_reshaped.reshape(X.shape)
        else:
            X_reshaped = X.reshape(-1, 1)
            X_scaled = scaler.transform(X_reshaped).reshape(X.shape)

        self.X = torch.FloatTensor(X_scaled)
        self.y_30 = torch.FloatTensor(y_30)
        self.y_60 = torch.FloatTensor(y_60)
        self.patient_ids = torch.LongTensor(patient_ids)
        self.time_feats = torch.FloatTensor(time_feats)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return (self.X[idx], self.y_30[idx], self.y_60[idx],
                self.patient_ids[idx], self.time_feats[idx])


# ── 训练函数 ──
def train_transformer(model, train_loader, val_loader, device):
    """训练Transformer模型"""
    criterion = nn.L1Loss()  # MAE
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=50, T_mult=2, eta_min=1e-6
    )

    best_val_loss = float('inf')
    best_state = None
    best_epoch = 0
    patience = 0
    history = []

    pbar = tqdm(range(1, EPOCHS + 1), desc="Transformer", ncols=100,
                bar_format='{desc} |{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')

    for epoch in pbar:
        # Train
        model.train()
        train_loss = 0.0
        for X_b, y30_b, y60_b, pid_b, tf_b in train_loader:
            X_b, y30_b, y60_b = X_b.to(device), y30_b.to(device), y60_b.to(device)
            pid_b, tf_b = pid_b.to(device), tf_b.to(device)

            optimizer.zero_grad()
            pred_30, pred_60 = model(X_b, pid_b, tf_b.unsqueeze(1).repeat(1, X_b.size(1), 1))

            loss = criterion(pred_30, y30_b) + criterion(pred_60, y60_b)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * X_b.size(0)
        train_loss /= len(train_loader.dataset)

        # Validate
        model.eval()
        val_loss = 0.0
        all_pred_30, all_pred_60, all_y30, all_y60 = [], [], [], []
        with torch.no_grad():
            for X_b, y30_b, y60_b, pid_b, tf_b in val_loader:
                X_b, y30_b, y60_b = X_b.to(device), y30_b.to(device), y60_b.to(device)
                pid_b, tf_b = pid_b.to(device), tf_b.to(device)

                pred_30, pred_60 = model(X_b, pid_b, tf_b.unsqueeze(1).repeat(1, X_b.size(1), 1))
                loss = criterion(pred_30, y30_b) + criterion(pred_60, y60_b)
                val_loss += loss.item() * X_b.size(0)
                all_pred_30.append(pred_30.cpu())
                all_pred_60.append(pred_60.cpu())
                all_y30.append(y30_b.cpu())
                all_y60.append(y60_b.cpu())
        val_loss /= len(val_loader.dataset)
        all_pred_30 = torch.cat(all_pred_30)
        all_pred_60 = torch.cat(all_pred_60)

        scheduler.step()
        # CosineAnnealingWarmRestarts requires epoch or batch step, manually step
        scheduler.step(epoch)  # Actually this steps by epoch

        history.append({'epoch': epoch, 'train_loss': train_loss, 'val_loss': val_loss})

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            patience = 0
        else:
            patience += 1

        pbar.set_postfix({
            'train': f'{train_loss:.4f}',
            'val': f'{val_loss:.4f}',
            'best': f'{best_val_loss:.4f}',
        }, refresh=False)

        if patience >= PATIENCE:
            print(f"\n  Early stopping at epoch {epoch}")
            break

    # Load best
    model.load_state_dict(best_state)
    return model, best_val_loss, best_epoch, history


# ── 评估函数 ──
@torch.no_grad()
def evaluate_model(model, val_loader, scaler, device, pred_len=60):
    """详细评估模型性能"""
    model.eval()
    all_preds = []
    all_targets = []

    for X_batch, y_batch in val_loader:
        X_batch = X_batch.to(device)
        # For LSTM models without patient/time features
        if isinstance(model, GlucoseTransformer):
            # Create dummy features for eval
            pid_dummy = torch.zeros(X_batch.size(0), dtype=torch.long).to(device)
            tf_dummy = torch.zeros(X_batch.size(0), X_batch.size(1), 2).to(device)
            pred_30, pred_60 = model(X_batch, pid_dummy, tf_dummy)
            if pred_len == 30:
                all_preds.append(pred_30.cpu())
                all_targets.append(y_batch.cpu()[:, :6])
            else:
                all_preds.append(pred_60.cpu())
                all_targets.append(y_batch.cpu()[:, :12])
        else:
            pred = model(X_batch)
            all_preds.append(pred.cpu())
            all_targets.append(y_batch.cpu())

    preds = torch.cat(all_preds).numpy()
    targets = torch.cat(all_targets).numpy()

    # Inverse transform
    if scaler is not None:
        orig_shape = preds.shape
        preds = scaler.inverse_transform(preds.reshape(-1, 1)).reshape(orig_shape)
        targets = scaler.inverse_transform(targets.reshape(-1, 1)).reshape(orig_shape)

    # MAE per step
    mae_per_step = np.mean(np.abs(preds - targets), axis=0)
    mae = np.mean(mae_per_step)
    rmse = np.sqrt(np.mean((preds - targets) ** 2))
    
    # R2
    r2 = r2_score(targets.ravel(), preds.ravel())

    return {
        'mae': float(mae),
        'mae_per_step': mae_per_step.tolist(),
        'rmse': float(rmse),
        'r2': float(r2),
    }


# ── 主流程 ──
def main():
    # 1. 加载所有数据
    df_all, patient_stats = load_all_glucose()

    # 2. 创建序列
    print(f"\n创建时间序列窗口 (seq_len={SEQ_LEN}, pred_30={PRED_30}步, pred_60={PRED_60}步)...")
    X, y_30, y_60, patient_ids, time_feats = create_sequences(
        df_all, SEQ_LEN, PRED_30, PRED_60
    )
    print(f"  总样本数: {len(X)}")
    print(f"  X: {X.shape}")
    print(f"  y_30: {y_30.shape}")
    print(f"  y_60: {y_60.shape}")

    # 按患者划分
    split = patient_wise_split(X, y_30, y_60, patient_ids, time_feats)
    print(f"\n患者级别划分 (前6人训练, 后3人验证):")
    print(f"  训练: {len(split['train'][0])} 样本 (患者0-5)")
    print(f"  验证: {len(split['val'][0])} 样本 (患者6-8)")

    # 3. 创建数据加载器
    scaler = RobustScaler()
    scaler.fit(np.concatenate([split['train'][0].ravel(), split['val'][0].ravel()]).reshape(-1, 1))

    train_ds = GlucoseDataset(*split['train'], scaler, fit_scaler=False)
    val_ds = GlucoseDataset(*split['val'], scaler, fit_scaler=False)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader_30 = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    # Also create separate LSTM-compatible loaders for evaluation
    val_X = torch.FloatTensor(scaler.transform(split['val'][0].reshape(-1, 1)).reshape(split['val'][0].shape))
    val_y_30 = torch.FloatTensor(split['val'][1])
    val_y_60 = torch.FloatTensor(split['val'][2])
    val_lstm_loader_30 = DataLoader(TensorDataset(val_X, val_y_30), batch_size=BATCH_SIZE, shuffle=False)
    val_lstm_loader_60 = DataLoader(TensorDataset(val_X, val_y_60), batch_size=BATCH_SIZE, shuffle=False)

    print(f"\n血糖值标准化: center={scaler.center_[0]:.2f}, scale={scaler.scale_[0]:.2f}")

    # 4. 训练Transformer
    print(f"\n{'=' * 65}")
    print(f"  训练 Transformer 模型 (多任务: 30min + 60min)")
    print(f"{'=' * 65}")

    transformer = GlucoseTransformer(
        seq_len=SEQ_LEN, pred_30=PRED_30, pred_60=PRED_60,
        d_model=HIDDEN_SIZE, nhead=NUM_HEADS, num_layers=NUM_LAYERS,
        dropout=DROPOUT, n_patients=len(PATIENT_IDS)
    ).to(DEVICE)

    n_params = sum(p.numel() for p in transformer.parameters())
    print(f"  参数量: {n_params:,}")
    print(f"  Transformer: {NUM_LAYERS} layers, {NUM_HEADS} heads, {HIDDEN_SIZE} dim")

    transformer, best_loss, best_epoch, history = train_transformer(
        transformer, train_loader, val_loader_30, DEVICE
    )
    print(f"\n[OK] Transformer训练完成! 最佳val_loss={best_loss:.4f} @ epoch {best_epoch}")

    # 5. 为LSTM创建兼容的DataLoader (只输出X和y)
    lstm_train_X = torch.FloatTensor(scaler.transform(split['train'][0].reshape(-1, 1)).reshape(split['train'][0].shape))
    lstm_train_y30 = torch.FloatTensor(split['train'][1])
    lstm_train_y60 = torch.FloatTensor(split['train'][2])
    lstm_train_loader_30 = DataLoader(TensorDataset(lstm_train_X, lstm_train_y30), batch_size=BATCH_SIZE, shuffle=True)
    lstm_train_loader_60 = DataLoader(TensorDataset(lstm_train_X, lstm_train_y60), batch_size=BATCH_SIZE, shuffle=True)

    print(f"\n{'=' * 65}")
    print(f"  训练 BiLSTM 模型 (向后兼容, 30min和60min分别训练)")
    print(f"{'=' * 65}")

    lstm_models = {}
    for name, pred_len, train_l, val_loader in [
        ('30min', PRED_30, lstm_train_loader_30, val_lstm_loader_30),
        ('60min', PRED_60, lstm_train_loader_60, val_lstm_loader_60),
    ]:
        print(f"\n--- {name} 模型 ---")
        lstm_model = GlucoseBiLSTM(
            input_size=1, hidden_size=HIDDEN_SIZE, num_layers=3,
            dropout=DROPOUT, seq_len=SEQ_LEN, pred_len=pred_len
        ).to(DEVICE)

        optimizer = optim.AdamW(lstm_model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
        criterion = nn.L1Loss()
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

        best_lstm_loss = float('inf')
        best_lstm_state = None
        lstm_patience = 0

        pbar = tqdm(range(EPOCHS), desc=f"BiLSTM {name}", ncols=90,
                    bar_format='{desc} |{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
        for epoch in pbar:
            lstm_model.train()
            tl = 0
            for X_b, y_b in train_l:
                X_b, y_b = X_b.to(DEVICE), y_b.to(DEVICE)
                optimizer.zero_grad()
                loss = criterion(lstm_model(X_b), y_b[:, :pred_len])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(lstm_model.parameters(), 1.0)
                optimizer.step()
                tl += loss.item() * X_b.size(0)
            tl /= len(train_l.dataset)

            lstm_model.eval()
            vl = 0
            with torch.no_grad():
                for X_b, y_b in val_loader:
                    X_b, y_b = X_b.to(DEVICE), y_b.to(DEVICE)
                    loss = criterion(lstm_model(X_b), y_b[:, :pred_len])
                    vl += loss.item() * X_b.size(0)
            vl /= len(val_loader.dataset)
            scheduler.step()

            if vl < best_lstm_loss:
                best_lstm_loss = vl
                best_lstm_state = copy.deepcopy(lstm_model.state_dict())
                lstm_patience = 0
            else:
                lstm_patience += 1

            pbar.set_postfix({'train': f'{tl:.4f}', 'val': f'{vl:.4f}',
                             'best': f'{best_lstm_loss:.4f}'}, refresh=False)
            if lstm_patience >= PATIENCE:
                break

        lstm_model.load_state_dict(best_lstm_state)
        lstm_models[name] = lstm_model
        print(f"  [OK] {name}: best_val_loss={best_lstm_loss:.4f}")

    # 6. 评估
    print(f"\n{'=' * 65}")
    print(f"  模型评估 (验证集 - 患者6/7/8)")
    print(f"{'=' * 65}")

    # Transformer评估
    transformer.eval()
    transformer.to(DEVICE)
    all_t_pred_30, all_t_pred_60, all_t_y30, all_t_y60 = [], [], [], []
    with torch.no_grad():
        for X_b, y30_b, y60_b, pid_b, tf_b in val_loader_30:
            X_b, y30_b, y60_b = X_b.to(DEVICE), y30_b.to(DEVICE), y60_b.to(DEVICE)
            pid_b, tf_b = pid_b.to(DEVICE), tf_b.to(DEVICE)
            p30, p60 = transformer(X_b, pid_b, tf_b.unsqueeze(1).repeat(1, X_b.size(1), 1))
            all_t_pred_30.append(p30.cpu().numpy())
            all_t_pred_60.append(p60.cpu().numpy())
            all_t_y30.append(y30_b.cpu().numpy())
            all_t_y60.append(y60_b.cpu().numpy())

    t_pred_30 = scaler.inverse_transform(np.concatenate(all_t_pred_30).reshape(-1, 1)).reshape(-1, PRED_30)
    t_pred_60 = scaler.inverse_transform(np.concatenate(all_t_pred_60).reshape(-1, 1)).reshape(-1, PRED_60)
    t_y30 = scaler.inverse_transform(np.concatenate(all_t_y30).reshape(-1, 1)).reshape(-1, PRED_30)
    t_y60 = scaler.inverse_transform(np.concatenate(all_t_y60).reshape(-1, 1)).reshape(-1, PRED_60)

    t_mae_30 = np.mean(np.abs(t_pred_30 - t_y30))
    t_mae_60 = np.mean(np.abs(t_pred_60 - t_y60))
    t_rmse_30 = np.sqrt(np.mean((t_pred_30 - t_y30) ** 2))
    t_rmse_60 = np.sqrt(np.mean((t_pred_60 - t_y60) ** 2))
    t_r2_30 = r2_score(t_y30.ravel(), t_pred_30.ravel())
    t_r2_60 = r2_score(t_y60.ravel(), t_pred_60.ravel())

    print(f"\n  Transformer 多任务模型:")
    print(f"  30min: MAE={t_mae_30:.3f}, RMSE={t_rmse_30:.3f}, R2={t_r2_30:.4f}")
    print(f"  60min: MAE={t_mae_60:.3f}, RMSE={t_rmse_60:.3f}, R2={t_r2_60:.4f}")

    # LSTM评估
    lstm_results = {}
    for name, pred_len, val_loader in [
        ('30min', PRED_30, val_lstm_loader_30),
        ('60min', PRED_60, val_lstm_loader_60),
    ]:
        lstm_model = lstm_models[name]
        lstm_model.eval()
        lstm_model.to(DEVICE)
        all_pred, all_y = [], []
        with torch.no_grad():
            for X_b, y_b in val_loader:
                pred = lstm_model(X_b.to(DEVICE))
                all_pred.append(pred.cpu().numpy())
                all_y.append(y_b[:, :pred_len].numpy())
        pred = scaler.inverse_transform(np.concatenate(all_pred).reshape(-1, 1)).reshape(-1, pred_len)
        y = scaler.inverse_transform(np.concatenate(all_y).reshape(-1, 1)).reshape(-1, pred_len)
        mae = np.mean(np.abs(pred - y))
        rmse = np.sqrt(np.mean((pred - y) ** 2))
        r2 = r2_score(y.ravel(), pred.ravel())
        lstm_results[name] = {'mae': mae, 'rmse': rmse, 'r2': r2}
        print(f"\n  BiLSTM {name}:")
        print(f"  MAE={mae:.3f}, RMSE={rmse:.3f}, R2={r2:.4f}")

    # 7. 保存模型
    transformer_path_30 = os.path.join(OUTPUT_DIR, 'glucose_lstm_30min.pth')
    transformer_path_60 = os.path.join(OUTPUT_DIR, 'glucose_lstm_60min.pth')
    scaler_path = os.path.join(OUTPUT_DIR, 'glucose_scaler.joblib')
    info_path = os.path.join(OUTPUT_DIR, 'glucose_info.joblib')

    # 保存Transformer模型 (主要)
    torch.save({
        'model_type': 'GlucoseTransformer',
        'state_dict': transformer.state_dict(),
        'config': {
            'seq_len': SEQ_LEN,
            'pred_30': PRED_30,
            'pred_60': PRED_60,
            'd_model': HIDDEN_SIZE,
            'nhead': NUM_HEADS,
            'num_layers': NUM_LAYERS,
            'dropout': DROPOUT,
            'n_patients': len(PATIENT_IDS),
        },
        'performance': {
            '30min': {'mae': t_mae_30, 'rmse': t_rmse_30, 'r2': t_r2_30},
            '60min': {'mae': t_mae_60, 'rmse': t_rmse_60, 'r2': t_r2_60},
        },
        'best_epoch': best_epoch,
        'best_val_loss': best_loss,
    }, transformer_path_30)  # Save as primary model (30min path)
    print(f"\n  保存Transformer: {transformer_path_30}")

    # Also save LSTM models for backward compatibility
    for name, model in lstm_models.items():
        path_key = '30min' if '30' in name else '60min'
        save_path = transformer_path_60 if path_key == '60min' else transformer_path_30
        # Save LSTM as the glucose_lstm_60min.pth, and transformer as 30min
        if path_key == '60min':
            torch.save({
                'model_type': 'GlucoseBiLSTM',
                'state_dict': lstm_models['60min'].state_dict(),
                'config': {
                    'input_size': 1,
                    'hidden_size': HIDDEN_SIZE,
                    'num_layers': 3,
                    'seq_len': SEQ_LEN,
                    'pred_len': PRED_60,
                },
                'performance': lstm_results['60min'],
            }, save_path)
            print(f"  保存BiLSTM-60min: {save_path}")

    # 30min model = Transformer, 60min model = BiLSTM (both available)
    # Actually, save LSTM 30min too
    torch.save({
        'model_type': 'GlucoseBiLSTM',
        'state_dict': lstm_models['30min'].state_dict(),
        'config': {
            'input_size': 1,
            'hidden_size': HIDDEN_SIZE,
            'num_layers': 3,
            'seq_len': SEQ_LEN,
            'pred_len': PRED_30,
        },
        'performance': lstm_results['30min'],
    }, os.path.join(OUTPUT_DIR, 'glucose_lstm_30min_bilstm.pth'))
    print(f"  保存BiLSTM-30min: {os.path.join(OUTPUT_DIR, 'glucose_lstm_30min_bilstm.pth')}")

    # Save scaler
    joblib.dump(scaler, scaler_path)
    print(f"  保存Scaler: {scaler_path}")

    # Save info
    info = {
        'name': '血糖预测 v2 (Transformer + BiLSTM, 9名患者CGM)',
        'model_types': ['GlucoseTransformer', 'GlucoseBiLSTM'],
        'data': {
            'source': f'{len(PATIENT_IDS)}名患者CGM数据',
            'total_records': len(df_all),
            'total_sequences': len(X),
            'train_val_split': 'patient-wise (6 train, 3 val)',
            'patient_stats': patient_stats,
        },
        'config': {
            'seq_len': f'{SEQ_LEN} steps ({SEQ_LEN * 5} min)',
            'pred_30': f'{PRED_30} steps (30 min)',
            'pred_60': f'{PRED_60} steps (60 min)',
            'transformer': {
                'layers': NUM_LAYERS,
                'heads': NUM_HEADS,
                'd_model': HIDDEN_SIZE,
            },
            'lstm': {
                'layers': 3,
                'hidden_size': HIDDEN_SIZE,
            },
        },
        'performance': {
            'transformer_30min': {'mae': t_mae_30, 'rmse': t_rmse_30, 'r2': t_r2_30},
            'transformer_60min': {'mae': t_mae_60, 'rmse': t_rmse_60, 'r2': t_r2_60},
            'bilstm_30min': lstm_results.get('30min', {}),
            'bilstm_60min': lstm_results.get('60min', {}),
        },
        'optimal_models': 'transformer for 30min, bilstm for 60min',
        'training_date': datetime.now().isoformat(),
        'device': str(DEVICE),
    }
    joblib.dump(info, info_path)
    print(f"  保存Info: {info_path}")

    print(f"\n{'=' * 65}")
    print(f"  [完成] 血糖预测 v2 训练结束!")
    print(f"{'=' * 65}\n")


if __name__ == '__main__':
    main()
