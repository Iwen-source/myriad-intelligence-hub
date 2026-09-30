"""
Traffic Congestion Model: Multi-output prediction
- Predicts: avg_speed, flow_count, congestion_index, accident_probability
- Features: hour, day_of_week, is_weekend, is_holiday, season, weather_code, section_capacity
Generates: traffic_model.joblib, traffic_scaler.joblib, traffic_features.joblib
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

N = 5000

# ── Generate synthetic traffic data ──
data = []
for _ in range(N):
    hour = np.random.randint(0, 24)
    day_of_week = np.random.randint(1, 8)
    is_weekend = 1 if day_of_week >= 6 else 0
    is_holiday = np.random.choice([0, 1], p=[0.95, 0.05])
    season = np.random.randint(1, 5)  # 1=spring, 2=summer, 3=autumn, 4=winter
    weather_code = np.random.choice([0, 1, 2, 3], p=[0.55, 0.25, 0.15, 0.05])  # 0=clear, 1=cloudy, 2=rain, 3=snow
    section_capacity = np.random.choice([1200, 1500, 1800, 2200, 2800])  # vehicles/hour per lane set
    lanes = np.random.choice([2, 3, 4, 5, 6])
    speed_limit = np.random.choice([40, 50, 60, 70, 80])
    road_type = np.random.choice([0, 1, 2], p=[0.4, 0.35, 0.25])  # 0=主干道, 1=快速路, 2=支路

    # Traffic flow base (rush hour patterns)
    if 7 <= hour <= 9:
        base_flow = np.random.uniform(0.7, 1.0) * 4000
    elif 17 <= hour <= 19:
        base_flow = np.random.uniform(0.65, 0.95) * 4000
    elif 22 <= hour or hour <= 5:
        base_flow = np.random.uniform(0.05, 0.15) * 4000
    else:
        base_flow = np.random.uniform(0.2, 0.5) * 4000

    # Weather impact
    weather_factor = {0: 1.0, 1: 0.9, 2: 0.7, 3: 0.5}[weather_code]
    # Weekend factor
    weekend_factor = 0.65 if is_weekend else 1.0
    # Season factor
    season_factor = {1: 1.0, 2: 0.95, 3: 1.05, 4: 0.85}[season]

    flow = base_flow * weather_factor * weekend_factor * season_factor
    flow = max(50, min(8000, flow + np.random.normal(0, flow * 0.1)))

    # Speed based on flow/capacity ratio
    total_capacity = section_capacity * lanes * 0.8
    vc_ratio = flow / max(total_capacity, 1)
    if vc_ratio < 0.4:
        base_speed = speed_limit * np.random.uniform(0.85, 1.0)
    elif vc_ratio < 0.7:
        base_speed = speed_limit * np.random.uniform(0.65, 0.85)
    elif vc_ratio < 0.9:
        base_speed = speed_limit * np.random.uniform(0.4, 0.65)
    else:
        base_speed = speed_limit * np.random.uniform(0.1, 0.4)

    # Weather further reduces speed
    speed_weather = {0: 1.0, 1: 0.92, 2: 0.75, 3: 0.55}[weather_code]
    speed = base_speed * speed_weather
    speed = max(5, min(speed_limit, speed + np.random.normal(0, 3)))

    # Congestion index (0-1)
    congestion_index = max(0, min(1, 1.0 - speed / speed_limit * (1 - 0.3 * weather_code / 3)))
    # Accident probability (hour+weather+flow factor)
    accident_base = 0.001 + (0.003 if weather_code >= 2 else 0) + abs(hour - 12) * 0.0002 + vc_ratio * 0.005
    accident_prob = min(0.1, accident_base + np.random.exponential(0.002))

    data.append({
        'hour': hour, 'day_of_week': day_of_week, 'is_weekend': is_weekend,
        'is_holiday': is_holiday, 'season': season, 'weather_code': weather_code,
        'section_capacity': section_capacity, 'lanes': lanes,
        'speed_limit': speed_limit, 'road_type': road_type,
        'avg_speed': round(speed, 1), 'flow_count': round(flow),
        'congestion_index': round(congestion_index, 4),
        'accident_probability': round(accident_prob, 4)
    })

df = pd.DataFrame(data)
print(f"Generated {len(df)} traffic records")

# ── Feature engineering ──
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

feature_cols = ['hour_sin', 'hour_cos', 'day_sin', 'day_cos',
                'is_weekend', 'is_holiday', 'season',
                'weather_code', 'section_capacity', 'lanes',
                'speed_limit', 'road_type']
target_cols = ['avg_speed', 'flow_count', 'congestion_index', 'accident_probability']

X = df[feature_cols].values.astype(np.float32)
y = df[target_cols].values.astype(np.float32)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_tr, X_te, y_tr, y_te = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
print(f"Train: {len(X_tr)}, Test: {len(X_te)}, Features: {len(feature_cols)}")

# ── Train model ──
model = RandomForestRegressor(
    n_estimators=100, max_depth=12, min_samples_leaf=3,
    random_state=42, n_jobs=-1
)
model.fit(X_tr, y_tr)

# ── Evaluate ──
y_pred = model.predict(X_te)
for i, col in enumerate(target_cols):
    mae = mean_absolute_error(y_te[:, i], y_pred[:, i])
    r2 = r2_score(y_te[:, i], y_pred[:, i])
    print(f"  {col}: MAE={mae:.3f}, R2={r2:.3f}")

# ── Train anomaly detection model ──
anomaly_model = IsolationForest(
    n_estimators=100, contamination=0.05, random_state=42
)
anomaly_model.fit(X_scaled)
anomaly_pred = anomaly_model.predict(X_scaled)
print(f"Anomalies detected: {(anomaly_pred == -1).sum()} / {len(anomaly_pred)}")

# ── Save models ──
joblib.dump(model, os.path.join(BASE_DIR, 'traffic_model.joblib'))
joblib.dump(scaler, os.path.join(BASE_DIR, 'traffic_scaler.joblib'))
joblib.dump(anomaly_model, os.path.join(BASE_DIR, 'traffic_anomaly_model.joblib'))
joblib.dump(feature_cols, os.path.join(BASE_DIR, 'traffic_features.joblib'))
print("Saved: traffic_model.joblib, traffic_scaler.joblib, traffic_anomaly_model.joblib")
