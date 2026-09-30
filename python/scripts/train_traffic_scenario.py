import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
"""
交通场景仿真模型训练脚本

使用 XGBoost 回归模拟交通改善措施 (增车道/调限速/优化信号) 对交通流的影响。

输入:
  路段特征 + 变更类型 + 变更幅度 → 预测结果流量 + 速度

输出:
  - traffic_scenario_model.pkl     # XGBoost 模型
  - traffic_scenario_scaler.pkl    # 标准化器
"""
import os
import sys
import pickle
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error, r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, 'python', 'data', 'traffic', 'scenario_train.csv')
MODELS_DIR = os.path.join(BASE_DIR, 'python', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

print("=" * 60)
print("[SCENARIO] 交通场景仿真模型训练")
print("=" * 60)

# 1. 加载数据
if not os.path.exists(DATA_PATH):
    print(f"[FAIL] 未找到数据文件: {DATA_PATH}")
    sys.exit(1)

df = pd.read_csv(DATA_PATH)
print(f"[DATA] 加载数据: {len(df):,} 条场景记录")

# 2. 特征编码
change_type_map = {"add_lane": 0, "change_speed": 1}
df["change_type_code"] = df["change_type"].map(change_type_map).fillna(0)

feature_cols = [
    "road_type", "lanes", "speed_limit",
    "hour", "day_of_week",
    "change_type_code", "change_value",
    "base_flow", "base_speed",
]

target_cols = ["result_flow", "result_speed"]

X = df[feature_cols].fillna(0).values
y = df[target_cols].values

# 3. 切分
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 4. 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. 训练 XGBoost 多输出模型
print("\n[TRAIN] 训练 XGBoost 场景仿真模型...")
model = MultiOutputRegressor(
    xgb.XGBRegressor(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
)
model.fit(X_train_scaled, y_train)

# 6. 评估
y_pred = model.predict(X_test_scaled)
print("\n[DATA] 模型评估:")
for i, target in enumerate(target_cols):
    mae = mean_absolute_error(y_test[:, i], y_pred[:, i])
    r2 = r2_score(y_test[:, i], y_pred[:, i])
    print(f"  {target}: MAE={mae:.2f}, R²={r2:.4f}")

# 7. 保存
model_path = os.path.join(MODELS_DIR, "traffic_scenario_model.pkl")
scaler_path = os.path.join(MODELS_DIR, "traffic_scenario_scaler.pkl")
encoders_path = os.path.join(MODELS_DIR, "traffic_scenario_encoders.pkl")

joblib.dump(model, model_path)
joblib.dump(scaler, scaler_path)
joblib.dump({
    "feature_cols": feature_cols,
    "target_cols": target_cols,
    "change_type_map": change_type_map,
    "change_type_names": {0: "增加车道", 1: "调整限速"},
}, encoders_path)

print(f"\n[OK] 模型保存完成:")
print(f"  {model_path}")
print(f"  {scaler_path}")
print(f"  {encoders_path}")

# 8. 示例
print("\n" + "=" * 60)
print("📝 场景仿真示例:")
print("=" * 60)

# 场景1: 增加2条车道
s1 = np.array([[1, 6, 70, 8, 2, 0, 2, 1800, 40]])
# 场景2: 限速提升10km/h
s2 = np.array([[1, 6, 70, 8, 2, 1, 10, 1800, 40]])

for label, sample in [("增加2车道", s1), ("限速+10km/h", s2)]:
    s = scaler.transform(sample)
    pred = model.predict(s)[0]
    base_flow, base_speed = sample[0, 7], sample[0, 8]
    print(f"  {label}:")
    print(f"    流量: {base_flow:.0f} → {pred[0]:.0f} 辆/小时 "
          f"(+{(pred[0]/base_flow - 1)*100:.1f}%)")
    print(f"    速度: {base_speed:.0f} → {pred[1]:.1f} km/h "
          f"(+{(pred[1]/base_speed - 1)*100:.1f}%)")

print("\n[OK] 训练完成!")
