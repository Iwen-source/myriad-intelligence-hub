"""
Traffic Accident Risk Prediction - XGBoost Classifier
=====================================================
Trains an XGBoost model to predict real-time traffic accident risk.

Dataset: 30,000 synthetic traffic records with 21 features
Output model: ../models/traffic_accident_risk.pkl

Usage: python train_traffic_accident_risk.py
"""

import numpy as np
import pandas as pd
import pickle
import os
import json
import logging
import warnings
warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

try:
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
    from sklearn.ensemble import GradientBoostingClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    log.error("sklearn not installed.")
    exit(1)

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    log.warning("XGBoost not available.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)
N_SAMPLES = 30000
TEST_SIZE = 0.2


def generate_traffic_data(n=30000):
    """Generate synthetic traffic data with accident labels."""
    np.random.seed(SEED)
    df = pd.DataFrame({
        'hour': np.random.randint(0, 24, n),
        'day_of_week': np.random.randint(0, 7, n),
        'is_weekend': np.random.randint(0, 2, n),
        'is_holiday': np.random.choice([0, 1], n, p=[0.95, 0.05]),
        'season': np.random.randint(0, 4, n),
        'weather_code': np.random.choice([0, 1, 2, 3, 4, 5], n, p=[0.35, 0.25, 0.15, 0.08, 0.10, 0.07]),
        'visibility_km': np.random.exponential(12, n).clip(0.1, 50),
        'section_capacity': np.random.choice([1200, 1500, 1800, 2000, 2200], n),
        'lanes': np.random.choice([1, 2, 3, 4, 5, 6], n, p=[0.04, 0.08, 0.22, 0.35, 0.18, 0.13]),
        'speed_limit': np.random.choice([30, 40, 50, 60, 70, 80, 100, 120], n,
                                        p=[0.04, 0.06, 0.10, 0.18, 0.22, 0.18, 0.14, 0.08]),
        'road_type': np.random.choice([0, 1, 2, 3], n, p=[0.20, 0.40, 0.25, 0.15]),
        'traffic_volume': np.random.lognormal(6.8, 0.9, n).clip(10, 12000),
        'accident_count_7d': np.random.poisson(2.0, n).clip(0, 25),
    })

    congestion = df['traffic_volume'] / (df['section_capacity'] * df['lanes'] / 2)
    df['congestion_index'] = np.clip(congestion * 55, 0, 100)
    df['avg_speed'] = df['speed_limit'] * np.clip(1.0 - 0.35 * (congestion - 0.5), 0.25, 1.0)
    df['avg_speed'] += np.random.normal(0, 4, n)

    is_night = ((df['hour'] >= 22) | (df['hour'] <= 5)).astype(float)
    is_rush = (((df['hour'] >= 7) & (df['hour'] <= 9)) | ((df['hour'] >= 17) & (df['hour'] <= 19))).astype(float)
    bad_wx = (df['weather_code'] >= 2).astype(float)
    severe_wx = (df['weather_code'] >= 4).astype(float)
    low_vis = (df['visibility_km'] < 2).astype(float)
    high_spd = (df['speed_limit'] >= 80).astype(float)
    high_cong = (df['congestion_index'] > 60).astype(float)
    highway = (df['road_type'] == 0).astype(float)

    log_odds = (-5.0 + 1.3 * is_night + 0.7 * is_rush + 0.6 * bad_wx + 1.8 * severe_wx
                + 1.2 * low_vis + 0.5 * high_spd + 0.8 * high_cong + 0.3 * highway
                + 0.4 * np.log1p(df['accident_count_7d']) * 0.3 + 0.5 * is_night * bad_wx)
    prob = (1 / (1 + np.exp(-log_odds))).clip(0.001, 0.75)
    df['accident_risk'] = prob
    df['has_accident'] = (np.random.random(n) < prob).astype(int)

    log.info(f"Generated {n} records, accident rate: {df['has_accident'].mean():.2%}")
    return df


def build_features(df):
    """Build 21 feature columns."""
    f = pd.DataFrame()
    f['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    f['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    f['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    f['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    f['season_sin'] = np.sin(2 * np.pi * df['season'] / 4)
    f['season_cos'] = np.cos(2 * np.pi * df['season'] / 4)
    f['is_weekend'] = df['is_weekend'].astype(float)
    f['is_holiday'] = df['is_holiday'].astype(float)
    f['weather_code'] = df['weather_code'].astype(float)
    f['visibility_km'] = df['visibility_km'].astype(float)
    f['lanes'] = df['lanes'].astype(float)
    f['road_type'] = df['road_type'].astype(float)
    f['traffic_volume'] = np.log1p(df['traffic_volume'].astype(float))
    f['avg_speed'] = df['avg_speed'].astype(float) / df['speed_limit'].astype(float).clip(1)
    f['speed_limit'] = df['speed_limit'].astype(float)
    f['congestion_index'] = df['congestion_index'].astype(float)
    f['accident_count_7d'] = df['accident_count_7d'].astype(float)
    f['speed_congestion'] = df['speed_limit'].astype(float) * df['congestion_index'].astype(float) / 100
    f['night_bad_weather'] = f['hour_sin'] * (df['weather_code'] >= 2).astype(float)
    vcr = np.log1p(df['traffic_volume'].astype(float)) / np.log1p(df['section_capacity'].astype(float) * df['lanes'].astype(float))
    f['volume_capacity_ratio'] = vcr
    f['highway_night'] = (df['road_type'] == 0).astype(float) * ((df['hour'] >= 22) | (df['hour'] <= 5)).astype(float)
    return f


def main():
    log.info("=" * 60)
    log.info(f"Traffic Accident Risk Prediction ({N_SAMPLES} records)")
    log.info("=" * 60)

    df = generate_traffic_data(N_SAMPLES)
    sample_path = os.path.join(os.path.dirname(BASE_DIR), 'data', 'sample_traffic_accidents.csv')
    df.head(1000).to_csv(sample_path, index=False)

    features = build_features(df)
    feature_names = list(features.columns)
    X = features.values.astype(np.float64)
    y = df['has_accident'].values.astype(np.int64)
    log.info(f"Features: {len(feature_names)}, X: {X.shape}, pos ratio: {y.mean():.4f}")

    split_idx = int(len(X) * (1 - TEST_SIZE))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    if XGB_AVAILABLE:
        log.info("Training XGBoost...")
        pos_scale = (1 - y.mean()) / y.mean()
        model = xgb.XGBClassifier(n_estimators=500, max_depth=6, learning_rate=0.03,
            subsample=0.8, colsample_bytree=0.7, scale_pos_weight=pos_scale,
            reg_alpha=0.1, reg_lambda=2.0, eval_metric='auc', random_state=SEED)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    else:
        log.info("Training GradientBoosting...")
        model = GradientBoostingClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.7, max_features='sqrt', random_state=SEED)
        model.fit(X_train, y_train)

    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)
    precisions, recalls, thresholds = precision_recall_curve(y_test, y_prob)
    f1_scores = 2 * precisions[:-1] * recalls[:-1] / (precisions[:-1] + recalls[:-1] + 1e-10)
    best_idx = np.argmax(f1_scores)
    best_thr, best_f1 = thresholds[best_idx], f1_scores[best_idx]
    y_pred = (y_prob >= best_thr).astype(int)

    log.info(f"\n📊 Evaluation: AUC={auc:.4f}, best_thr={best_thr:.3f} (F1={best_f1:.3f})")
    for line in classification_report(y_test, y_pred, target_names=['Safe', 'Accident']).split('\n'):
        log.info(f"   {line}")

    if hasattr(model, 'feature_importances_'):
        imp = sorted(zip(feature_names, model.feature_importances_), key=lambda x: -x[1])
        log.info(f"\n   Top 10 features:")
        for name, score in imp[:10]:
            log.info(f"     {name}: {score:.4f}")

    model_data = {'model': model, 'scaler': scaler, 'features': feature_names,
                  'threshold': float(best_thr), 'auc': float(auc)}
    model_path = os.path.join(MODELS_DIR, 'traffic_accident_risk.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    log.info(f"\n✅ Model saved to {model_path}")

    config = {'model_file': 'traffic_accident_risk.pkl', 'n_features': len(feature_names),
              'n_samples': N_SAMPLES, 'auc': round(float(auc), 4), 'threshold': round(float(best_thr), 3)}
    with open(os.path.join(MODELS_DIR, 'traffic_accident_config.json'), 'w') as f:
        json.dump(config, f, indent=2)

    # Demo predictions (self-contained, doesn't need avg_speed in input)
    log.info(f"\n📌 Demo scenarios:")
    test_rows = [
        {'hour': 3, 'day_of_week': 6, 'is_weekend': 1, 'is_holiday': 0, 'season': 0,
         'weather_code': 4, 'visibility_km': 0.5, 'section_capacity': 1800, 'lanes': 2,
         'speed_limit': 80, 'road_type': 0, 'traffic_volume': 500, 'accident_count_7d': 3},
        {'hour': 8, 'day_of_week': 1, 'is_weekend': 0, 'is_holiday': 0, 'season': 1,
         'weather_code': 0, 'visibility_km': 15, 'section_capacity': 2000, 'lanes': 4,
         'speed_limit': 60, 'road_type': 1, 'traffic_volume': 4000, 'accident_count_7d': 1},
        {'hour': 14, 'day_of_week': 3, 'is_weekend': 0, 'is_holiday': 0, 'season': 1,
         'weather_code': 1, 'visibility_km': 10, 'section_capacity': 1600, 'lanes': 3,
         'speed_limit': 50, 'road_type': 1, 'traffic_volume': 800, 'accident_count_7d': 0},
    ]
    for i, s in enumerate(test_rows):
        c = s['traffic_volume'] / (s['section_capacity'] * s['lanes'] / 2)
        s['congestion_index'] = float(np.clip(c * 55, 0, 100))
        s['avg_speed'] = s['speed_limit'] * float(np.clip(1.0 - 0.35 * (c - 0.5), 0.25, 1.0))

        feat = build_features(pd.DataFrame([s]))
        feat_scaled = scaler.transform(feat.values.astype(np.float64))
        p = model.predict_proba(feat_scaled)[0, 1]
        level = 'Low' if p < 0.2 else 'Med' if p < 0.4 else 'High' if p < 0.6 else 'Crit'
        log.info(f"  Scenario {i+1}: {level} (p={p:.1%})")

    log.info("\n🎉 Traffic Accident Risk Model training complete!")


if __name__ == '__main__':
    main()
