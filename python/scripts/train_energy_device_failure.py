"""
Energy Device Failure Prediction - XGBoost Classifier
=====================================================
Train an XGBoost classifier to predict device failure probability
based on operational parameters and historical maintenance data.

Output model: ../models/energy_device_failure.pkl

Usage: python train_energy_device_failure.py
"""

import numpy as np
import pandas as pd
import pickle
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    log.error("sklearn not installed. Install: pip install scikit-learn")
    exit(1)

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    log.warning("XGBoost not installed. Falling back to GradientBoostingClassifier.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)
N_SAMPLES = 5000
TEST_SIZE = 0.2


def generate_device_data(n=5000):
    """Generate synthetic energy device operational data."""
    np.random.seed(SEED)

    data = {
        'device_age_years': np.random.exponential(5, n).clip(0.1, 25),
        'operating_hours': np.random.uniform(100, 50000, n),
        'avg_temperature_c': np.random.normal(45, 15, n).clip(10, 90),
        'max_temperature_c': np.random.normal(65, 20, n).clip(20, 120),
        'vibration_level': np.random.exponential(2, n).clip(0.1, 15),
        'power_consumption_kw': np.random.normal(150, 50, n).clip(20, 400),
        'load_factor': np.random.beta(5, 2, n),  # 0-1
        'maintenance_frequency': np.random.poisson(3, n).clip(0, 20),  # per year
        'days_since_last_maintenance': np.random.exponential(90, n).clip(0, 730),
        'voltage_stability': np.random.beta(12, 2, n),  # 0-1, higher = more stable
        'ambient_temperature': np.random.normal(25, 10, n).clip(-10, 50),
        'humidity': np.random.uniform(20, 95, n),
    }

    df = pd.DataFrame(data)

    # Failure probability: higher age, higher temp, higher vibration, lower maintenance
    log_odds = (
        -3.5
        + 0.3 * np.log1p(df['device_age_years'])
        + 0.015 * (df['avg_temperature_c'] - 20) * 0.5
        + 0.02 * df['max_temperature_c'] * 0.3
        + 0.3 * df['vibration_level']
        + 0.001 * df['power_consumption_kw'] * 0.3
        - 0.2 * df['maintenance_frequency']
        + 0.005 * df['days_since_last_maintenance']
        - 2.0 * df['voltage_stability']
        + 0.01 * df['humidity'] * 0.2
        + 0.3 * (df['load_factor'] - 0.5).clip(0, 0.5) * 2
    )

    prob = 1 / (1 + np.exp(-log_odds))
    prob = prob.clip(0.01, 0.99)
    df['failure_probability'] = prob
    df['failure_label'] = (np.random.random(n) < prob).astype(int)

    log.info(f"Generated {n} samples, failure rate: {df['failure_label'].mean():.2%}")
    return df


def main():
    log.info("=" * 60)
    log.info("Energy Device Failure Prediction Model Training")
    log.info("=" * 60)

    # 1. Generate synthetic data
    df = generate_device_data(N_SAMPLES)

    # 2. Feature engineering
    feature_cols = [
        'device_age_years', 'operating_hours', 'avg_temperature_c',
        'max_temperature_c', 'vibration_level', 'power_consumption_kw',
        'load_factor', 'maintenance_frequency', 'days_since_last_maintenance',
        'voltage_stability', 'ambient_temperature', 'humidity'
    ]

    # Add interaction features
    df['age_temp_interaction'] = df['device_age_years'] * df['avg_temperature_c'] / 100
    df['vibration_load'] = df['vibration_level'] * df['load_factor']
    df['maintenance_gap'] = df['days_since_last_maintenance'] / (df['maintenance_frequency'] + 1)
    enhanced_features = feature_cols + ['age_temp_interaction', 'vibration_load', 'maintenance_gap']

    X = df[enhanced_features].values
    y = df['failure_label'].values

    # 3. Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=SEED, stratify=y
    )

    # 4. Scale
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # 5. Train model
    if XGB_AVAILABLE:
        log.info("Training XGBoost classifier...")
        model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=(1 - y.mean()) / y.mean(),  # handle imbalance
            random_state=SEED,
            eval_metric='logloss',
            use_label_encoder=False,
        )
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
    else:
        log.info("Training GradientBoosting classifier...")
        model = GradientBoostingClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            random_state=SEED
        )
        model.fit(X_train, y_train)

    # 6. Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)

    log.info("\n📊 Evaluation:")
    log.info(f"   ROC-AUC: {auc:.4f}")
    log.info(f"\n   Classification Report:")
    for line in classification_report(y_test, y_pred, target_names=['Normal', 'Failure']).split('\n'):
        log.info(f"   {line}")

    cm = confusion_matrix(y_test, y_pred)
    log.info(f"\n   Confusion Matrix:")
    log.info(f"   TN={cm[0,0]}  FP={cm[0,1]}")
    log.info(f"   FN={cm[1,0]}  TP={cm[1,1]}")

    # 7. Feature importance
    if hasattr(model, 'feature_importances_'):
        importances = sorted(zip(enhanced_features, model.feature_importances_),
                             key=lambda x: x[1], reverse=True)
        log.info(f"\n   Top 5 feature importances:")
        for name, score in importances[:5]:
            log.info(f"     {name}: {score:.4f}")

    # 8. Save model
    model_data = {
        'model': model,
        'scaler': scaler,
        'features': enhanced_features,
        'auc': float(auc),
    }

    model_path = os.path.join(MODELS_DIR, 'energy_device_failure.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    log.info(f"\n✅ Model saved to {model_path}")

    # 9. Save prediction config
    config = {
        'model_file': 'energy_device_failure.pkl',
        'features': enhanced_features,
        'feature_count': len(enhanced_features),
        'model_type': 'xgboost' if XGB_AVAILABLE else 'gradient_boosting',
        'auc': round(float(auc), 4),
        'threshold': 0.5,
    }
    config_path = os.path.join(MODELS_DIR, 'energy_device_failure_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    log.info(f"✅ Config saved to {config_path}")

    # 10. Sample prediction for verification
    sample = X_test[:3]
    sample_probs = model.predict_proba(sample)[:, 1]
    log.info(f"\n📌 Sample predictions: {[f'{p:.2%}' for p in sample_probs]}")

    log.info("🎉 Energy Device Failure Prediction Model training complete!")


if __name__ == '__main__':
    main()
