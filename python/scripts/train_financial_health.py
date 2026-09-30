"""
Financial Health Diagnosis: RandomForestRegressor (multi-dimensional)
Generates: financial_health_model.joblib, health_dimension_weights.joblib
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
import joblib
import os
import random

random.seed(42)
np.random.seed(42)

SCORE_COLS = ["income_expense_ratio", "savings_rate", "investment_diversity", "debt_ratio", "financial_stability"]


def generate_profiles(n=2500):
    """Generate synthetic financial profiles."""
    data = []

    for _ in range(n):
        income = random.uniform(3000, 80000)
        expense = random.uniform(1000, income * 0.95)
        savings = income - expense
        savings_rate = savings / income if income > 0 else 0

        # Investment diversity score (0-100)
        n_investments = random.randint(0, 5)
        investment_diversity = min(n_investments * 20, 100)

        # Debt ratio (0-100)
        debt = random.uniform(0, income * 2)
        debt_ratio = min(debt / (income * 12 + 1) * 100, 100)

        # Income/expense ratio (0-100)
        income_expense_ratio = max(0, min(100, (income - expense) / income * 100))

        # Financial stability (0-100)
        employment = random.randint(0, 30)
        emergency_fund = random.uniform(0, income * 6)
        stability = min(100, employment * 2 + emergency_fund / income * 10)

        # Overall financial health score (0-100)
        overall = (
            income_expense_ratio * 0.25 +
            (min(savings_rate * 100, 100)) * 0.25 +
            investment_diversity * 0.15 +
            (100 - debt_ratio) * 0.2 +
            stability * 0.15 +
            np.random.normal(0, 3)
        )
        overall = max(0, min(100, overall))

        data.append({
            "monthly_income": income,
            "monthly_expense": expense,
            "total_savings": savings * random.randint(1, 24),
            "total_debt": debt,
            "n_investment_types": n_investments,
            "years_employed": employment,
            "emergency_fund_months": emergency_fund / (expense + 1),
            "income_expense_ratio": round(income_expense_ratio, 1),
            "savings_rate": round(savings_rate * 100, 1),
            "investment_diversity": investment_diversity,
            "debt_ratio": round(debt_ratio, 1),
            "financial_stability": round(stability, 1),
            "overall_health": round(overall, 1),
        })

    df = pd.DataFrame(data)
    print(f"Generated {len(df)} profiles, score range: {df['overall_health'].min():.1f}-{df['overall_health'].max():.1f}")
    return df


def train():
    print("=" * 60)
    print("Training Financial Health Diagnosis Model")
    print("=" * 60)

    df = generate_profiles(2500)

    # Train on raw financial features, predict 5 dimension scores and overall
    raw_features = ["monthly_income", "monthly_expense", "total_savings", "total_debt",
                    "n_investment_types", "years_employed", "emergency_fund_months"]
    X = df[raw_features].values
    y_dimensions = df[SCORE_COLS].values
    y_overall = df["overall_health"].values

    X_train, X_test, y_train_dims, y_test_dims, y_train_overall, y_test_overall = train_test_split(
        X, y_dimensions, y_overall, test_size=0.2, random_state=42
    )

    # Train multi-output model
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train_dims)

    # Also train overall model
    overall_model = RandomForestRegressor(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    overall_model.fit(X_train, y_train_overall)

    # Evaluate
    y_pred_dims = model.predict(X_test)
    y_pred_overall = overall_model.predict(X_test)

    r2_multi = r2_score(y_test_dims, y_pred_dims, multioutput="uniform_average")
    r2_overall = r2_score(y_test_overall, y_pred_overall)

    print(f"Dimension model R2 = {r2_multi:.4f}")
    print(f"Overall model R2 = {r2_overall:.4f}")
    print(f"Overall MAE = {mean_absolute_error(y_test_overall, y_pred_overall):.2f}")

    out_dir = os.path.dirname(__file__)
    joblib.dump({"dimension_model": model, "overall_model": overall_model, "raw_features": raw_features},
                os.path.join(out_dir, "financial_health_model.joblib"))
    joblib.dump({"score_cols": SCORE_COLS}, os.path.join(out_dir, "health_dimension_weights.joblib"))
    print("Models saved.")


def diagnose(financial_profile: dict):
    """Diagnose financial health from financial profile."""
    out_dir = os.path.dirname(__file__)
    data = joblib.load(os.path.join(out_dir, "financial_health_model.joblib"))
    model = data["dimension_model"]
    overall_model = data["overall_model"]
    raw_features = data["raw_features"]

    X = np.array([[float(financial_profile.get(f, 0)) for f in raw_features]])
    dim_scores = model.predict(X)[0]
    overall = overall_model.predict(X)[0]

    overall = max(0, min(100, overall))
    dim_scores = np.clip(dim_scores, 0, 100)

    # Percentile (rough)
    percentile = min(99, max(1, int(overall)))

    # Improvement suggestions
    suggestions = []
    dim_result = {}
    for i, col in enumerate(SCORE_COLS):
        score = round(float(dim_scores[i]), 1)
        dim_result[col] = score
        if col == "income_expense_ratio" and score < 30:
            suggestions.append("建议减少非必要支出，提高收入支出比")
        elif col == "savings_rate" and score < 20:
            suggestions.append("建议每月至少存下收入的20%以建立应急基金")
        elif col == "investment_diversity" and score < 40:
            suggestions.append("考虑分散投资，增加股票、基金、债券等不同资产类型")
        elif col == "debt_ratio" and score > 50:
            suggestions.append("建议制定还债计划，优先偿还高利率债务")
        elif col == "financial_stability" and score < 40:
            suggestions.append("建议增加应急基金至3-6个月的生活支出")

    if not suggestions:
        suggestions.append("财务状况良好！建议继续保持并定期审视资产配置。")

    return {
        "overall_score": round(float(overall), 1),
        "percentile": percentile,
        "dimension_scores": dim_result,
        "improvement_suggestions": suggestions,
    }


if __name__ == "__main__":
    train()

    # Test
    profile = {"monthly_income": 15000, "monthly_expense": 10000, "total_savings": 50000,
               "total_debt": 100000, "n_investment_types": 2, "years_employed": 5, "emergency_fund_months": 3}
    result = diagnose(profile)
    print(f"\nFinancial diagnosis:")
    print(f"  Overall: {result['overall_score']}/100 (p{result['percentile']})")
    for dim, score in result["dimension_scores"].items():
        print(f"  {dim}: {score}")
    for s in result["improvement_suggestions"]:
        print(f"  → {s}")

