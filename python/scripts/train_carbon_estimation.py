"""
Carbon Emission Estimation - RandomForest
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def train():
    print("=" * 60)
    print("Training Carbon Emission Estimation Model")
    print("=" * 60)
    np.random.seed(42)
    n_samples = 800

    electricity = np.random.uniform(100, 5000, n_samples)  # kWh
    coal = np.random.uniform(0, 1000, n_samples)           # kg
    oil = np.random.uniform(0, 500, n_samples)              # liters
    gas = np.random.uniform(0, 300, n_samples)              # m3
    prod_scale = np.random.uniform(1, 10, n_samples)
    efficiency = np.random.uniform(0.5, 1.0, n_samples)
    season = np.random.choice([0, 1, 2, 3], n_samples)

    carbon_target = (
        electricity * 0.0007 +
        coal * 2.5 +
        oil * 2.3 +
        gas * 2.0
    ) * prod_scale * (1.1 - efficiency) * (1 + 0.1 * np.sin(season * np.pi / 2))
    carbon_target += np.random.normal(0, carbon_target * 0.05)

    season_encoded = np.eye(4)[season]

    features = np.column_stack([electricity, coal, oil, gas, prod_scale, efficiency, season_encoded])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, carbon_target, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = model.score(X_test, y_test)
    mae = np.mean(np.abs(y_pred - y_test))
    print(f"R2 = {r2:.4f}, MAE = {mae:.2f} tons")

    joblib.dump(model, os.path.join(BASE_DIR, "carbon_model.joblib"))
    joblib.dump(scaler, os.path.join(BASE_DIR, "carbon_scaler.joblib"))
    print("Models saved to", BASE_DIR)

if __name__ == "__main__":
    train()
