import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
"""
交通异常检测模型训练脚本

使用 Isolation Forest 无监督学习检测异常交通模式。
基于流量和速度的统计偏差自动识别异常。

训练数据格式:
  section_id, hour, day_of_week,
  flow_mean, flow_std, flow_min, flow_max,
  speed_mean, speed_std, cong_mean, cong_std,
  flow_count, avg_speed,
  flow_deviation, speed_deviation

输出:
  - traffic_anomaly_iforest.pkl     # Isolation Forest 模型
  - traffic_anomaly_scaler.pkl      # 标准化器
  - traffic_anomaly_threshold.pkl   # 异常阈值
"""
import os
import sys
import pickle
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, 'python', 'data', 'traffic', 'anomaly_train.csv')
MODELS_DIR = os.path.join(BASE_DIR, 'python', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

print("=" * 60)
print("[ALERT] 交通异常检测模型训练 (Isolation Forest)")
print("=" * 60)

# 1. 加载数据
if not os.path.exists(DATA_PATH):
    print(f"[FAIL] 未找到数据文件: {DATA_PATH}")
    print("   请先运行 data/traffic/generate_traffic_data.py 生成数据")
    sys.exit(1)

df = pd.read_csv(DATA_PATH)
print(f"[DATA] 加载数据: {len(df):,} 条记录")
print(f"  异常标签率: {df['is_anomaly'].mean():.2%}")

# 2. 特征选择
feature_cols = [
    "section_id", "hour", "day_of_week",
    "flow_mean", "flow_std",
    "speed_mean", "speed_std",
    "cong_mean", "cong_std",
    "flow_deviation", "speed_deviation",
    "flow_count", "avg_speed",
]

X = df[feature_cols].fillna(0).values
y_true = df["is_anomaly"].values

# 3. 标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 4. 训练 Isolation Forest
print("\n[TRAIN] 训练 Isolation Forest 模型...")
model = IsolationForest(
    n_estimators=200,
    max_samples='auto',
    contamination=0.05,  # 预期异常率
    max_features=1.0,
    bootstrap=False,
    n_jobs=-1,
    random_state=42,
    verbose=1,
)
model.fit(X_scaled)

# 5. 评估 (使用生成的标签作为参考)
y_pred = model.predict(X_scaled)
# Isolation Forest: 1=正常, -1=异常 → 转为 0/1
y_pred_binary = (y_pred == -1).astype(int)

print("\n[DATA] 异常检测评估:")
tn, fp, fn, tp = confusion_matrix(y_true, y_pred_binary).ravel()
print(f"  True Positives:  {tp}")
print(f"  True Negatives:  {tn}")
print(f"  False Positives: {fp}")
print(f"  False Negatives: {fn}")
print(f"  准确率: {(tp + tn) / (tp + tn + fp + fn):.4f}")
print(f"  精确率: {tp / max(tp + fp, 1):.4f}")
print(f"  召回率: {tp / max(tp + fn, 1):.4f}")

# 异常评分分布
anomaly_scores = model.score_samples(X_scaled)
print(f"\n  异常分数统计:")
print(f"    均值: {anomaly_scores.mean():.4f}")
print(f"    标准差: {anomaly_scores.std():.4f}")
print(f"    异常阈值(5%分位): {np.percentile(anomaly_scores, 5):.4f}")

# 6. 保存模型和阈值
model_path = os.path.join(MODELS_DIR, "traffic_anomaly_iforest.pkl")
scaler_path = os.path.join(MODELS_DIR, "traffic_anomaly_scaler.pkl")
threshold_path = os.path.join(MODELS_DIR, "traffic_anomaly_threshold.pkl")

joblib.dump(model, model_path)
joblib.dump(scaler, scaler_path)

# 保存异常阈值 (5% 分位点)
threshold = np.percentile(anomaly_scores, 5)
joblib.dump({
    "threshold": threshold,
    "feature_cols": feature_cols,
    "contamination": 0.05,
    "train_anomaly_rate": y_true.mean(),
}, threshold_path)

print(f"\n[OK] 模型保存完成:")
print(f"  {model_path}")
print(f"  {scaler_path}")
print(f"  {threshold_path}")

# 7. 使用示例
print("\n" + "=" * 60)
print("📝 使用示例:")
print("=" * 60)

# 构造一个正常的和一个异常的样本
normal_sample = np.array([[1, 8, 2, 1500, 300, 45, 10, 0.6, 0.2, 0.1, 0.2, 1600, 42]])
abnormal_sample = np.array([[1, 8, 2, 1500, 300, 45, 10, 0.6, 0.2, 3.5, -3.0, 500, 15]])

normal_scaled = scaler.transform(normal_sample)
abnormal_scaled = scaler.transform(abnormal_sample)

normal_pred = model.predict(normal_scaled)[0]
abnormal_pred = model.predict(abnormal_scaled)[0]
normal_score = model.score_samples(normal_scaled)[0]
abnormal_score = model.score_samples(abnormal_scaled)[0]

print(f"  正常样本: 预测={normal_pred} (1=正常), 分数={normal_score:.4f}, "
      f"{'[FAIL] 异常' if normal_pred == -1 else '[OK] 正常'}")
print(f"  异常样本: 预测={abnormal_pred} (1=正常), 分数={abnormal_score:.4f}, "
      f"{'[FAIL] 异常' if abnormal_pred == -1 else '[OK] 正常'}")
print("\n[OK] 训练完成!")
