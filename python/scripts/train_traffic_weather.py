import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
"""
天气-交通影响分析模型训练脚本

使用 XGBoost 回归模型预测不同天气条件下交通流速度和流量的变化。

输入:
  weather_code, road_type, hour → flow_count, avg_speed, congestion_index

输出:
  - traffic_weather_model.pkl        # XGBoost 模型
  - traffic_weather_scaler.pkl       # 标准化器
  - traffic_weather_encoders.pkl     # 编码器 + 元数据
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
from sklearn.metrics import mean_absolute_error, r2_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, 'python', 'data', 'traffic', 'weather_train.csv')
MODELS_DIR = os.path.join(BASE_DIR, 'python', 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

print("=" * 60)
print("🌤️ 天气-交通影响模型训练")
print("=" * 60)

# 1. 加载数据
if not os.path.exists(DATA_PATH):
    print(f"[FAIL] 未找到数据文件: {DATA_PATH}")
    sys.exit(1)

df = pd.read_csv(DATA_PATH)
print(f"[DATA] 加载数据: {len(df):,} 条记录")

# 天气名称映射
WEATHER_NAMES = {
    0: "晴", 1: "多云", 2: "小雨", 3: "中雨", 4: "暴雨",
    5: "小雪", 6: "中雪", 7: "大雪", 8: "雾"
}

# 2. 特征工程
feature_cols = ["weather_code", "road_type", "hour", "temperature", "humidity"]
target_cols = ["flow_count", "avg_speed", "congestion_index"]

X = df[feature_cols].fillna(0).values
y_dict = {}
for col in target_cols:
    if col in df.columns:
        y_dict[col] = df[col].values

# 3. 训练三个独立的单输出模型 (更易解释)
models = {}
scalers = {}

for target in target_cols:
    if target not in y_dict:
        continue
    
    y = y_dict[target]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print(f"\n[TRAIN] 训练 {target} 预测模型...")
    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=False
    )
    
    y_pred = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"  {target}: MAE={mae:.2f}, R²={r2:.4f}")
    
    models[target] = model
    scalers[target] = scaler

# 4. 保存模型
model_path = os.path.join(MODELS_DIR, "traffic_weather_model.pkl")
scaler_path = os.path.join(MODELS_DIR, "traffic_weather_scaler.pkl")
encoder_path = os.path.join(MODELS_DIR, "traffic_weather_encoders.pkl")

joblib.dump(models, model_path)
joblib.dump(scalers, scaler_path)
joblib.dump({
    "feature_cols": feature_cols,
    "target_cols": target_cols,
    "weather_names": WEATHER_NAMES,
    "road_type_names": {0: "次干道", 1: "主干道", 2: "快速路"},
}, encoder_path)

print(f"\n[OK] 模型保存完成:")
print(f"  {model_path}")
print(f"  {scaler_path}")
print(f"  {encoder_path}")

# 5. 展示天气影响
print("\n" + "=" * 60)
print("[DATA] 不同天气条件下的交通影响:")
print("=" * 60)

weather_demo = pd.DataFrame([
    {"weather_code": w, "road_type": 1, "hour": h, "temperature": 20, "humidity": 50}
    for w in [0, 2, 4, 7, 8]
    for h in [8, 14, 18]
])

for w in [0, 2, 4, 7, 8]:
    for h in [8, 14, 18]:
        sample = np.array([[w, 1, h, 20, 50]])
        
        results = []
        for target in target_cols:
            if target in models:
                s = scalers[target].transform(sample)
                pred = models[target].predict(s)[0]
                results.append(pred)
        
        weather_name = WEATHER_NAMES.get(w, f"未知({w})")
        period = "早高峰" if h == 8 else "下午" if h == 14 else "晚高峰"
        
        if len(results) == 3:
            print(f"  {weather_name:4s} | {period} | "
                  f"流量={results[0]:7.0f} | 速度={results[1]:5.1f}km/h | "
                  f"拥堵={results[2]:.3f}")

print("\n[OK] 训练完成!")
