"""
Resource Scheduling: RandomForestRegressor for hospital visit prediction
Generates: resource_model.joblib, resource_scaler.joblib, department_list.joblib
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
import joblib
import os
import random

random.seed(42)
np.random.seed(42)

DEPARTMENTS = [
    "内科", "外科", "儿科", "妇产科", "眼科",
    "耳鼻喉科", "皮肤科", "骨科", "神经内科", "口腔科"
]


def generate_schedule_data(n=1200):
    """Generate synthetic hospital visit data."""
    data = []

    for _ in range(n):
        season = random.randint(1, 4)  # 1=spring, 2=summer, 3=fall, 4=winter
        temperature = random.uniform(-10, 40)
        humidity = random.uniform(20, 90)
        booked_count = random.randint(5, 60)
        historical_same_day = random.randint(10, 80)
        day_of_week = random.randint(1, 7)  # 1=Mon, 7=Sun
        is_holiday = 1 if day_of_week >= 6 or random.random() < 0.05 else 0
        department = random.choice(DEPARTMENTS)

        # Visit count formula
        base = 40

        # Seasonal effect
        if season == 2:  # Summer: more external injuries
            season_bonus = 10 if department in ["外科", "骨科", "皮肤科"] else -3
        elif season == 1:  # Spring: more allergies
            season_bonus = 8 if department in ["耳鼻喉科", "皮肤科", "内科"] else -2
        elif season == 4:  # Winter: more colds
            season_bonus = 15 if department in ["内科", "儿科"] else -5
        else:
            season_bonus = 0

        # Temperature effect
        temp_effect = -abs(temperature - 22) * 0.5

        # Day of week: weekends have fewer visits
        dow_effect = 15 if day_of_week <= 5 else -10

        # Holiday effect
        holiday_effect = -15 if is_holiday else 0

        # Department popularity
        dept_base = {"内科": 50, "儿科": 45, "外科": 35, "妇产科": 30, "骨科": 25,
                     "眼科": 20, "耳鼻喉科": 20, "皮肤科": 18, "神经内科": 15, "口腔科": 12}

        # Historical same day correlation
        hist_effect = historical_same_day * 0.15

        noise = np.random.normal(0, 5)

        visits = base + season_bonus + temp_effect + dow_effect + holiday_effect + dept_base.get(department, 20) + hist_effect * 0.3 + noise
        visits = max(5, visits)

        data.append({
            "season": season,
            "temperature": temperature,
            "humidity": humidity,
            "booked_count": booked_count,
            "historical_same_day": historical_same_day,
            "day_of_week": day_of_week,
            "is_holiday": is_holiday,
            "department": department,
            "visit_count": round(visits),
        })

    df = pd.DataFrame(data)
    print(f"Generated {len(df)} samples for {len(DEPARTMENTS)} departments")
    return df


def train():
    print("=" * 60)
    print("Training Resource Scheduling Model")
    print("=" * 60)

    df = generate_schedule_data(1200)

    # One-hot encode department
    dept_dummies = pd.get_dummies(df["department"], prefix="dept")
    feature_df = pd.concat([
        df[["season", "temperature", "humidity", "booked_count", "historical_same_day", "day_of_week", "is_holiday"]],
        dept_dummies
    ], axis=1)

    feature_cols = feature_df.columns.tolist()
    X = feature_df.values
    y = df["visit_count"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"R2 = {r2:.4f}, MAE = {mae:.2f}")

    out_dir = os.path.dirname(__file__)
    joblib.dump(model, os.path.join(out_dir, "resource_model.joblib"))
    joblib.dump(scaler, os.path.join(out_dir, "resource_scaler.joblib"))
    joblib.dump({"departments": DEPARTMENTS, "feature_cols": feature_cols, "dept_prefix": [c for c in feature_cols if c.startswith("dept_")]},
                os.path.join(out_dir, "resource_metadata.joblib"))
    print("Models saved.")


def predict_resources(features: dict, department: str):
    """Predict visit count for a department on a given date."""
    out_dir = os.path.dirname(__file__)
    model = joblib.load(os.path.join(out_dir, "resource_model.joblib"))
    scaler = joblib.load(os.path.join(out_dir, "resource_scaler.joblib"))
    meta = joblib.load(os.path.join(out_dir, "resource_metadata.joblib"))

    # Build feature vector
    base_features = ["season", "temperature", "humidity", "booked_count", "historical_same_day", "day_of_week", "is_holiday"]
    row = [features.get(f, 0) for f in base_features]

    # Department one-hot
    dept_prefixes = meta["dept_prefix"]
    for dept_p in sorted(set(DEPARTMENTS)):
        row.append(1 if f"dept_{department}" == f"dept_{dept_p}" else 0)

    # Ensure correct feature count
    expected = len(meta["feature_cols"])
    if len(row) > expected:
        row = row[:expected]
    elif len(row) < expected:
        row.extend([0] * (expected - len(row)))

    X = np.array([row])
    X_scaled = scaler.transform(X)

    pred = float(model.predict(X_scaled)[0])
    pred = max(0, round(pred))

    # Suggested doctors (based on predicted visits)
    suggested_doctors = max(1, round(pred / 15))

    # Peak hours based on day type
    is_weekend = features.get("day_of_week", 1) >= 6 or features.get("is_holiday", 0) == 1
    if is_weekend:
        peak_hours = ["09:00-11:00"]
    else:
        peak_hours = ["08:00-10:00", "14:00-16:00"]

    return {
        "predicted_visits": pred,
        "suggested_doctors": suggested_doctors,
        "peak_hours": peak_hours,
    }


if __name__ == "__main__":
    train()

    # Test
    test_features = {"season": 4, "temperature": 5, "humidity": 60, "booked_count": 30,
                     "historical_same_day": 45, "day_of_week": 2, "is_holiday": 0}
    result = predict_resources(test_features, "内科")
    print(f"\nTest: {test_features}")
    print(f"  Visits: {result['predicted_visits']}, Doctors: {result['suggested_doctors']}, Peak: {result['peak_hours']}")

