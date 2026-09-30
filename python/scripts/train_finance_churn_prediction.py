"""
Finance Customer Churn Prediction - XGBoost Classifier
=====================================================
Predict customer churn risk for a financial platform.

Dataset: 20,000 synthetic customer profiles with 25+ behavioral features
Output model: ../models/finance_churn_prediction.pkl

Usage: python train_finance_churn_prediction.py
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
    from sklearn.metrics import classification_report, roc_auc_score, roc_curve
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
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
N_SAMPLES = 20000
TEST_SIZE = 0.2


def generate_customer_data(n=20000):
    """Generate synthetic customer data with churn labels."""
    np.random.seed(SEED)

    df = pd.DataFrame({
        'user_age': np.random.randint(18, 70, n),
        'account_age_days': np.random.exponential(500, n).clip(30, 3000).astype(int),
        'monthly_transaction_count': np.random.poisson(10, n).clip(0, 100).astype(float),
        'avg_transaction_amount': np.random.lognormal(4.5, 0.9, n).clip(10, 100000),
        'max_transaction_amount': np.random.lognormal(5, 1.1, n).clip(50, 200000),
        'transaction_amount_std': np.random.exponential(500, n).clip(10, 15000),
        'days_since_last_transaction': np.random.exponential(12, n).clip(0, 200).astype(int),
        'transaction_type_diversity': np.random.poisson(3, n).clip(1, 8).astype(float),
        'avg_balance': np.random.lognormal(8, 1.6, n).clip(100, 500000),
        'balance_volatility': np.random.exponential(0.2, n).clip(0.01, 1.5),
        'min_balance_30d': np.random.lognormal(6, 1.8, n).clip(0, 200000),
        'balance_trend_30d': np.random.normal(0, 0.15, n).clip(-0.5, 0.5),
        'login_frequency_per_week': np.random.poisson(3, n).clip(0, 30).astype(float),
        'days_since_last_login': np.random.exponential(4, n).clip(0, 90).astype(int),
        'feature_usage_count': np.random.poisson(4, n).clip(0, 20).astype(float),
        'support_ticket_count_90d': np.random.poisson(1, n).clip(0, 15).astype(float),
        'notification_click_rate': np.random.beta(2, 5, n),
        'credit_score': np.random.normal(650, 80, n).clip(300, 850).astype(int),
        'has_loan': np.random.choice([0, 1], n, p=[0.6, 0.4]).astype(int),
        'loan_default_history': np.random.choice([0, 1], n, p=[0.93, 0.07]).astype(int),
        'debt_to_income_ratio': np.random.beta(2, 5, n).clip(0, 1.5),
        'referral_count': np.random.poisson(1, n).clip(0, 10).astype(float),
        'is_premium_user': np.random.choice([0, 1], n, p=[0.7, 0.3]).astype(int),
    })

    # Churn probability: higher for inactive, low-engagement, high-debt users
    log_odds = (
        -1.5
        + 0.5 * (df['user_age'] > 55).astype(float)
        - 0.2 * np.log1p(df['account_age_days']) / 5
        - 0.06 * df['monthly_transaction_count']
        + 0.25 * (df['monthly_transaction_count'] < 3).astype(float)
        + 0.25 * np.log1p(df['days_since_last_transaction']) / 3
        - 0.08 * df['transaction_type_diversity']
        - 0.002 * np.log1p(df['avg_balance'])
        + 0.4 * df['balance_volatility']
        - 0.08 * df['balance_trend_30d']
        - 0.12 * df['login_frequency_per_week']
        + 0.15 * np.log1p(df['days_since_last_login']) / 2
        - 0.08 * df['feature_usage_count']
        + 0.08 * df['support_ticket_count_90d']
        + 0.4 * (df['notification_click_rate'] < 0.1).astype(float)
        - 0.002 * (df['credit_score'] - 600)
        + 0.25 * df['loan_default_history']
        + 0.15 * (df['debt_to_income_ratio'] > 0.4).astype(float)
        - 0.15 * df['referral_count']
        - 0.3 * df['is_premium_user']
        + np.random.normal(0, 0.4, n)
    )

    prob = (1 / (1 + np.exp(-log_odds))).clip(0.001, 0.9)
    df['churn_probability'] = prob
    df['has_churned'] = (np.random.random(n) < prob).astype(int)

    log.info(f"Generated {n} customer records, churn rate: {df['has_churned'].mean():.2%}")
    return df


def prepare_features(df):
    """Build feature set."""
    cols = [c for c in df.columns if c not in ('churn_probability', 'has_churned')]
    features = df[cols].copy()

    # Derived features
    features['avg_amount_ratio'] = features['avg_transaction_amount'] / (features['avg_balance'] + 1)
    features['balance_min_ratio'] = features['min_balance_30d'] / (features['avg_balance'] + 1)
    features['recency_score'] = np.exp(-features['days_since_last_transaction'] / 30)
    features['login_recency'] = np.exp(-features['days_since_last_login'] / 14)
    features['tx_frequency_score'] = np.minimum(1.0, features['monthly_transaction_count'] / 20)
    features['engagement_score'] = (
        features['tx_frequency_score'] * 0.4
        + features['recency_score'] * 0.4
        + np.minimum(1.0, features['feature_usage_count'] / 15) * 0.2
    )
    features['high_value_flag'] = (features['avg_balance'] > 100000).astype(int)
    features['inactive_flag'] = (features['days_since_last_transaction'] > 30).astype(int)
    features['premium_engagement'] = features['is_premium_user'] * features['engagement_score']
    features['debt_warning'] = (features['debt_to_income_ratio'] > 0.4).astype(int)
    return features


def main():
    log.info("=" * 60)
    log.info(f"Finance Customer Churn Prediction ({N_SAMPLES} customers)")
    log.info("=" * 60)

    # 1. Generate
    df = generate_customer_data(N_SAMPLES)

    sample_path = os.path.join(os.path.dirname(BASE_DIR), 'data', 'sample_finance_churn.csv')
    df.head(1000).to_csv(sample_path, index=False)

    # 2. Features
    features = prepare_features(df)
    feature_names = list(features.columns)
    X = features.values.astype(np.float64)
    y = df['has_churned'].values.astype(np.int64)

    log.info(f"Features: {len(feature_names)}, X: {X.shape}")
    log.info(f"Positive ratio: {y.mean():.4f}")

    # 3. Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=SEED, stratify=y
    )

    # 4. Scale
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # 5. Train
    if XGB_AVAILABLE:
        log.info("Training XGBoost...")
        pos_scale = (1 - y.mean()) / y.mean()
        model = xgb.XGBClassifier(
            n_estimators=400, max_depth=6, learning_rate=0.03, subsample=0.8,
            colsample_bytree=0.75, scale_pos_weight=pos_scale,
            reg_alpha=0.1, reg_lambda=1.0, eval_metric='auc',
            random_state=SEED,
        )
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    else:
        log.info("Training GB + RF ensemble...")
        gb = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.7, random_state=SEED)
        rf = RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=5, class_weight='balanced', random_state=SEED)
        gb.fit(X_train, y_train)
        rf.fit(X_train, y_train)
        model = (gb, rf)

    # 6. Evaluate
    if XGB_AVAILABLE:
        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = model.predict(X_test)
    else:
        gb, rf = model
        y_prob = (gb.predict_proba(X_test)[:, 1] + rf.predict_proba(X_test)[:, 1]) / 2
        y_pred = (y_prob >= 0.5).astype(int)

    auc = roc_auc_score(y_test, y_prob)

    log.info(f"\n📊 Evaluation:")
    log.info(f"   ROC-AUC: {auc:.4f}")
    log.info(f"\n   Classification Report:")
    for line in classification_report(y_test, y_pred, target_names=['Active', 'Churned']).split('\n'):
        log.info(f"   {line}")

    # Optimal threshold
    fpr, tpr, thresholds = roc_curve(y_test, y_prob)
    youden = np.argmax(tpr - fpr)
    best_thr = thresholds[youden]
    log.info(f"   Optimal threshold (Youden): {best_thr:.3f} (TPR={tpr[youden]:.3f}, FPR={fpr[youden]:.3f})")

    # Feature importance
    if XGB_AVAILABLE and hasattr(model, 'feature_importances_'):
        imp = sorted(zip(feature_names, model.feature_importances_), key=lambda x: -x[1])
        log.info(f"\n   Top 10 features:")
        for name, score in imp[:10]:
            log.info(f"     {name}: {score:.4f}")

    # 7. Save
    mdata = {'model': model if XGB_AVAILABLE else {'gb': model[0], 'rf': model[1], 'ensemble': True},
             'scaler': scaler, 'features': feature_names,
             'threshold': float(best_thr), 'auc': float(auc)}
    model_path = os.path.join(MODELS_DIR, 'finance_churn_prediction.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(mdata, f)
    log.info(f"\n✅ Model saved to {model_path}")

    config = {'model_file': 'finance_churn_prediction.pkl', 'features': feature_names,
              'n_features': len(feature_names), 'n_samples': N_SAMPLES,
              'auc': round(float(auc), 4), 'threshold': round(float(best_thr), 3)}
    config_path = os.path.join(MODELS_DIR, 'finance_churn_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # 8. Churn risk segmentation
    y_prob_test = y_prob
    log.info(f"\n📌 Churn risk segmentation:")
    for lo, hi, lbl in [(0, 0.2, 'Low (<20%)'), (0.2, 0.5, 'Med (20-50%)'),
                         (0.5, 0.8, 'High (50-80%)'), (0.8, 1, 'Crit (>80%)')]:
        pct = ((y_prob_test >= lo) & (y_prob_test < hi)).mean()
        log.info(f"   {lbl}: {pct:.1%}")

    log.info("\n🎉 Finance Churn Prediction training complete!")


if __name__ == '__main__':
    main()
