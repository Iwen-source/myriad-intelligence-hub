"""
糖尿病风险深度神经网络训练脚本 (PyTorch DNN)
=============================================
【数据源】PIMA印第安人糖尿病数据集 (768条真实临床记录)
【架构】  深度神经网络 + BatchNorm + Dropout
【优化】  AdamW + CosineAnnealingLR + EarlyStopping
【输出】  仅保留验证集损失最低的最优模型
         → diabetes_dnn_model.pth
         → diabetes_scaler.joblib
         → diabetes_info.joblib
"""

import os, sys, json, warnings
import numpy as np
import pandas as pd
import joblib
from datetime import datetime

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix,
                             roc_curve, classification_report)

from tqdm import tqdm

warnings.filterwarnings('ignore')

# ======================== 配置 ========================

DATA_PATH = r'D:\东软实习\相关性分析_胰岛素_血糖\pima-indians-diabetes.csv'
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
    print(f"         显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

# 超参数
EPOCHS = 500
BATCH_SIZE = 32
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4
PATIENCE = 50          # Early stopping patience
DROPOUT_RATE = 0.35
HIDDEN_LAYERS = [128, 256, 128]  # 网络层宽度

COLUMNS = [
    'pregnancies', 'glucose', 'blood_pressure', 'skin_thickness',
    'insulin', 'bmi', 'diabetes_pedigree', 'age', 'outcome'
]

FEATURE_NAMES = [
    ('怀孕次数', 'pregnancies', '次'),
    ('血糖浓度', 'glucose', 'mg/dL'),
    ('血压', 'blood_pressure', 'mm Hg'),
    ('皮褶厚度', 'skin_thickness', 'mm'),
    ('胰岛素水平', 'insulin', 'mu U/ml'),
    ('BMI', 'bmi', 'kg/m²'),
    ('糖尿病家族史系数', 'diabetes_pedigree', ''),
    ('年龄', 'age', '岁'),
]


# ======================== 神经网络定义 ========================

class DiabetesDNN(nn.Module):
    """糖尿病风险深度神经网络"""

    def __init__(self, input_dim=8, hidden_dims=None, dropout_rate=0.35):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [128, 256, 128]

        layers = []
        prev_dim = input_dim

        for h_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, h_dim),
                nn.BatchNorm1d(h_dim),
                nn.ReLU(inplace=True),
                nn.Dropout(dropout_rate),
            ])
            prev_dim = h_dim

        # 额外加一个小压缩层
        layers.append(nn.Linear(prev_dim, 64))
        layers.append(nn.BatchNorm1d(64))
        layers.append(nn.ReLU(inplace=True))
        layers.append(nn.Dropout(dropout_rate * 0.8))

        layers.append(nn.Linear(64, 1))

        self.network = nn.Sequential(*layers)

        # 初始化权重
        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x):
        return self.network(x)


# ======================== 数据加载与预处理 ========================

def load_data():
    """加载并清洗 PIMA 数据"""
    print("=" * 65)
    print("              糖尿病风险DNN训练 — PIMA数据集")
    print("=" * 65)

    df = pd.read_csv(DATA_PATH, header=None, names=COLUMNS)

    print(f"\n📊 数据概况:")
    print(f"   样本总数: {len(df)}")
    print(f"   特征维度: 8")
    print(f"   正例(患病): {df['outcome'].sum()} ({df['outcome'].mean():.1%})")
    print(f"   负例(健康): {(1 - df['outcome']).sum()} ({(1 - df['outcome']).mean():.1%})")
    print(f"\n   特征列: {', '.join(c[1] for c in FEATURE_NAMES)}")

    # 处理0值替换为中位数（PIMA特有的缺失值标记方式）
    zero_replace_cols = ['glucose', 'blood_pressure', 'skin_thickness', 'insulin', 'bmi']
    print(f"\n🔄 缺失值处理 (0值→中位数):")
    for col in zero_replace_cols:
        median_val = df[df[col] > 0][col].median()
        count_zero = (df[col] == 0).sum()
        df.loc[df[col] == 0, col] = median_val
        if count_zero > 0:
            print(f"   {col}: {count_zero} 个0值 → {median_val:.2f}")

    print(f"\n📈 特征统计:")
    print(df[COLUMNS[:-1]].describe().to_string())

    X = df[COLUMNS[:-1]].values.astype(np.float32)
    y = df['outcome'].values.astype(np.float32)

    return X, y, df


def create_dataloaders(X, y, batch_size=32):
    """划分训练/验证集并创建 DataLoader"""
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )

    print(f"\n📦 数据集划分:")
    print(f"   训练集: {len(X_train)} 样本")
    print(f"   验证集: {len(X_val)} 样本")

    # 标准化
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # DataLoader
    train_dataset = TensorDataset(
        torch.FloatTensor(X_train_scaled),
        torch.FloatTensor(y_train).view(-1, 1)
    )
    val_dataset = TensorDataset(
        torch.FloatTensor(X_val_scaled),
        torch.FloatTensor(y_val).view(-1, 1)
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, scaler, X_val_scaled, y_val


# ======================== 训练 ========================

def train_epoch(model, loader, criterion, optimizer, device):
    """训练一个epoch"""
    model.train()
    total_loss = 0.0
    all_preds, all_targets = [], []

    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)

        optimizer.zero_grad()
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * X_batch.size(0)
        probs = torch.sigmoid(outputs)
        all_preds.extend(probs.detach().cpu().numpy())
        all_targets.extend(y_batch.cpu().numpy())

    avg_loss = total_loss / len(loader.dataset)
    return avg_loss, np.array(all_preds), np.array(all_targets)


def evaluate(model, loader, criterion, device):
    """评估模型"""
    model.eval()
    total_loss = 0.0
    all_preds, all_targets = [], []

    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            total_loss += loss.item() * X_batch.size(0)
            all_preds.extend(torch.sigmoid(outputs).cpu().numpy())
            all_targets.extend(y_batch.cpu().numpy())

    avg_loss = total_loss / len(loader.dataset)
    return avg_loss, np.array(all_preds), np.array(all_targets)


def compute_metrics(y_true, y_pred_probs, threshold=0.5):
    """计算评价指标"""
    y_pred = (y_pred_probs >= threshold).astype(int)
    y_true_int = y_true.astype(int)

    return {
        'accuracy': float(accuracy_score(y_true_int, y_pred)),
        'precision': float(precision_score(y_true_int, y_pred, zero_division=0)),
        'recall': float(recall_score(y_true_int, y_pred, zero_division=0)),
        'f1_score': float(f1_score(y_true_int, y_pred, zero_division=0)),
        'roc_auc': float(roc_auc_score(y_true_int, y_pred_probs)),
        'threshold': threshold,
    }


def train():
    """主训练流程"""
    # ── 加载数据 ──
    X, y, raw_df = load_data()
    train_loader, val_loader, scaler, X_val_scaled, y_val = create_dataloaders(
        X, y, BATCH_SIZE
    )

    # ── 初始化模型 ──
    model = DiabetesDNN(
        input_dim=X.shape[1],
        hidden_dims=HIDDEN_LAYERS,
        dropout_rate=DROPOUT_RATE
    ).to(DEVICE)

    # 统计参数量
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\n🧠 模型结构:")
    print(f"   总参数量: {total_params:,}")
    print(f"   可训练参数: {trainable_params:,}")
    print(f"   架构: {HIDDEN_LAYERS}")

    # ── 损失函数 & 优化器 ──
    pos_weight = torch.tensor([(y == 0).sum() / (y == 1).sum()]).to(DEVICE)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-6)

    print(f"\n⚙  训练配置:")
    print(f"   Epochs: {EPOCHS} (early stopping: {PATIENCE})")
    print(f"   Batch Size: {BATCH_SIZE}")
    print(f"   Learning Rate: {LEARNING_RATE}")
    print(f"   Optimizer: AdamW (wd={WEIGHT_DECAY})")
    print(f"   Scheduler: CosineAnnealing")
    print(f"   类别权重 (pos_weight): {pos_weight.item():.2f}")
    print(f"   Dropout: {DROPOUT_RATE}")
    print()

    # ── 训练循环 ──
    best_val_loss = float('inf')
    best_model_state = None
    best_epoch = 0
    patience_counter = 0
    history = {'train_loss': [], 'val_loss': [], 'lr': []}

    for epoch in range(1, EPOCHS + 1):
        # 训练
        train_loss, train_preds, train_targets = train_epoch(
            model, train_loader, criterion, optimizer, DEVICE
        )
        val_loss, val_preds, val_targets = evaluate(
            model, val_loader, criterion, DEVICE
        )

        current_lr = optimizer.param_groups[0]['lr']
        scheduler.step()

        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['lr'].append(current_lr)

        # 进度条输出
        train_metrics = compute_metrics(train_targets, train_preds, 0.5)
        val_metrics = compute_metrics(val_targets, val_preds, 0.5)

        desc = (f"Epoch {epoch:3d}/{EPOCHS} | "
                f"Train Loss: {train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f} | "
                f"Val Acc: {val_metrics['accuracy']:.3f} | "
                f"Val AUC: {val_metrics['roc_auc']:.3f} | "
                f"LR: {current_lr:.2e}")
        print(desc)

        # 保存最优模型
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_state = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'val_metrics': val_metrics,
                'hyperparams': {
                    'hidden_layers': HIDDEN_LAYERS,
                    'dropout': DROPOUT_RATE,
                    'lr': LEARNING_RATE,
                    'weight_decay': WEIGHT_DECAY,
                    'batch_size': BATCH_SIZE,
                }
            }
            best_epoch = epoch
            patience_counter = 0
        else:
            patience_counter += 1

        # Early stopping
        if patience_counter >= PATIENCE:
            print(f"\n  Early stopping at epoch {epoch} (no improvement for {PATIENCE} epochs)")
            break

    print(f"\n{'=' * 65}")
    print(f"🏆 训练完成！最佳模型在 Epoch {best_epoch}")
    print(f"   验证集损失: {best_val_loss:.4f}")
    print(f"{'=' * 65}")

    # ── 加载最佳模型评估 ──
    model.load_state_dict(best_model_state['model_state_dict'])

    # 在完整验证集上最终评估
    criterion_final = nn.BCEWithLogitsLoss()
    val_loss_final, val_preds_final, val_targets_final = evaluate(
        model, val_loader, criterion_final, DEVICE
    )

    print(f"\n📊 最终验证集评估:")
    final_metrics = compute_metrics(val_targets_final, val_preds_final, 0.5)
    for k, v in final_metrics.items():
        if k != 'threshold':
            print(f"   {k}: {v:.4f}" if isinstance(v, float) else f"   {k}: {v}")

    # 输出分类报告
    y_pred_binary = (val_preds_final >= 0.5).astype(int)
    report_str = classification_report(val_targets_final.astype(int), y_pred_binary,
                                       target_names=['健康', '患病'], zero_division=0)
    print(report_str)

    # 在全部数据上做最终训练（用于部署的最佳模型）
    print(f"\n🔄 在全量数据上微调最终模型...")
    full_scaler = StandardScaler()
    X_full_scaled = full_scaler.fit_transform(X)
    full_dataset = TensorDataset(
        torch.FloatTensor(X_full_scaled),
        torch.FloatTensor(y).view(-1, 1)
    )
    full_loader = DataLoader(full_dataset, batch_size=BATCH_SIZE, shuffle=True)

    # 重新初始化模型
    final_model = DiabetesDNN(
        input_dim=X.shape[1],
        hidden_dims=HIDDEN_LAYERS,
        dropout_rate=DROPOUT_RATE * 0.5  # 最终训练降低dropout
    ).to(DEVICE)

    final_optimizer = optim.AdamW(
        final_model.parameters(), lr=LEARNING_RATE * 0.3, weight_decay=WEIGHT_DECAY
    )
    final_criterion = nn.BCEWithLogitsLoss(
        pos_weight=torch.tensor([(y == 0).sum() / (y == 1).sum()]).to(DEVICE)
    )

    # 全量数据微调
    best_full_loss = float('inf')
    patience_full = 20
    p_counter = 0

    for epoch in tqdm(range(100), desc="全量微调", ncols=80):
        final_model.train()
        total_loss = 0
        for X_b, y_b in full_loader:
            X_b, y_b = X_b.to(DEVICE), y_b.to(DEVICE)
            final_optimizer.zero_grad()
            loss = final_criterion(final_model(X_b), y_b)
            loss.backward()
            final_optimizer.step()
            total_loss += loss.item() * X_b.size(0)

        avg_loss = total_loss / len(full_loader.dataset)
        if avg_loss < best_full_loss:
            best_full_loss = avg_loss
            best_final_state = final_model.state_dict()
            p_counter = 0
        else:
            p_counter += 1
        if p_counter >= patience_full:
            break

    final_model.load_state_dict(best_final_state)
    print(f"   全量微调完成, 最终损失: {best_full_loss:.4f}")

    # ── 保存模型 ──
    model_path = os.path.join(OUTPUT_DIR, 'diabetes_dnn_model.pth')
    scaler_path = os.path.join(OUTPUT_DIR, 'diabetes_scaler.joblib')
    info_path = os.path.join(OUTPUT_DIR, 'diabetes_info.joblib')

    # 保存完整模型 (结构+权重)
    torch.save({
        'model_state_dict': best_final_state,
        'input_dim': X.shape[1],
        'hidden_layers': HIDDEN_LAYERS,
        'dropout': DROPOUT_RATE * 0.5,
        'final_loss': best_full_loss,
    }, model_path)

    # 保存标准化器
    joblib.dump(full_scaler, scaler_path)

    # 保存模型信息
    info = {
        'name': 'PIMA印第安人糖尿病数据集 (PyTorch DNN)',
        'model_type': 'PyTorch Deep Neural Network',
        'architecture': {
            'type': 'DiabetesDNN',
            'input_dim': X.shape[1],
            'hidden_layers': HIDDEN_LAYERS,
            'final_compression': 64,
            'output': 'sigmoid(binary)',
            'total_params': total_params,
            'trainable_params': trainable_params,
        },
        'training': {
            'data_source': 'PIMA Indians Diabetes Dataset',
            'samples': len(X),
            'features': X.shape[1],
            'train_samples': len(X) - len(X_val_scaled),
            'val_samples': len(X_val_scaled),
            'epochs_trained': min(EPOCHS, epoch),
            'best_epoch': best_epoch,
            'best_val_loss': best_val_loss,
            'full_finetune_loss': best_full_loss,
        },
        'performance': final_metrics,
        'feature_names': [f[1] for f in FEATURE_NAMES],
        'feature_display': [(f[0], f[2]) for f in FEATURE_NAMES],
        'risk_thresholds': {
            'low': 0.3,
            'medium': 0.6,
        },
        'training_date': datetime.now().isoformat(),
        'device': str(DEVICE),
        'is_real_data': True,
    }
    joblib.dump(info, info_path)

    print(f"\n💾 模型文件已保存:")
    print(f"   → {model_path}")
    print(f"   → {scaler_path}")
    print(f"   → {info_path}")

    # 验证准确性（在原始scale数据上用最终模型）
    final_model.eval()
    with torch.no_grad():
        full_preds = torch.sigmoid(final_model(torch.FloatTensor(X_full_scaled).to(DEVICE)))
        full_preds_np = full_preds.cpu().numpy().flatten()
    full_metrics = compute_metrics(y, full_preds_np, 0.5)

    print(f"\n📈 全量数据最终指标:")
    print(f"   Accuracy:  {full_metrics['accuracy']:.4f}")
    print(f"   Precision: {full_metrics['precision']:.4f}")
    print(f"   Recall:    {full_metrics['recall']:.4f}")
    print(f"   F1-Score:  {full_metrics['f1_score']:.4f}")
    print(f"   AUC-ROC:   {full_metrics['roc_auc']:.4f}")

    print(f"\n[OK] 糖尿病风险DNN训练完成！\n")

    return model, scaler, info


if __name__ == '__main__':
    train()
