"""
Loan Default Prediction: XGBoost + LogisticRegression ensemble (VotingClassifier)
Generates: loan_model.joblib, loan_scaler.joblib, loan_features.joblib
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report, accuracy_score
from sklearn.calibration import CalibratedClassifierCV
import joblib
import os
import random
import warnings
warnings.filterwarnings("ignore")

random.seed(42)
np.random.seed(42)

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False


def generate_loan_data(n=2500):
    """Generate synthetic loan applicant data."""
    data = []

    for _ in range(n):
        income = random.uniform(3000, 100000)
        debt = random.uniform(0, income * 0.8)
        credit_score = random.randint(300, 850)
        loan_amount = random.uniform(10000, 500000)
        loan_term = random.choice([12, 24, 36, 48, 60])
        employment_years = random.randint(0, 40)
        historical_defaults = random.randint(0, 5)

        # Default probability formula
        # Higher DTI = more risk
        dti = debt / (income + 1)
        # Lower credit score = more risk
        credit_risk = max(0, (750 - credit_score) / 450)
        # Loan-to-income ratio
        lti = loan_amount / (income * loan_term/12 + 1)
        # Employment stability
        emp_factor = max(0, (5 - employment_years) / 10)
        # Historical defaults
        default_factor = min(historical_defaults * 0.15, 0.6)

        prob_default = 0.05 + 0.3 * dti + 0.35 * credit_risk + 0.15 * lti + 0.1 * emp_factor + 0.1 * default_factor
        prob_default = min(prob_default, 0.95)

        default = 1 if random.random() < prob_default else 0

        data.append({
            "income": income,
            "debt": debt,
            "credit_score": credit_score,
            "loan_amount": loan_amount,
            "loan_term": loan_term,
            "employment_years": employment_years,
            "historical_defaults": historical_defaults,
            "default": default,
        })

    df = pd.DataFrame(data)
    default_rate = df["default"].mean()
    print(f"Generated {len(df)} samples, default rate: {default_rate:.2%}")
    return df


def train():
    print("=" * 60)
    print("Training Loan Default Prediction Model")
    print("=" * 60)

    df = generate_loan_data(2500)

    feature_cols = ["income", "debt", "credit_score", "loan_amount", "loan_term", "employment_years", "historical_defaults"]
    X = df[feature_cols].values
    y = df["default"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)

    # Build ensemble
    estimators = []

    if HAS_XGB:
        xgb = XGBClassifier(n_estimators=150, max_depth=4, learning_rate=0.1, random_state=42, use_label_encoder=False, eval_metric="logloss")
        estimators.append(("xgb", xgb))

    lr = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
    estimators.append(("lr", lr))

    if len(estimators) > 1:
        model = VotingClassifier(estimators=estimators, voting="soft")
    else:
        model = estimators[0][1]

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    print(f"Accuracy: {acc:.4f}, AUC-ROC: {auc:.4f}")

    out_dir = os.path.dirname(__file__)
    joblib.dump(model, os.path.join(out_dir, "loan_model.joblib"))
    joblib.dump(scaler, os.path.join(out_dir, "loan_scaler.joblib"))
    joblib.dump(feature_cols, os.path.join(out_dir, "loan_features.joblib"))
    print(f"Models saved. AUC = {auc:.4f}")


def predict_loan(applicant: dict):
    """Predict loan default probability."""
    out_dir = os.path.dirname(__file__)
    model = joblib.load(os.path.join(out_dir, "loan_model.joblib"))
    scaler = joblib.load(os.path.join(out_dir, "loan_scaler.joblib"))
    feature_cols = joblib.load(os.path.join(out_dir, "loan_features.joblib"))

    X = np.array([[applicant.get(f, 0) for f in feature_cols]])
    X_scaled = scaler.transform(X)

    proba = model.predict_proba(X_scaled)[0][1] if hasattr(model, "predict_proba") else 0.5
    proba_pct = round(proba * 100, 2)

    if proba_pct >= 70:
        risk = "高风险"
    elif proba_pct >= 40:
        risk = "中风险"
    elif proba_pct >= 20:
        risk = "低风险"
    else:
        risk = "极低风险"

    # Simplified SHAP-like factor analysis (feature contributions)
    X_contrib = X[0]
    scaled_contrib = X_scaled[0]

    if hasattr(model, "estimators_" if hasattr(model, "named_estimators_") else ""):
        try:
            importances = np.mean([est.feature_importances_ if hasattr(est, "feature_importances_") else
                                   np.abs(est.coef_[0]) if hasattr(est, "coef_") else
                                   np.ones(len(feature_cols)) for name, est in model.named_estimators_.items()], axis=0)
        except Exception:
            importances = np.ones(len(feature_cols))
    elif hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        importances = np.ones(len(feature_cols))

    # Scale contributions by feature values (like SHAP)
    contributions = {feature_cols[i]: round(float(importances[i] * abs(scaled_contrib[i])), 4) for i in range(len(feature_cols))}
    top_factors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "default_probability": proba_pct,
        "risk_level": risk,
        "top_factors": [{"factor": f, "importance": v} for f, v in top_factors],
    }


if __name__ == "__main__":
    train()

    # Test
    test = {"income": 15000, "debt": 5000, "credit_score": 680, "loan_amount": 100000, "loan_term": 36, "employment_years": 3, "historical_defaults": 0}
    result = predict_loan(test)
    print(f"\nTest: {test}")
    print(f"  Default prob: {result['default_probability']}%")
    print(f"  Risk level: {result['risk_level']}")
    for f in result["top_factors"]:
        print(f"  {f['factor']}: {f['importance']}")
