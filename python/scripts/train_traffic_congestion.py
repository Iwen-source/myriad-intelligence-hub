import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
"""
交通拥堵预测模型训练脚本

使用真实交通数据训练的 XGBoost 多输出回归模型。
预测给定时间+路段条件下的:
  - 车流量 (flow_count)
  - 平均速度 (avg_speed)
  - 拥堵指数 (congestion_index)

输入特征:
  时间特征: hour, day_of_week, month, season, is_weekend, is_holiday
  周期性编码: hour_sin, hour_cos, day_sin, day_cos
  天气特征: weather_code, temperature, humidity
  路段特征: lanes, speed_limit, road_type

输出:
  - traffic_congestion_model.pkl     # XGBoost 模型
  - traffic_congestion_scaler.pkl    # 特征标准化器
  - traffic_congestion_encoders.pkl  # 编码器
"""
import os
import sys
import pickle
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.multioutput import MultiOutputRegressor
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, 'python', 'data', 'traffic', 'congestion_train.csv')
MODELS_DIR = os.path.join(BASE_DIR, 'python', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

print("=" * 60)
print("[TRAFFIC] 交通拥堵预测模型训练")
print("=" * 60)

# 1. 加载数据
if not os.path.exists(DATA_PATH):
    print(f"[FAIL] 未找到数据文件: {DATA_PATH}")
    print("   请先运行 data/traffic/generate_traffic_data.py 生成数据")
    sys.exit(1)

df = pd.read_csv(DATA_PATH)
print(f"[DATA] 加载数据: {len(df):,} 条记录")
print(f"  字段: {list(df.columns)}")

# 2. 特征工程
feature_cols = [
    "hour", "day_of_week", "month", "season", "is_weekend", "is_holiday",
    "weather_code", "temperature", "humidity",
    "lanes", "speed_limit",
    "hour_sin", "hour_cos", "day_sin", "day_cos",
]

# 道路类型编码 (如果存在)
if "road_type" in df.columns:
    road_type_map = {"快速路": 2, "主干道": 1, "次干道": 0}
    df["road_type"] = df["road_type"].map(road_type_map).fillna(0)
    feature_cols.append("road_type")

target_cols = ["flow_count", "avg_speed", "congestion_index"]

# 3. 切分数据
X = df[feature_cols].values
y = df[target_cols].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42
)

print(f"\n[DATA] 数据集划分:")
print(f"  训练集: {len(X_train):,} 条")
print(f"  测试集: {len(X_test):,} 条")

# 4. 标准化特征
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. 训练 XGBoost 多输出回归模型
print("\n[TRAIN] 训练 XGBoost 模型...")

model = MultiOutputRegressor(
    xgb.XGBRegressor(
        n_estimators=500,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        verbosity=1,
    )
)
model.fit(X_train_scaled, y_train)

# 6. 评估
y_pred = model.predict(X_test_scaled)

print("\n[DATA] 模型评估:")
for i, target in enumerate(target_cols):
    mae = mean_absolute_error(y_test[:, i], y_pred[:, i])
    rmse = np.sqrt(mean_squared_error(y_test[:, i], y_pred[:, i]))
    r2 = r2_score(y_test[:, i], y_pred[:, i])
    print(f"  {target}:")
    print(f"    MAE  = {mae:.2f}")
    print(f"    RMSE = {rmse:.2f}")
    print(f"    R²   = {r2:.4f}")

# 7. 保存模型
model_path = os.path.join(MODELS_DIR, "traffic_congestion_model.pkl")
scaler_path = os.path.join(MODELS_DIR, "traffic_congestion_scaler.pkl")
encoder_path = os.path.join(MODELS_DIR, "traffic_congestion_encoders.pkl")

joblib.dump(model, model_path)
joblib.dump(scaler, scaler_path)
joblib.dump({
    "feature_cols": feature_cols,
    "target_cols": target_cols,
    "road_type_map": {"快速路": 2, "主干道": 1, "次干道": 0},
}, encoder_path)

print(f"\n[OK] 模型保存完成:")
print(f"  {model_path}")
print(f"  {scaler_path}")
print(f"  {encoder_path}")
print(f"\n总文件大小: {os.path.getsize(model_path) / 1024:.1f} KB")

# 8. 简单使用示例
print("\n" + "=" * 60)
print("📝 使用示例:")
print("=" * 60)
sample = np.array([[
    8,    # hour (早8点)
    2,    # day_of_week (周二)
    5,    # month (5月)
    2,    # season (春)
    0,    # is_weekend
    0,    # is_holiday
    0,    # weather_code (晴)
    25.0, # temperature
    50.0, # humidity
    6,    # lanes
    70,   # speed_limit
    0.5,  # hour_sin
    0.866,# hour_cos
    0.435,# day_sin
    0.901,# day_cos
    1,    # road_type (主干道)
]])
sample_scaled = scaler.transform(sample)
pred = model.predict(sample_scaled)[0]
print(f"    输入: 周二早8点, 晴, 6车道主干道, 限速70")
print(f"    预测: 流量={pred[0]:.0f} 辆/小时, "
      f"速度={pred[1]:.1f} km/h, "
      f"拥堵指数={pred[2]:.4f}")
print("\n[OK] 训练完成!")
