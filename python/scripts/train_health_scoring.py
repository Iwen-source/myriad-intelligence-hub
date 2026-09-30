"""
Health Scoring Model: GradientBoostingRegressor
Generates: health_scoring_model.joblib, health_scaler.joblib
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
import joblib
import os
import random

random.seed(42)
np.random.seed(42)


def generate_patients(n=1200):
    """Generate synthetic patient data with realistic health scores."""
    data = []
    for i in range(n):
        age = random.randint(5, 90)
        visit_frequency = random.randint(0, 24)  # visits per year
        past_illness_count = random.randint(0, 15)
        symptom_severity = random.uniform(0, 10)  # 0=mild, 10=severe
        diagnosis_diversity = random.randint(1, 8)  # number of unique diagnoses

        # Health score formula (0-100, higher = healthier)
        # Base: 80
        base = 80

        # Age penalty: <10 or >65 reduce score
        if age < 10:
            age_penalty = (10 - age) * 1.5
        elif age > 65:
            age_penalty = (age - 65) * 0.5
        else:
            age_penalty = 0

        # Visit frequency penalty: too few or too many visits indicate issues
        visit_score = -(abs(visit_frequency - 2) * 1.5) if visit_frequency > 0 else -10

        # Illness count penalty
        illness_penalty = min(past_illness_count * 2, 30)

        # Symptom severity penalty (exponential)
        severity_penalty = symptom_severity ** 1.5 * 0.8

        # Diagnosis diversity penalty
        diversity_penalty = min((diagnosis_diversity - 1) * 3, 20) if diagnosis_diversity > 1 else 0

        # Random noise
        noise = np.random.normal(0, 3)

        health_score = base - age_penalty + visit_score - illness_penalty - severity_penalty - diversity_penalty + noise
        health_score = max(0, min(100, health_score))

        data.append({
            "age": age,
            "visit_frequency": visit_frequency,
            "past_illness_count": past_illness_count,
            "symptom_severity": symptom_severity,
            "diagnosis_diversity": diagnosis_diversity,
            "health_score": round(health_score, 1),
        })

    df = pd.DataFrame(data)
    print(f"Generated {len(df)} patients, score range: {df['health_score'].min():.1f}-{df['health_score'].max():.1f}")
    return df


def train():
    print("=" * 60)
    print("Training Health Scoring Model (GradientBoostingRegressor)")
    print("=" * 60)

    df = generate_patients(1200)

    feature_cols = ["age", "visit_frequency", "past_illness_count", "symptom_severity", "diagnosis_diversity"]
    X = df[feature_cols].values
    y = df["health_score"].values

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        min_samples_split=5,
        min_samples_leaf=3,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"R2 = {r2:.4f}, MAE = {mae:.2f}")
    print(f"Feature importances: {dict(zip(feature_cols, model.feature_importances_))}")

    out_dir = os.path.dirname(__file__)
    joblib.dump(model, os.path.join(out_dir, "health_scoring_model.joblib"))
    joblib.dump(scaler, os.path.join(out_dir, "health_scaler.joblib"))
    print("Models saved.")


def predict_health(patient_features: dict):
    """Predict health score from patient features."""
    out_dir = os.path.dirname(__file__)
    model = joblib.load(os.path.join(out_dir, "health_scoring_model.joblib"))
    scaler = joblib.load(os.path.join(out_dir, "health_scaler.joblib"))

    feature_cols = ["age", "visit_frequency", "past_illness_count", "symptom_severity", "diagnosis_diversity"]
    X = np.array([[patient_features.get(f, 0) for f in feature_cols]])
    X_scaled = scaler.transform(X)

    score = float(model.predict(X_scaled)[0])
    score = max(0, min(100, score))

    # Risk level
    if score >= 80:
        risk = "低风险"
    elif score >= 60:
        risk = "中风险"
    elif score >= 40:
        risk = "高风险"
    else:
        risk = "极高风险"

    # Dimension breakdown (approximate contributions)
    base_score = 80
    dim_scores = {}
    for i, f in enumerate(feature_cols):
        val = patient_features.get(f, 0)
        if f == "age":
            if val < 10:
                penalty = (10 - val) * 1.5
            elif val > 65:
                penalty = (val - 65) * 0.5
            else:
                penalty = 0
        elif f == "visit_frequency":
            penalty = -(abs(val - 2) * 1.5) if val > 0 else -10
        elif f == "past_illness_count":
            penalty = min(val * 2, 30)
        elif f == "symptom_severity":
            penalty = val ** 1.5 * 0.8
        else:
            penalty = min((val - 1) * 3, 20) if val > 1 else 0
        dim_scores[f] = max(0, min(100, base_score - penalty))

    return {
        "overall_score": round(score, 1),
        "risk_level": risk,
        "dimension_breakdown": dim_scores,
        "trend_slope": "stable",
    }


if __name__ == "__main__":
    train()

    # Test
    test_patient = {"age": 45, "visit_frequency": 4, "past_illness_count": 2, "symptom_severity": 3.5, "diagnosis_diversity": 2}
    result = predict_health(test_patient)
    print(f"\nTest patient: {test_patient}")
    print(f"  Score: {result['overall_score']}, Risk: {result['risk_level']}")
    print(f"  Dimensions: {result['dimension_breakdown']}")

