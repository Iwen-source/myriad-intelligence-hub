"""
Environment Model: AQI (Air Quality Index) Prediction + Main Pollutant Identification
- RandomForestRegressor for multi-pollutant → AQI prediction
- Feature importance for main pollutant contribution
Generates: environment_model.joblib
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
import joblib
import os
import random
import math

random.seed(42)
np.random.seed(42)

# ── Pollutant features ─────────────────────────────────────────────────
POLLUTANT_FEATURES = ["pm25", "pm10", "o3", "no2", "so2", "co"]
ENV_FEATURES = POLLUTANT_FEATURES + ["temperature", "humidity"]

# AQI breakpoints (simplified Chinese standard)
AQI_BREAKPOINTS = [
    (0, 50, "优", "空气质量令人满意，基本无空气污染。"),
    (51, 100, "良", "空气质量可接受，某些污染物可能对极少数敏感人群有轻微影响。"),
    (101, 150, "轻度污染", "敏感人群症状有轻度加剧，健康人群出现刺激症状。建议减少户外活动。"),
    (151, 200, "中度污染", "进一步加剧敏感人群症状，可能对健康人群心脏、呼吸系统有影响。建议减少外出。"),
    (201, 300, "重度污染", "心脏病和肺病患者症状显著加剧。建议避免户外活动。"),
    (301, 500, "严重污染", "健康人群运动耐受力降低。建议留在室内并使用空气净化器。"),
]


def get_aqi_level(aqi: float) -> dict:
    """Get AQI level name and health advice."""
    for low, high, level, advice in AQI_BREAKPOINTS:
        if low <= aqi <= high:
            return {"level": level, "advice": advice}
    return {"level": "严重污染", "advice": "健康人群运动耐受力降低。建议留在室内并使用空气净化器。"}


def compute_aqi(pm25, pm10, o3, no2, so2, co):
    """
    Simplified AQI calculation based on individual pollutant AQI sub-scores.
    AQI = max(sub_aqi for each pollutant).
    Uses linear interpolation between breakpoints (simplified).
    """
    # Simplified sub-AQI calculations (based on Chinese AQI standard ranges)
    def sub_aqi_pm25(val):
        breakpoints = [(0, 35, 0, 50), (35, 75, 50, 100), (75, 115, 100, 150),
                       (115, 150, 150, 200), (150, 250, 200, 300), (250, 500, 300, 500)]
        for c_low, c_high, aqi_low, aqi_high in breakpoints:
            if c_low <= val <= c_high:
                return aqi_low + (aqi_high - aqi_low) * (val - c_low) / (c_high - c_low)
        return 500

    def sub_aqi_pm10(val):
        breakpoints = [(0, 50, 0, 50), (50, 150, 50, 100), (150, 250, 100, 150),
                       (250, 350, 150, 200), (350, 420, 200, 300), (420, 600, 300, 500)]
        for c_low, c_high, aqi_low, aqi_high in breakpoints:
            if c_low <= val <= c_high:
                return aqi_low + (aqi_high - aqi_low) * (val - c_low) / (c_high - c_low)
        return 500

    def sub_aqi_o3(val):
        breakpoints = [(0, 100, 0, 50), (100, 160, 50, 100), (160, 215, 100, 150),
                       (215, 265, 150, 200), (265, 800, 200, 300)]
        for c_low, c_high, aqi_low, aqi_high in breakpoints:
            if c_low <= val <= c_high:
                return aqi_low + (aqi_high - aqi_low) * (val - c_low) / (c_high - c_low)
        return 300

    def sub_aqi_no2(val):
        breakpoints = [(0, 100, 0, 50), (100, 200, 50, 100), (200, 700, 100, 150),
                       (700, 1200, 150, 200), (1200, 2340, 200, 300), (2340, 3090, 300, 500)]
        for c_low, c_high, aqi_low, aqi_high in breakpoints:
            if c_low <= val <= c_high:
                return aqi_low + (aqi_high - aqi_low) * (val - c_low) / (c_high - c_low)
        return 500

    def sub_aqi_so2(val):
        breakpoints = [(0, 50, 0, 50), (50, 150, 50, 100), (150, 475, 100, 150),
                       (475, 800, 150, 200), (800, 1600, 200, 300), (1600, 2100, 300, 500)]
        for c_low, c_high, aqi_low, aqi_high in breakpoints:
            if c_low <= val <= c_high:
                return aqi_low + (aqi_high - aqi_low) * (val - c_low) / (c_high - c_low)
        return 500

    def sub_aqi_co(val):
        breakpoints = [(0, 5, 0, 50), (5, 10, 50, 100), (10, 35, 100, 150),
                       (35, 60, 150, 200), (60, 90, 200, 300), (90, 150, 300, 500)]
        for c_low, c_high, aqi_low, aqi_high in breakpoints:
            if c_low <= val <= c_high:
                return aqi_low + (aqi_high - aqi_low) * (val - c_low) / (c_high - c_low)
        return 500

    subs = {
        "pm25": sub_aqi_pm25(pm25),
        "pm10": sub_aqi_pm10(pm10),
        "o3": sub_aqi_o3(o3),
        "no2": sub_aqi_no2(no2),
        "so2": sub_aqi_so2(so2),
        "co": sub_aqi_co(co),
    }

    aqi = max(subs.values())
    main_pollutant = max(subs, key=subs.get)

    return round(aqi, 1), main_pollutant, subs


def generate_environment_dataset(n_samples=1200):
    """Generate synthetic air quality data with realistic correlations."""
    rows = []
    for _ in range(n_samples):
        # Generate correlated pollutants with some randomness
        # Base values for different air quality scenarios
        scenario = random.random()

        if scenario < 0.3:  # Good air quality
            pm25 = random.gauss(25, 10)
            pm10 = random.gauss(40, 15)
            o3 = random.gauss(60, 20)
            no2 = random.gauss(30, 15)
            so2 = random.gauss(15, 8)
            co = random.gauss(1.0, 0.5)
        elif scenario < 0.6:  # Moderate
            pm25 = random.gauss(60, 20)
            pm10 = random.gauss(100, 30)
            o3 = random.gauss(100, 30)
            no2 = random.gauss(60, 20)
            so2 = random.gauss(30, 12)
            co = random.gauss(2.0, 0.8)
        elif scenario < 0.85:  # Unhealthy
            pm25 = random.gauss(120, 30)
            pm10 = random.gauss(200, 40)
            o3 = random.gauss(160, 30)
            no2 = random.gauss(100, 25)
            so2 = random.gauss(50, 15)
            co = random.gauss(4.0, 1.0)
        else:  # Very unhealthy
            pm25 = random.gauss(200, 40)
            pm10 = random.gauss(350, 50)
            o3 = random.gauss(200, 30)
            no2 = random.gauss(180, 30)
            so2 = random.gauss(80, 20)
            co = random.gauss(8.0, 2.0)

        # Clip to realistic ranges
        pm25 = max(0, pm25)
        pm10 = max(0, pm10)
        o3 = max(0, o3)
        no2 = max(0, no2)
        so2 = max(0, so2)
        co = max(0, co)

        # Temperature and humidity (weather-related)
        temperature = random.gauss(20, 10)  # Celsius
        humidity = random.gauss(55, 20)  # Percentage

        # Compute AQI
        aqi, main_pollutant, subs = compute_aqi(pm25, pm10, o3, no2, so2, co)

        rows.append(
            {
                "pm25": round(pm25, 1),
                "pm10": round(pm10, 1),
                "o3": round(o3, 1),
                "no2": round(no2, 1),
                "so2": round(so2, 1),
                "co": round(co, 2),
                "temperature": round(temperature, 1),
                "humidity": round(humidity, 1),
                "aqi": aqi,
                "main_pollutant": main_pollutant,
            }
        )

    df = pd.DataFrame(rows)
    return df


def train():
    print("=" * 60)
    print("Training Environment Model (AQI Prediction)")
    print("=" * 60)

    # Generate dataset
    df = generate_environment_dataset(1200)

    X = df[ENV_FEATURES].values
    y = df["aqi"].values

    print(f"Dataset: {len(df)} samples, {len(ENV_FEATURES)} features")
    print(f"AQI range: {y.min():.1f} - {y.max():.1f}")
    print(f"AQI mean: {y.mean():.1f}, std: {y.std():.1f}")

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train RandomForestRegressor
    print("\n--- AQI Prediction Model ---")
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    print(f"RMSE: {rmse:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"R2:   {r2:.4f}")

    # Feature importance
    print("\n--- Feature Importance (Main Pollutant Identification) ---")
    feature_importance = sorted(
        zip(ENV_FEATURES, model.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    )
    for name, imp in feature_importance:
        print(f"  {name}: {imp:.4f}")

    # Evaluate main pollutant identification accuracy
    print("\n--- Main Pollutant Identification Accuracy ---")
    # For each test sample, predict AQI and determine which single feature
    # contributes most (based on feature importance * value)
    correct = 0
    for i in range(len(X_test)):
        actual_main = df.iloc[y_test.index[i] if hasattr(y_test, 'index') else i]["main_pollutant"] if i < len(X_test) else "pm25"
        # Check from original df
        idx = y_test.index[i] if hasattr(y_test, 'index') else i
        actual_main = df.iloc[idx]["main_pollutant"]

        # Our approach: pollutant with highest weighted contribution
        scaled_vals = X_test_scaled[i]
        contributions = {
            ENV_FEATURES[j]: model.feature_importances_[j] * scaled_vals[j]
            for j in range(len(POLLUTANT_FEATURES))
        }
        predicted_main = max(contributions, key=contributions.get)

        if actual_main == predicted_main:
            correct += 1

    print(f"  Accuracy: {correct / len(X_test):.4f} ({correct}/{len(X_test)})")

    # Save artifacts
    model_dir = os.path.dirname(__file__)
    model_path = os.path.join(model_dir, "environment_model.joblib")
    scaler_path = os.path.join(model_dir, "environment_scaler.joblib")

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    print(f"\nModels saved:")
    print(f"  {model_path}")
    print(f"  {scaler_path}")
    print("Training complete!")


def predict(pollutant_features: dict) -> dict:
    """Load model and predict AQI + main pollutant."""
    model_dir = os.path.dirname(__file__)
    model = joblib.load(os.path.join(model_dir, "environment_model.joblib"))
    scaler = joblib.load(os.path.join(model_dir, "environment_scaler.joblib"))

    row = {
        "pm25": pollutant_features.get("pm25", 50),
        "pm10": pollutant_features.get("pm10", 80),
        "o3": pollutant_features.get("o3", 60),
        "no2": pollutant_features.get("no2", 40),
        "so2": pollutant_features.get("so2", 20),
        "co": pollutant_features.get("co", 1.0),
        "temperature": pollutant_features.get("temperature", 20),
        "humidity": pollutant_features.get("humidity", 50),
    }

    X = np.array([[row[f] for f in ENV_FEATURES]])
    X_scaled = scaler.transform(X)

    predicted_aqi = float(model.predict(X_scaled)[0])
    predicted_aqi = round(max(0, predicted_aqi), 1)

    # Determine main pollutant from feature importances weighted by scaled values
    scaled_vals = X_scaled[0]
    contributions = {
        ENV_FEATURES[j]: model.feature_importances_[j] * abs(scaled_vals[j])
        for j in range(len(POLLUTANT_FEATURES))
    }
    # Only consider pollutant features (not temp/humidity)
    pollutant_contributions = {k: v for k, v in contributions.items() if k in POLLUTANT_FEATURES}
    main_pollutant = max(pollutant_contributions, key=pollutant_contributions.get)

    # Get AQI level and advice
    aqi_info = get_aqi_level(predicted_aqi)

    return {
        "predicted_aqi": predicted_aqi,
        "aqi_level": aqi_info["level"],
        "main_pollutant": main_pollutant,
        "health_advice": aqi_info["advice"],
    }


if __name__ == "__main__":
    train()

    # Test predictions
    print("\n" + "=" * 60)
    print("Test predictions:")
    print("=" * 60)
    test_cases = [
        {"pm25": 15, "pm10": 30, "o3": 50, "no2": 20, "so2": 10, "co": 0.5, "temperature": 22, "humidity": 45},
        {"pm25": 150, "pm10": 220, "o3": 180, "no2": 120, "so2": 60, "co": 5.0, "temperature": 30, "humidity": 60},
        {"pm25": 250, "pm10": 400, "o3": 200, "no2": 200, "so2": 100, "co": 10.0, "temperature": 28, "humidity": 55},
    ]
    for tc in test_cases:
        result = predict(tc)
        print(f"  PM2.5={tc['pm25']}, PM10={tc['pm10']}, O3={tc['o3']}")
        print(f"  → AQI={result['predicted_aqi']} ({result['aqi_level']}), Main: {result['main_pollutant']}")
