"""
AQI Level Early Warning - ExtraTrees + XGBoost
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def train():
    print("=" * 60)
    print("Training AQI Level Early Warning Model")
    print("=" * 60)
    np.random.seed(42)
    n_samples = 1500

    pm25 = np.random.uniform(0, 300, n_samples)
    pm10 = pm25 * np.random.uniform(0.8, 1.5, n_samples)
    o3 = np.random.uniform(0, 200, n_samples)
    no2 = np.random.uniform(0, 100, n_samples)
    so2 = np.random.uniform(0, 50, n_samples)
    co = np.random.uniform(0, 5, n_samples)
    temp = np.random.uniform(-5, 40, n_samples)
    humidity = np.random.uniform(20, 90, n_samples)

    aqi_calc = (pm25 * 0.3 + pm10 * 0.2 + o3 * 0.2 + no2 * 0.1 + so2 * 0.1 + co * 0.1)
    noise = np.random.normal(0, 10, n_samples)
    aqi = aqi_calc + noise

    def aqi_level(aqi_val):
        if aqi_val <= 50: return 0
        elif aqi_val <= 100: return 1
        elif aqi_val <= 150: return 2
        elif aqi_val <= 200: return 3
        elif aqi_val <= 300: return 4
        else: return 5

    labels = np.array([aqi_level(v) for v in aqi])
    level_names = ["优", "良", "轻度污染", "中度污染", "重度污染", "严重污染"]

    features = np.column_stack([pm25, pm10, o3, no2, so2, co, temp, humidity])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, labels, test_size=0.2, random_state=42)

    model = ExtraTreesClassifier(n_estimators=200, max_depth=15, random_state=42)
    model.fit(X_train, y_train)
    acc = model.score(X_test, y_test)
    print(f"Test accuracy: {acc:.4f}")

    le = LabelEncoder()
    le.fit(labels)
    le.classes_ = np.array(level_names)

    joblib.dump(model, os.path.join(BASE_DIR, "aqi_forecast_model.joblib"))
    joblib.dump(scaler, os.path.join(BASE_DIR, "aqi_forecast_scaler.joblib"))
    joblib.dump(le, os.path.join(BASE_DIR, "aqi_level_encoder.joblib"))
    print(f"Models saved. Test accuracy: {acc:.2%}")

if __name__ == "__main__":
    train()
