import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
"""
交通事故影响分析模型训练脚本

使用 GradientBoosting 回归模型预测交通事故对交通流的影响程度。

输入:
  路段特征 + 事故严重程度 → 流量/速度下降百分比

输出:
  - traffic_accident_impact_model.pkl   # GradientBoosting 模型
  - traffic_accident_impact_scaler.pkl  # 标准化器
  - traffic_accident_impact_encoders.pkl
"""
import os
import sys
import pickle
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error, r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, 'python', 'data', 'traffic', 'accident_train.csv')
MODELS_DIR = os.path.join(BASE_DIR, 'python', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

print("=" * 60)
print("[ACCIDENT] 交通事故影响分析模型训练")
print("=" * 60)

# 1. 加载数据
if not os.path.exists(DATA_PATH):
    print(f"[FAIL] 未找到数据文件: {DATA_PATH}")
    print("   请先运行 data/traffic/generate_traffic_data.py 生成数据")
    sys.exit(1)

df = pd.read_csv(DATA_PATH)
print(f"[DATA] 加载数据: {len(df):,} 条事故记录")

# 2. 特征
feature_cols = [
    "section_id", "road_type", "lanes", "speed_limit",
    "hour", "day_of_week", "weather_code",
    "accident_severity",
    "normal_flow", "normal_speed",
]

# 目标: 流量下降百分比, 速度下降百分比
target_cols = ["flow_reduction_pct", "speed_reduction_pct"]

# 查看是否有需要的列
available_features = [c for c in feature_cols if c in df.columns]
available_targets = [c for c in target_cols if c in df.columns]

print(f"  可用特征: {available_features}")
print(f"  预测目标: {available_targets}")

X = df[available_features].fillna(0).values
y = df[available_targets].fillna(0).values

# 3. 切分
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 4. 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. 训练
print("\n[TRAIN] 训练 GradientBoosting 模型...")
model = MultiOutputRegressor(
    GradientBoostingRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )
)
model.fit(X_train_scaled, y_train)

# 6. 评估
y_pred = model.predict(X_test_scaled)
print("\n[DATA] 模型评估:")

for i, target in enumerate(available_targets):
    mae = mean_absolute_error(y_test[:, i], y_pred[:, i])
    r2 = r2_score(y_test[:, i], y_pred[:, i])
    print(f"  {target}: MAE={mae:.2f}%, R²={r2:.4f}")

# 7. 保存
model_path = os.path.join(MODELS_DIR, "traffic_accident_impact_model.pkl")
scaler_path = os.path.join(MODELS_DIR, "traffic_accident_impact_scaler.pkl")
encoders_path = os.path.join(MODELS_DIR, "traffic_accident_impact_encoders.pkl")

joblib.dump(model, model_path)
joblib.dump(scaler, scaler_path)
joblib.dump({
    "feature_cols": available_features,
    "target_cols": available_targets,
}, encoders_path)

print(f"\n[OK] 模型保存完成:")
print(f"  {model_path}")
print(f"  {scaler_path}")
print(f"  {encoders_path}")

# 8. 示例
print("\n" + "=" * 60)
print("📝 事故影响预测示例:")
print("=" * 60)

# 轻微事故
sample1 = np.array([[1, 1, 6, 70, 8, 2, 0, 0.2, 1500, 45]])
# 严重事故
sample2 = np.array([[1, 1, 6, 70, 18, 2, 0, 0.7, 1800, 35]])

for label, sample in [("轻微追尾", sample1), ("多车碰撞(晚高峰)", sample2)]:
    s = scaler.transform(sample)
    pred = model.predict(s)[0]
    print(f"  {label}:")
    print(f"    流量下降: {pred[0]:.1f}%")
    print(f"    速度下降: {pred[1]:.1f}%")

print("\n[OK] 训练完成!")
