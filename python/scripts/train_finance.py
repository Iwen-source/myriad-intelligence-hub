"""
Finance Model: Transaction Risk Scoring + Anomaly Detection
- RandomForestRegressor for risk score (0-100)
- IsolationForest for anomaly detection
Generates: finance_model.joblib, anomaly_model.joblib
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
import joblib
import os
import random

random.seed(42)
np.random.seed(42)

# ── Feature definitions ────────────────────────────────────────────────
FEATURES = [
    "amount",           # Transaction amount (Y)
    "hour_of_day",      # 0-23
    "day_of_week",      # 0=Monday, 6=Sunday
    "transaction_count_24h",  # Number of transactions in last 24h
    "avg_amount_7d",    # Average transaction amount over last 7 days
    "is_weekend",       # 0 or 1
    "user_age",         # Account age in days
    "is_night",         # 23:00-05:00 = 1, else 0
    "amount_ratio",     # amount / avg_amount_7d (how unusual is this amount)
]


def generate_transaction_dataset(n_samples=1200):
    """Generate synthetic transaction data with realistic risk patterns."""
    rows = []
    for _ in range(n_samples):
        # Normal transaction patterns (80%)
        if random.random() < 0.8:
            amount = round(random.gauss(200, 100), 2)
            amount = max(1, amount)
            hour = int(random.gauss(14, 4))
            hour = max(0, min(23, hour))
            day = random.randint(0, 6)
            tx_24h = max(0, int(random.gauss(3, 2)))
            avg_7d = round(random.gauss(180, 80), 2)
            avg_7d = max(10, avg_7d)
            user_age = int(random.gauss(365, 200))
            user_age = max(1, user_age)
        # Suspicious transactions (20%)
        else:
            amount = round(random.gauss(5000, 3000), 2)
            hour = random.choice([2, 3, 4, 22, 23, 0, 1])
            day = random.randint(0, 6)
            tx_24h = max(0, int(random.gauss(8, 4)))
            avg_7d = round(random.gauss(200, 150), 2)
            avg_7d = max(10, avg_7d)
            user_age = int(random.gauss(30, 20))
            user_age = max(1, user_age)

        is_weekend = 1 if day >= 5 else 0
        is_night = 1 if hour < 6 or hour >= 23 else 0
        amount_ratio = round(amount / avg_7d, 2) if avg_7d > 0 else 1.0

        rows.append(
            {
                "amount": amount,
                "hour_of_day": hour,
                "day_of_week": day,
                "transaction_count_24h": tx_24h,
                "avg_amount_7d": avg_7d,
                "is_weekend": is_weekend,
                "user_age": user_age,
                "is_night": is_night,
                "amount_ratio": amount_ratio,
            }
        )

    df = pd.DataFrame(rows)
    # Add NaN protection
    df = df.fillna(0)
    return df


def compute_risk_score(row):
    """Compute realistic risk score based on transaction features (rule-based ground truth)."""
    score = 0.0

    # High amount
    if row["amount"] > 3000:
        score += 25
    elif row["amount"] > 1000:
        score += 15
    elif row["amount"] > 500:
        score += 5

    # Night transaction
    if row["is_night"]:
        score += 15

    # High amount ratio (much larger than usual)
    if row["amount_ratio"] > 10:
        score += 20
    elif row["amount_ratio"] > 5:
        score += 10
    elif row["amount_ratio"] > 3:
        score += 5

    # Many transactions in 24h
    if row["transaction_count_24h"] > 10:
        score += 15
    elif row["transaction_count_24h"] > 6:
        score += 8

    # New account
    if row["user_age"] < 7:
        score += 15
    elif row["user_age"] < 30:
        score += 8
    elif row["user_age"] < 90:
        score += 3

    # Weekend + night combo
    if row["is_weekend"] and row["is_night"]:
        score += 10

    # Add some noise
    score += random.gauss(0, 5)
    score = max(0, min(100, score))
    return round(score, 2)


def train():
    print("=" * 60)
    print("Training Finance Model (Risk Scoring + Anomaly Detection)")
    print("=" * 60)

    # Generate dataset
    df = generate_transaction_dataset(1200)

    # Compute ground truth risk scores
    df["risk_score"] = df.apply(compute_risk_score, axis=1)

    X = df[FEATURES].values
    y = df["risk_score"].values

    print(f"Dataset: {len(df)} samples, {len(FEATURES)} features")
    print(f"Risk score range: {y.min():.1f} - {y.max():.1f}")
    print(f"Risk score mean: {y.mean():.1f}, std: {y.std():.1f}")

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ── Model 1: RandomForestRegressor for risk scoring ──
    print("\n--- Risk Scoring Model (RandomForestRegressor) ---")
    risk_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    risk_model.fit(X_train_scaled, y_train)

    y_pred = risk_model.predict(X_test_scaled)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    print(f"RMSE: {rmse:.4f}")
    print(f"MAE:  {mae:.4f}")
    print(f"R2:   {r2:.4f}")

    # ── Model 2: IsolationForest for anomaly detection ──
    print("\n--- Anomaly Detection Model (IsolationForest) ---")

    # Anomalies are defined as risk_score > 50 or very unusual patterns
    contamination = 0.08  # Expect ~8% anomalies
    anomaly_model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    anomaly_model.fit(X_train_scaled)

    # Evaluate anomaly detection
    train_preds = anomaly_model.predict(X_train_scaled)
    test_preds = anomaly_model.predict(X_test_scaled)

    # Create ground truth: score > 50 is "anomaly"
    y_anomaly_true = (y_test > 50).astype(int)
    y_anomaly_pred = (test_preds == -1).astype(int)

    anomaly_accuracy = (y_anomaly_true == y_anomaly_pred).mean()
    print(f"Anomaly detection (score>50): {anomaly_accuracy:.4f} accuracy")
    print(f"Anomalies in test set: {y_anomaly_true.sum()} / {len(y_anomaly_true)}")

    # Save artifacts
    model_dir = os.path.dirname(__file__)
    risk_path = os.path.join(model_dir, "finance_model.joblib")
    anomaly_path = os.path.join(model_dir, "finance_anomaly_model.joblib")
    scaler_path = os.path.join(model_dir, "finance_scaler.joblib")

    joblib.dump(risk_model, risk_path)
    joblib.dump(anomaly_model, anomaly_path)
    joblib.dump(scaler, scaler_path)

    print(f"\nModels saved:")
    print(f"  {risk_path}")
    print(f"  {anomaly_path}")
    print(f"  {scaler_path}")
    print("Training complete!")


def predict(transaction_features: dict) -> dict:
    """Load models and predict risk score + anomaly flag."""
    model_dir = os.path.dirname(__file__)
    risk_model = joblib.load(os.path.join(model_dir, "finance_model.joblib"))
    anomaly_model = joblib.load(os.path.join(model_dir, "finance_anomaly_model.joblib"))
    scaler = joblib.load(os.path.join(model_dir, "finance_scaler.joblib"))

    # Build feature vector
    row = {
        "amount": transaction_features.get("amount", 100),
        "hour_of_day": transaction_features.get("hour_of_day", 12),
        "day_of_week": transaction_features.get("day_of_week", 1),
        "transaction_count_24h": transaction_features.get("transaction_count_24h", 1),
        "avg_amount_7d": transaction_features.get("avg_amount_7d", 200),
        "is_weekend": transaction_features.get("is_weekend", 0),
        "user_age": transaction_features.get("user_age", 365),
        "is_night": transaction_features.get("is_night", 0),
        "amount_ratio": transaction_features.get("amount_ratio", 1.0),
    }

    X = np.array([[row[f] for f in FEATURES]])
    X_scaled = scaler.transform(X)

    risk_score = float(risk_model.predict(X_scaled)[0])
    is_anomaly = bool(anomaly_model.predict(X_scaled)[0] == -1)

    # Risk level
    if risk_score >= 70:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "is_anomaly": is_anomaly,
    }


if __name__ == "__main__":
    train()

    # Test predictions
    print("\n" + "=" * 60)
    print("Test predictions:")
    print("=" * 60)
    test_cases = [
        {"amount": 50, "hour_of_day": 14, "day_of_week": 2, "transaction_count_24h": 1, "avg_amount_7d": 180, "is_weekend": 0, "user_age": 500, "is_night": 0, "amount_ratio": 0.3},
        {"amount": 8000, "hour_of_day": 3, "day_of_week": 6, "transaction_count_24h": 12, "avg_amount_7d": 200, "is_weekend": 1, "user_age": 5, "is_night": 1, "amount_ratio": 40.0},
        {"amount": 1500, "hour_of_day": 22, "day_of_week": 5, "transaction_count_24h": 5, "avg_amount_7d": 300, "is_weekend": 1, "user_age": 60, "is_night": 0, "amount_ratio": 5.0},
    ]
    for tc in test_cases:
        result = predict(tc)
        print(f"  Amount=Y{tc['amount']}, Hour={tc['hour_of_day']:02d}:00")
        print(f"  → Risk: {result['risk_score']}/100 ({result['risk_level']}), Anomaly: {result['is_anomaly']}")
