"""
Epidemiological Forecasting Model: ARIMA (statsmodels)
Generates: epidemic_models.joblib (dict of ARIMA results per disease)
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os
import random
import warnings
warnings.filterwarnings("ignore")

random.seed(42)
np.random.seed(42)

DISEASES = [
    "流行性感冒", "新型冠状病毒感染", "手足口病", "登革热", "水痘"
]


def generate_time_series(days=400):
    """Generate synthetic epidemic time series with seasonal patterns."""
    data = {}
    t = np.arange(days)

    for disease in DISEASES:
        # Base daily count with seasonal oscillation
        base = random.uniform(30, 100)
        # Annual seasonality (patients with yearly pattern)
        season_amplitude = random.uniform(10, 30)
        seasonal = season_amplitude * np.sin(2 * np.pi * t / 365 + random.uniform(0, 2 * np.pi))

        # Weekly pattern (weekend effect)
        weekly = random.uniform(5, 15) * np.sin(2 * np.pi * t / 7)

        # Trend (slight upward/downward)
        trend_slope = random.uniform(-0.02, 0.05)
        trend = trend_slope * t

        # Random noise
        noise = np.random.normal(0, base * 0.1, days)

        # Outbreaks (sudden spikes)
        outbreak_positions = np.random.choice(days, size=random.randint(2, 5), replace=False)
        outbreak_mask = np.zeros(days)
        for pos in outbreak_positions:
            # Gaussian spike
            for j in range(max(0, pos - 7), min(days, pos + 8)):
                outbreak_mask[j] += 50 * np.exp(-0.3 * (j - pos) ** 2)

        values = base + seasonal + weekly + trend + noise + outbreak_mask
        values = np.maximum(values, 0)  # No negative counts

        data[disease] = values.astype(int)

    df = pd.DataFrame(data)
    print(f"Generated {days} days of data for {len(DISEASES)} diseases")
    return df


def train():
    print("=" * 60)
    print("Training Epidemiological Forecasting Model (ARIMA)")
    print("=" * 60)

    df = generate_time_series(400)

    # Split: train on first 365, test on last 35
    train_df = df.iloc[:365]
    test_df = df.iloc[365:]

    models = {}
    metrics = {}

    for disease in DISEASES:
        print(f"\nTraining ARIMA for: {disease}")
        series = train_df[disease].values.astype(float)

        # Try different orders and pick best AIC
        best_aic = float("inf")
        best_result = None
        best_order = None

        # Try a few ARIMA orders
        orders_to_try = [(1, 1, 1), (2, 1, 2), (3, 1, 2), (2, 1, 1), (1, 1, 2)]
        for order in orders_to_try:
            try:
                model = ARIMA(series, order=order)
                fitted = model.fit()
                if fitted.aic < best_aic:
                    best_aic = fitted.aic
                    best_result = fitted
                    best_order = order
            except Exception:
                continue

        if best_result is None:
            # Fallback to simplest order
            model = ARIMA(series, order=(1, 1, 1))
            best_result = model.fit()
            best_order = (1, 1, 1)

        print(f"  Best ARIMA order: {best_order}, AIC: {best_aic:.2f}")

        # Evaluate on test set (30 days holdout)
        n_test = 30
        test_actual = test_df[disease].values[:n_test]
        # Use dynamic forecasting
        fc = best_result.forecast(steps=n_test)
        if len(fc) < len(test_actual):
            n_test = len(fc)
            test_actual = test_actual[:n_test]

        mae = mean_absolute_error(test_actual[:len(fc)], fc)
        rmse = np.sqrt(mean_squared_error(test_actual[:len(fc)], fc))
        print(f"  Test MAE: {mae:.2f}, RMSE: {rmse:.2f}")

        # Store model parameters (not the full ARIMA results object for space)
        models[disease] = {
            "params": best_result.params.tolist(),
            "order": best_order,
            "aic": best_aic,
            "residuals_std": best_result.resid.std(),
            "last_values": series[-30:].tolist(),  # Keep last 30 values for future forecasts
        }
        metrics[disease] = {"mae": float(mae), "rmse": float(rmse)}

    # Bundle everything
    model_data = {
        "models": models,
        "metrics": metrics,
        "disease_order": DISEASES,
    }

    out_dir = os.path.dirname(__file__)
    joblib.dump(model_data, os.path.join(out_dir, "epidemic_models.joblib"))
    print(f"\nModels saved. Metrics: {metrics}")


def predict_forecast(disease_name=None, forecast_days=14):
    """Load model and forecast."""
    out_dir = os.path.dirname(__file__)
    model_data = joblib.load(os.path.join(out_dir, "epidemic_models.joblib"))
    models = model_data["models"]

    diseases = [disease_name] if disease_name else model_data["disease_order"]
    results = {}

    for disease in diseases:
        if disease not in models:
            continue

        m = models[disease]

        # Refit ARIMA with stored params and last values
        series = np.array(m["last_values"])
        try:
            model = ARIMA(series, order=tuple(m["order"]))
            fitted = model.fit()
            fc = fitted.forecast(steps=forecast_days)

            # Confidence intervals (approximate)
            residual_std = m["residuals_std"]
            fc_values = fc.tolist()
            upper = [v + 1.96 * residual_std for v in fc_values]
            lower = [v - 1.96 * residual_std for v in fc_values]

            # Trend direction
            if len(fc_values) >= 3:
                trend_slope = (fc_values[-1] - fc_values[0]) / len(fc_values)
                if trend_slope > 1:
                    direction = "上升"
                elif trend_slope < -1:
                    direction = "下降"
                else:
                    direction = "平稳"
            else:
                direction = "平稳"

            # Alarm level
            avg_pred = np.mean(fc_values)
            base_avg = np.mean(series[-7:])
            ratio = avg_pred / (base_avg + 1)
            if ratio > 2:
                alarm = "红色警报"
            elif ratio > 1.5:
                alarm = "橙色警报"
            elif ratio > 1.2:
                alarm = "黄色预警"
            else:
                alarm = "正常"

            results[disease] = {
                "predicted_counts": [max(0, round(v, 1)) for v in fc_values],
                "upper_bound": [max(0, round(v, 1)) for v in upper],
                "lower_bound": [max(0, round(v, 1)) for v in lower],
                "trend_direction": direction,
                "alarm_level": alarm,
                "forecast_days": forecast_days,
            }
        except Exception as e:
            results[disease] = {"error": str(e)}

    return {
        "diseases": results,
        "metrics": model_data["metrics"].get(disease_name if disease_name else "", {}),
    }


if __name__ == "__main__":
    train()

    # Test
    print("\nTest forecast for 流行性感冒 (14 days):")
    result = predict_forecast("流行性感冒", 14)
    print(f"  Trend: {result['diseases']['流行性感冒']['trend_direction']}")
    print(f"  Alarm: {result['diseases']['流行性感冒']['alarm_level']}")
    print(f"  First 3 predictions: {result['diseases']['流行性感冒']['predicted_counts'][:3]}")


