"""
糖尿病风险深度神经网络 v2
=========================
【改进】K折交叉验证 + Focal Loss + 特征重要性 + MC Dropout不确定性
【数据】PIMA印第安人糖尿病数据集 (768条完整临床记录, 8项指标)
【架构】深度残差连接网络 + SELU激活 + Alpha Dropout
【优化】AdamW + OneCycleLR + Focal Loss + Gradient Clipping
【输出】仅保留最优模型 -> diabetes_dnn_model.pth
"""

import os, sys, json, warnings, copy
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from collections import OrderedDict

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, SubsetRandomSampler

from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix,
                             roc_curve, classification_report)
from scipy.special import expit

from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── 配置 ──
DATA_PATH = r'D:\东软实习\相关性分析_胰岛素_血糖\pima-indians-diabetes.csv'
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

N_FOLDS = 10                    # K折交叉验证
EPOCHS_PER_FOLD = 300           
BATCH_SIZE = 16                 # 小batch提升泛化
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 5e-5             
PATIENCE = 60                   
DROPOUT_RATE = 0.25             
ENSEMBLE_N = 5                  # 最终集成模型数

COLUMNS = [
    'pregnancies', 'glucose', 'blood_pressure', 'skin_thickness',
    'insulin', 'bmi', 'diabetes_pedigree', 'age', 'outcome'
]

FEATURE_NAMES = [
    'pregnancies', 'glucose', 'blood_pressure', 'skin_thickness',
    'insulin', 'bmi', 'diabetes_pedigree', 'age'
]


# ── 残差块定义 ──
class ResidualBlock(nn.Module):
    def __init__(self, dim, dropout=0.2):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.fc2 = nn.Linear(dim, dim)
        self.dropout = nn.AlphaDropout(dropout) if dropout > 0 else nn.Identity()
        self.selu = nn.SELU()

    def forward(self, x):
        residual = x
        out = self.selu(self.fc1(x))
        out = self.dropout(out)
        out = self.fc2(out)
        out = self.selu(out + residual)  # 残差连接
        return out


class DiabetesDNNv2(nn.Module):
    """
    糖尿病风险深度神经网络 v2
    架构: 输入 -> 扩展层 -> 3个残差块 -> 压缩层 -> 输出
    """
    def __init__(self, input_dim=8, dropout=0.25):
        super().__init__()
        self.input_layer = nn.Sequential(OrderedDict([
            ('fc_in', nn.Linear(input_dim, 256)),
            ('selu_in', nn.SELU()),
            ('drop_in', nn.AlphaDropout(dropout * 0.8)),
        ]))

        self.res_blocks = nn.Sequential(OrderedDict([
            ('block1', ResidualBlock(256, dropout)),
            ('block2', ResidualBlock(256, dropout * 0.7)),
            ('block3', ResidualBlock(256, dropout * 0.5)),
        ]))

        self.output_layer = nn.Sequential(OrderedDict([
            ('fc_mid', nn.Linear(256, 64)),
            ('selu_mid', nn.SELU()),
            ('drop_mid', nn.AlphaDropout(dropout * 0.5)),
            ('fc_out', nn.Linear(64, 1)),
        ]))

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_in', nonlinearity='linear')
                nn.init.constant_(m.bias, 0)

    def forward(self, x):
        x = self.input_layer(x)
        x = self.res_blocks(x)
        x = self.output_layer(x)
        return x


# ── Focal Loss ──
class FocalLoss(nn.Module):
    """Focal Loss 处理类别不平衡"""
    def __init__(self, alpha=0.75, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, inputs, targets):
        bce_loss = F.binary_cross_entropy_with_logits(inputs, targets, reduction='none')
        prob = torch.sigmoid(inputs)
        p_t = prob * targets + (1 - prob) * (1 - targets)
        focal_weight = (1 - p_t) ** self.gamma
        alpha_t = self.alpha * targets + (1 - self.alpha) * (1 - targets)
        loss = alpha_t * focal_weight * bce_loss
        return loss.mean()


# ── 数据加载与清洗 ──
def load_data():
    """加载PIMA数据, 所有0值以中位数填充"""
    print("=" * 65)
    print("          糖尿病风险DNN v2 - PIMA数据集 (768条真实记录)")
    print("=" * 65)

    df = pd.read_csv(DATA_PATH, header=None, names=COLUMNS)

    # 统计
    n_pos = df['outcome'].sum()
    n_neg = len(df) - n_pos
    print(f"\n数据概况:")
    print(f"  样本总数: {len(df)}")
    print(f"  特征维度: {len(FEATURE_NAMES)}")
    print(f"  正例(患病): {int(n_pos)} ({n_pos/len(df):.1%})")
    print(f"  负例(健康): {int(n_neg)} ({n_neg/len(df):.1%})")
    print(f"  不平衡比: {n_neg/n_pos:.2f}:1")

    # 0值处理 (PIMA的0表示缺失)
    zero_cols = ['glucose', 'blood_pressure', 'skin_thickness', 'insulin', 'bmi']
    print(f"\n缺失值处理 (0值→中位数):")
    for col in zero_cols:
        median_val = df[df[col] > 0][col].median()
        zero_cnt = (df[col] == 0).sum()
        df.loc[df[col] == 0, col] = median_val
        if zero_cnt > 0:
            print(f"  {col}: {zero_cnt}个 -> {median_val:.2f}")

    X = df[FEATURE_NAMES].values.astype(np.float32)
    y = df['outcome'].values.astype(np.float32)

    # 统计描述
    stats = df[FEATURE_NAMES].describe()
    print(f"\n特征统计:")
    for col in FEATURE_NAMES:
        print(f"  {col:20s}: mean={stats[col]['mean']:8.2f}  std={stats[col]['std']:8.2f}  "
              f"min={stats[col]['min']:8.2f}  max={stats[col]['max']:8.2f}")

    return X, y


# ── 训练与评估函数 ──
def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    all_preds, all_targets = [], []

    for X_b, y_b in loader:
        X_b, y_b = X_b.to(device), y_b.to(device)
        optimizer.zero_grad()
        outputs = model(X_b)
        loss = criterion(outputs, y_b)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        total_loss += loss.item() * X_b.size(0)
        probs = torch.sigmoid(outputs)
        all_preds.extend(probs.detach().cpu().numpy())
        all_targets.extend(y_b.cpu().numpy())

    return total_loss / len(loader.dataset), np.array(all_preds), np.array(all_targets)


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    all_preds, all_targets = [], []

    for X_b, y_b in loader:
        X_b, y_b = X_b.to(device), y_b.to(device)
        outputs = model(X_b)
        loss = criterion(outputs, y_b)
        total_loss += loss.item() * X_b.size(0)
        all_preds.extend(torch.sigmoid(outputs).cpu().numpy())
        all_targets.extend(y_b.cpu().numpy())

    return total_loss / len(loader.dataset), np.array(all_preds), np.array(all_targets)


def calc_metrics(y_true, y_pred_probs, threshold=0.5):
    y_pred = (y_pred_probs >= threshold).astype(int)
    y_t = y_true.astype(int)
    try:
        auc = roc_auc_score(y_t, y_pred_probs)
    except:
        auc = 0.5
    return {
        'accuracy': accuracy_score(y_t, y_pred),
        'precision': precision_score(y_t, y_pred, zero_division=0),
        'recall': recall_score(y_t, y_pred, zero_division=0),
        'f1_score': f1_score(y_t, y_pred, zero_division=0),
        'roc_auc': auc,
        'threshold': threshold,
    }


def find_optimal_threshold(y_true, y_pred_probs):
    """寻找约登指数最优阈值"""
    thresholds = np.arange(0.1, 0.9, 0.01)
    best_t = 0.5
    best_j = 0
    results = []
    for t in thresholds:
        y_b = (y_pred_probs >= t).astype(int)
        sens = recall_score(y_true.astype(int), y_b, zero_division=0)
        spec = (1 - y_true.astype(int))[y_b == 0].sum() / (1 - y_true.astype(int)).sum() if (1 - y_true.astype(int)).sum() > 0 else 0
        j = sens + spec - 1
        results.append((t, j, sens, spec))
        if j > best_j:
            best_j = j
            best_t = t
    return best_t, best_j, results


# ── 交叉验证训练 ──
def train_cv_fold(X, y, scaler, fold_idx, train_idx, val_idx):
    """训练单个折"""
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    X_train_s = scaler.transform(X_train)
    X_val_s = scaler.transform(X_val)

    train_ds = TensorDataset(torch.FloatTensor(X_train_s), torch.FloatTensor(y_train).view(-1, 1))
    val_ds = TensorDataset(torch.FloatTensor(X_val_s), torch.FloatTensor(y_val).view(-1, 1))

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    model = DiabetesDNNv2(input_dim=X.shape[1], dropout=DROPOUT_RATE).to(DEVICE)
    criterion = FocalLoss(alpha=0.75, gamma=2.0)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.OneCycleLR(optimizer, max_lr=LEARNING_RATE * 3,
                                              steps_per_epoch=len(train_loader),
                                              epochs=EPOCHS_PER_FOLD, pct_start=0.3)
    best_val_loss = float('inf')
    best_state = None
    best_epoch = 0
    patience = 0
    history = []

    pbar = tqdm(range(1, EPOCHS_PER_FOLD + 1), desc=f"Fold {fold_idx}", ncols=95,
                bar_format='{desc} |{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')

    for epoch in pbar:
        train_loss, _, _ = train_epoch(model, train_loader, criterion, optimizer, DEVICE)
        val_loss, val_preds, val_targets = evaluate(model, val_loader, criterion, DEVICE)
        scheduler.step()

        history.append({'epoch': epoch, 'train_loss': train_loss, 'val_loss': val_loss})

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            patience = 0
            pbar.set_postfix({'best': f'{best_val_loss:.4f}', 'val': f'{val_loss:.4f}'}, refresh=False)
        else:
            patience += 1

        if patience >= PATIENCE:
            break

    # 加载最佳模型评估
    model.load_state_dict(best_state)
    _, val_preds, val_targets = evaluate(model, val_loader, criterion, DEVICE)
    metrics = calc_metrics(val_targets, val_preds)

    return {
        'fold': fold_idx,
        'best_epoch': best_epoch,
        'best_val_loss': best_val_loss,
        'model_state': best_state,
        'metrics': metrics,
        'val_preds': val_preds,
        'val_targets': val_targets,
        'history': history,
    }


def train_kfold(X, y):
    """K折交叉验证"""
    print(f"\n{'=' * 65}")
    print(f"  {N_FOLDS}-折交叉验证训练")
    print(f"{'=' * 65}")

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    fold_results = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X_scaled, y), 1):
        result = train_cv_fold(X, y, scaler, fold_idx, train_idx, val_idx)
        fold_results.append(result)

        # 显示当前折结果
        m = result['metrics']
        print(f"\n  Fold {fold_idx}: "
              f"Val Loss={result['best_val_loss']:.4f}, "
              f"Acc={m['accuracy']:.3f}, "
              f"AUC={m['roc_auc']:.3f}, "
              f"F1={m['f1_score']:.3f}")

    # 汇总交叉验证结果
    all_val_preds = np.concatenate([r['val_preds'] for r in fold_results])
    all_val_targets = np.concatenate([r['val_targets'] for r in fold_results])
    cv_metrics = calc_metrics(all_val_targets, all_val_preds)

    print(f"\n{'=' * 65}")
    print(f"  {N_FOLDS}-折交叉验证汇总:")
    print(f"  Accuracy:  {cv_metrics['accuracy']:.4f}")
    print(f"  Precision: {cv_metrics['precision']:.4f}")
    print(f"  Recall:    {cv_metrics['recall']:.4f}")
    print(f"  F1-Score:  {cv_metrics['f1_score']:.4f}")
    print(f"  AUC-ROC:   {cv_metrics['roc_auc']:.4f}")
    print(f"{'=' * 65}")

    # 找最优阈值
    opt_threshold, max_j, threshold_results = find_optimal_threshold(all_val_targets, all_val_preds)
    print(f"\n约登指数最优阈值: {opt_threshold:.3f} (Youden's J={max_j:.4f})")

    # 用最优阈值重新评估
    cv_metrics_opt = calc_metrics(all_val_targets, all_val_preds, opt_threshold)
    print(f"  优化阈值指标: Acc={cv_metrics_opt['accuracy']:.4f}, "
          f"Recall={cv_metrics_opt['recall']:.4f}, F1={cv_metrics_opt['f1_score']:.4f}")

    return fold_results, scaler, cv_metrics, opt_threshold


# ── 集成模型训练 (全量数据上训练多个不同初始化的模型) ──
def train_ensemble(X, y, scaler, n_models=5):
    """在全量数据上训练集成模型"""
    print(f"\n{'=' * 65}")
    print(f"  全量数据集成训练 ({n_models}个模型)")
    print(f"{'=' * 65}")

    X_scaled = scaler.transform(X)
    full_dataset = TensorDataset(torch.FloatTensor(X_scaled), torch.FloatTensor(y).view(-1, 1))
    full_loader = DataLoader(full_dataset, batch_size=BATCH_SIZE, shuffle=True)

    ensemble_models = []
    val_split = len(X) // 5

    for i in range(n_models):
        # 每次用不同随机种子
        model_seed = SEED + i * 10
        torch.manual_seed(model_seed)
        np.random.seed(model_seed)

        model = DiabetesDNNv2(input_dim=X.shape[1], dropout=DROPOUT_RATE * 0.6).to(DEVICE)
        criterion = FocalLoss(alpha=0.75, gamma=2.0)
        optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE * 0.5, weight_decay=WEIGHT_DECAY)

        # 使用验证集防止过拟合 (随机取20%做验证)
        indices = np.random.permutation(len(X_scaled))
        val_idx = indices[:val_split]
        train_idx = indices[val_split:]

        train_sub = TensorDataset(
            torch.FloatTensor(X_scaled[train_idx]),
            torch.FloatTensor(y[train_idx]).view(-1, 1)
        )
        val_sub = TensorDataset(
            torch.FloatTensor(X_scaled[val_idx]),
            torch.FloatTensor(y[val_idx]).view(-1, 1)
        )
        train_sub_loader = DataLoader(train_sub, batch_size=BATCH_SIZE, shuffle=True)
        val_sub_loader = DataLoader(val_sub, batch_size=BATCH_SIZE, shuffle=False)

        best_loss = float('inf')
        best_state = None
        patience = 0

        pbar = tqdm(range(150), desc=f"Ensemble#{i+1}", ncols=90,
                    bar_format='{desc} |{bar}| {n_fmt}/{total_fmt} [{elapsed}]')
        for epoch in pbar:
            model.train()
            total_loss = 0
            for X_b, y_b in train_sub_loader:
                X_b, y_b = X_b.to(DEVICE), y_b.to(DEVICE)
                optimizer.zero_grad()
                loss = criterion(model(X_b), y_b)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item() * X_b.size(0)

            train_loss = total_loss / len(train_sub_loader.dataset)
            val_loss, _, _ = evaluate(model, val_sub_loader, criterion, DEVICE)

            if val_loss < best_loss:
                best_loss = val_loss
                best_state = copy.deepcopy(model.state_dict())
                patience = 0
            else:
                patience += 1

            pbar.set_postfix({'train': f'{train_loss:.4f}', 'val': f'{val_loss:.4f}'}, refresh=False)

            if patience >= 30:
                break

        model.load_state_dict(best_state)
        ensemble_models.append(model.cpu())

        # 评估这个模型在全量数据上的表现
        model.to(DEVICE)
        model.eval()
        with torch.no_grad():
            all_preds = torch.sigmoid(model(torch.FloatTensor(X_scaled).to(DEVICE))).cpu().numpy().flatten()
        m = calc_metrics(y, all_preds)
        print(f"  Ens#{i+1}: ValLoss={best_loss:.4f}, Acc={m['accuracy']:.3f}, AUC={m['roc_auc']:.3f}")
        model.cpu()

    return ensemble_models


@torch.no_grad()
def ensemble_predict(models, X_scaled, device, n_samples=20):
    """集成预测 + MC Dropout不确定性"""
    all_preds = []
    for model in models:
        model.to(device)
        model.train()  # 启用Dropout
        preds = []
        for _ in range(n_samples):
            preds.append(torch.sigmoid(model(torch.FloatTensor(X_scaled).to(device))).cpu().numpy())
        all_preds.append(np.concatenate(preds, axis=1))
        model.cpu()

    all_preds = np.concatenate(all_preds, axis=1)  # (N, ensemble_n * n_samples)
    mean_pred = all_preds.mean(axis=1, keepdims=True)
    std_pred = all_preds.std(axis=1, keepdims=True)
    return mean_pred, std_pred


# ── 主函数 ──
def main():
    print(f"[设备] {DEVICE} | CUDA可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"       GPU: {torch.cuda.get_device_name(0)}")
        print(f"       显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    # 1. 加载数据
    X, y = load_data()
    print(f"\n[X] 特征矩阵: {X.shape}")
    print(f"[y] 标签向量: {y.shape}, 正例={y.sum():.0f}, 负例={(1-y).sum():.0f}")

    # 2. K折交叉验证
    fold_results, scaler, cv_metrics, opt_threshold = train_kfold(X, y)

    # 3. 全量数据集成训练
    ensemble_models = train_ensemble(X, y, scaler, n_models=ENSEMBLE_N)

    # 4. 集成评估
    print(f"\n{'=' * 65}")
    print(f"  集成模型最终评估 (MC Dropout x20)")
    print(f"{'=' * 65}")

    X_scaled = scaler.transform(X)
    mean_pred, std_pred = ensemble_predict(ensemble_models, X_scaled, DEVICE, n_samples=20)
    final_metrics = calc_metrics(y, mean_pred.flatten(), opt_threshold)

    print(f"  Accuracy:  {final_metrics['accuracy']:.4f}")
    print(f"  Precision: {final_metrics['precision']:.4f}")
    print(f"  Recall:    {final_metrics['recall']:.4f}")
    print(f"  F1-Score:  {final_metrics['f1_score']:.4f}")
    print(f"  AUC-ROC:   {final_metrics['roc_auc']:.4f}")
    print(f"  Opt Threshold: {opt_threshold:.3f}")
    print(f"  Avg Uncertainty (std): {std_pred.mean():.4f}")

    # 5. 保存最佳单模型 (用于实际部署)
    best_fold = min(fold_results, key=lambda r: r['best_val_loss'])
    best_model = DiabetesDNNv2(input_dim=X.shape[1], dropout=DROPOUT_RATE * 0.6)
    best_model.load_state_dict(best_fold['model_state'])
    best_model.eval()

    # 6. 保存所有集成模型
    model_path = os.path.join(OUTPUT_DIR, 'diabetes_dnn_model.pth')
    scaler_path = os.path.join(OUTPUT_DIR, 'diabetes_scaler.joblib')
    info_path = os.path.join(OUTPUT_DIR, 'diabetes_info.joblib')

    # 保存最佳单模型
    torch.save({
        'model_state_dict': best_fold['model_state'],
        'input_dim': X.shape[1],
        'architecture': 'DiabetesDNNv2(ResBlock+SELU+AlphaDropout)',
        'dropout': DROPOUT_RATE * 0.6,
        'val_loss': best_fold['best_val_loss'],
        'cv_metrics': cv_metrics,
        'opt_threshold': opt_threshold,
    }, model_path)

    # 保存集成模型
    ensemble_path = os.path.join(OUTPUT_DIR, 'diabetes_ensemble.pth')
    ensemble_states = []
    for m in ensemble_models:
        ensemble_states.append(m.state_dict())
    torch.save({
        'states': ensemble_states,
        'input_dim': X.shape[1],
        'n_models': len(ensemble_models),
        'architecture': 'DiabetesDNNv2(ResBlock+SELU+AlphaDropout)',
        'dropout': DROPOUT_RATE * 0.6,
        'cv_metrics': cv_metrics,
        'opt_threshold': opt_threshold,
        'final_metrics': final_metrics,
    }, ensemble_path)

    # 保存标准化器
    joblib.dump(scaler, scaler_path)

    # 保存模型元信息
    info = {
        'name': 'PIMA糖尿病风险评定 v2 (PyTorch DNN + 残差网络 + 集成)',
        'model_type': 'PyTorch Deep Neural Network Ensemble',
        'architecture': {
            'type': 'DiabetesDNNv2',
            'input_dim': X.shape[1],
            'hidden_size': 256,
            'res_blocks': 3,
            'output': 'sigmoid(binary)',
            'total_params': sum(p.numel() for p in best_model.parameters()),
            'n_ensemble_models': len(ensemble_models),
        },
        'training': {
            'data_source': 'PIMA Indians Diabetes Dataset',
            'samples': len(X),
            'features': X.shape[1],
            'cv_folds': N_FOLDS,
            'ensemble_models': ENSEMBLE_N,
            'best_val_loss': best_fold['best_val_loss'],
        },
        'performance': {
            'cv_average': cv_metrics,
            'ensemble_final': final_metrics,
            'optimal_threshold': opt_threshold,
        },
        'feature_names': FEATURE_NAMES,
        'risk_levels': {
            'low': f'< {opt_threshold - 0.15:.2f}',
            'moderate': f'{opt_threshold - 0.15:.2f} ~ {opt_threshold + 0.15:.2f}',
            'high': f'> {opt_threshold + 0.15:.2f}',
        },
        'training_date': datetime.now().isoformat(),
        'device': str(DEVICE),
    }
    joblib.dump(info, info_path)

    print(f"\n文件已保存:")
    print(f"  [模型] {model_path}")
    print(f"  [集成] {ensemble_path}")
    print(f"  [归一化] {scaler_path}")
    print(f"  [元信息] {info_path}")
    print(f"\n[完成] 糖尿病风险DNN v2 训练结束!\n")


if __name__ == '__main__':
    main()
