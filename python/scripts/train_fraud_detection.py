"""
Advanced Fraud Detection: Ensemble (IsolationForest + LOF + OneClassSVM)
Generates: fraud_ensemble.joblib, fraud_scaler.joblib
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import recall_score, precision_score, f1_score
import joblib
import os
import random

random.seed(42)
np.random.seed(42)

FEATURE_COLS = ["amount", "distance_from_last", "time_gap", "amount_deviation",
                "device_score", "is_night", "is_international"]


def generate_transactions(n=2500):
    """Generate synthetic transaction data with known fraud labels."""
    data = []

    for _ in range(n):
        is_fraud = 1 if random.random() < 0.08 else 0  # 8% fraud rate

        if is_fraud:
            # Fraud patterns
            amount = random.uniform(5000, 50000)
            distance_from_last = random.uniform(100, 5000)
            time_gap = random.uniform(0.5, 24)
            amount_deviation = random.uniform(3, 10)
            device_score = random.uniform(0, 0.3)  # Low = suspicious
            is_night = 1 if random.random() < 0.6 else 0
            is_international = 1 if random.random() < 0.5 else 0
        else:
            # Normal patterns
            amount = max(1, np.random.pareto(2) * 100)
            distance_from_last = max(1, random.expovariate(0.02))
            time_gap = random.expovariate(1 / 48)
            amount_deviation = random.expovariate(2)
            device_score = random.uniform(0.7, 1.0)
            is_night = 1 if random.random() < 0.2 else 0
            is_international = 1 if random.random() < 0.02 else 0

        data.append({
            "amount": amount,
            "distance_from_last": distance_from_last,
            "time_gap": time_gap,
            "amount_deviation": amount_deviation,
            "device_score": device_score,
            "is_night": is_night,
            "is_international": is_international,
            "is_fraud": is_fraud,
        })

    df = pd.DataFrame(data)
    print(f"Generated {len(df)} transactions, {df['is_fraud'].sum()} fraud cases ({df['is_fraud'].mean():.2%})")
    return df


def train():
    print("=" * 60)
    print("Training Advanced Fraud Detection Ensemble")
    print("=" * 60)

    df = generate_transactions(2500)

    X = df[FEATURE_COLS].values
    y = df["is_fraud"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train each model on unlabeled data (anomaly detection)
    # IsolationForest
    iso = IsolationForest(contamination=0.08, random_state=42, n_estimators=200)
    iso_pred = iso.fit_predict(X_scaled)
    # Convert: -1=anomaly(fraud), 1=normal → 1=fraud, 0=normal
    iso_pred_binary = (iso_pred == -1).astype(int)
    iso_recall = recall_score(y, iso_pred_binary)
    print(f"IsolationForest recall: {iso_recall:.4f}")

    # LOF
    lof = LocalOutlierFactor(contamination=0.08, novelty=False, n_neighbors=20)
    lof_pred = lof.fit_predict(X_scaled)
    lof_pred_binary = (lof_pred == -1).astype(int)
    lof_recall = recall_score(y, lof_pred_binary)
    print(f"LOF recall: {lof_recall:.4f}")

    # OneClassSVM (trained on a clean subset for novelty detection)
    clean_data = X_scaled[y == 0]
    if len(clean_data) > 500:
        clean_data = clean_data[:500]
    ocsvm = OneClassSVM(nu=0.05, kernel="rbf", gamma="auto")
    ocsvm.fit(clean_data)
    ocsvm_pred = ocsvm.predict(X_scaled)
    ocsvm_pred_binary = (ocsvm_pred == -1).astype(int)
    ocsvm_recall = recall_score(y, ocsvm_pred_binary)
    print(f"OneClassSVM recall: {ocsvm_recall:.4f}")

    # Ensemble: soft voting (average anomaly scores)
    iso_scores = iso.score_samples(X_scaled)
    # Convert to 0-1 fraud score
    iso_scores = 1 - (iso_scores - iso_scores.min()) / (iso_scores.max() - iso_scores.min())

    lof_scores = lof.negative_outlier_factor_
    lof_scores = 1 - (lof_scores - lof_scores.min()) / (lof_scores.max() - lof_scores.min())

    ocsvm_scores = ocsvm.decision_function(X_scaled)
    ocsvm_scores = 1 - (ocsvm_scores - ocsvm_scores.min()) / (ocsvm_scores.max() - ocsvm_scores.min())

    ensemble_scores = (iso_scores + lof_scores + ocsvm_scores) / 3

    # Find threshold for recall > 0.85
    thresholds = np.linspace(0.1, 0.9, 50)
    best_f1 = 0
    best_thresh = 0.3
    for t in thresholds:
        pred = (ensemble_scores > t).astype(int)
        r = recall_score(y, pred)
        p = precision_score(y, pred)
        f1 = f1_score(y, pred)
        if r >= 0.85 and f1 > best_f1:
            best_f1 = f1
            best_thresh = t

    pred_at_best = (ensemble_scores > best_thresh).astype(int)
    print(f"\nEnsemble (best threshold={best_thresh:.2f}):")
    print(f"  Recall: {recall_score(y, pred_at_best):.4f}")
    print(f"  Precision: {precision_score(y, pred_at_best):.4f}")
    print(f"  F1: {f1_score(y, pred_at_best):.4f}")

    out_dir = os.path.dirname(__file__)
    joblib.dump({
        "isolation_forest": iso,
        "lof": lof,
        "one_class_svm": ocsvm,
        "threshold": best_thresh,
        "feature_cols": FEATURE_COLS,
    }, os.path.join(out_dir, "fraud_ensemble.joblib"))
    joblib.dump(scaler, os.path.join(out_dir, "fraud_scaler.joblib"))
    print("Models saved.")


def detect_fraud(transaction: dict):
    """Detect fraud probability for a transaction."""
    out_dir = os.path.dirname(__file__)
    ensemble = joblib.load(os.path.join(out_dir, "fraud_ensemble.joblib"))
    scaler = joblib.load(os.path.join(out_dir, "fraud_scaler.joblib"))

    iso = ensemble["isolation_forest"]
    lof = ensemble["lof"]
    ocsvm = ensemble["one_class_svm"]
    threshold = ensemble["threshold"]
    feature_cols = ensemble["feature_cols"]

    X = np.array([[float(transaction.get(f, 0)) for f in feature_cols]])
    X_scaled = scaler.transform(X)

    # Get scores from each model
    iso_score = iso.score_samples(X_scaled)[0]
    iso_norm = 1 - (iso_score + 0.5)  # Normalize roughly

    try:
        lof_score = lof.negative_outlier_factor_[0] if len(lof.negative_outlier_factor_.shape) > 0 else -1
        lof_norm = 1 - (lof_score + 1) / 2
    except Exception:
        lof_norm = 0.5

    ocsvm_score = ocsvm.decision_function(X_scaled)[0]
    ocsvm_norm = 1 - (ocsvm_score + 1) / 2

    # Ensemble
    fraud_prob = max(0, min(1, (iso_norm + lof_norm + ocsvm_norm) / 3))
    is_fraud = fraud_prob > threshold

    # Identify which features contributed most
    X_vals = X[0]
    feature_contributions = {}
    for i, f in enumerate(feature_cols):
        z_score = abs(X_scaled[0][i])
        feature_contributions[f] = round(float(z_score), 2)

    anomaly_features = sorted(feature_contributions.items(), key=lambda x: x[1], reverse=True)
    top_anomalies = [f for f, s in anomaly_features[:3] if s > 1.5]

    # Alert level
    if fraud_prob > 0.8:
        alert = "高风险"
        action = "立即拦截并通知安全团队"
    elif fraud_prob > 0.5:
        alert = "中风险"
        action = "加强验证并人工审核"
    elif fraud_prob > 0.3:
        alert = "低风险"
        action = "常规风控检查"
    else:
        alert = "安全"
        action = "正常放行"

    return {
        "fraud_probability": round(fraud_prob * 100, 2),
        "is_fraudulent": bool(is_fraud),
        "anomaly_features": top_anomalies,
        "alert_level": alert,
        "action_suggestion": action,
    }


if __name__ == "__main__":
    train()

    # Test
    normal_tx = {"amount": 150, "distance_from_last": 5, "time_gap": 48, "amount_deviation": 0.5,
                 "device_score": 0.95, "is_night": 0, "is_international": 0}
    fraud_tx = {"amount": 25000, "distance_from_last": 2000, "time_gap": 2, "amount_deviation": 8,
                "device_score": 0.1, "is_night": 1, "is_international": 1}

    print("\nNormal transaction:")
    r = detect_fraud(normal_tx)
    print(f"  Fraud prob: {r['fraud_probability']}%, Alert: {r['alert_level']}, Action: {r['action_suggestion']}")

    print("\nSuspicious transaction:")
    r = detect_fraud(fraud_tx)
    print(f"  Fraud prob: {r['fraud_probability']}%, Alert: {r['alert_level']}, Action: {r['action_suggestion']}")
    print(f"  Anomaly features: {r['anomaly_features']}")
