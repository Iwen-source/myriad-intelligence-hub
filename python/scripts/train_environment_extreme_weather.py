"""
Environment Extreme Weather Event Classifier - RandomForest
============================================================
Classifies weather conditions into severity levels using RandomForest.

Dataset: 25,000 synthetic weather records with air quality + meteorological features
Output model: ../models/environment_extreme_weather.pkl

Usage: python train_environment_extreme_weather.py
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
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
    from sklearn.utils.class_weight import compute_class_weight
    SKLEARN_AVAILABLE = True
except ImportError:
    log.error("sklearn not installed. Install: pip install scikit-learn")
    exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)
N_SAMPLES = 25000
TEST_SIZE = 0.2

EVENT_LEVELS = ['normal', 'advisory', 'warning', 'emergency']
EVENT_TYPES = ['无异常', '高温热浪', '寒潮低温', '暴雨预警', '雾霾严重', '沙尘暴', '臭氧污染', '静稳天气']


def generate_weather_data(n=25000):
    """Generate synthetic weather data with extreme event patterns (better balanced)."""
    np.random.seed(SEED)

    # Start with mostly normal conditions
    df = pd.DataFrame({
        'pm25': np.random.lognormal(3.2, 0.6, n).clip(5, 500),
        'pm10': np.random.lognormal(3.8, 0.6, n).clip(10, 800),
        'o3': np.random.normal(60, 35, n).clip(0, 300),
        'no2': np.random.normal(35, 18, n).clip(0, 200),
        'so2': np.random.normal(12, 8, n).clip(0, 100),
        'co': np.random.normal(1.2, 0.8, n).clip(0.1, 10),
        'temperature': np.random.normal(20, 12, n).clip(-20, 45),
        'humidity': np.random.uniform(20, 95, n),
        'pressure': np.random.normal(1013, 15, n).clip(970, 1050),
        'wind_speed': np.random.exponential(3, n).clip(0, 30),
        'wind_direction': np.random.uniform(0, 360, n),
        'precipitation': np.random.exponential(1.5, n).clip(0, 50),
        'season': np.random.randint(0, 4, n).astype(int),
        'is_extreme_season': np.random.choice([0, 1], n, p=[0.65, 0.35]).astype(int),
        'aqi_trend_3d': np.random.normal(0, 0.08, n).clip(-0.4, 0.4),
        'temp_anomaly': np.random.normal(0, 2.5, n).clip(-10, 10),
        'consecutive_high_aqi': np.random.poisson(0.5, n).clip(0, 8).astype(int),
    })

    # Manually inject more extreme events (about 15% of data)
    n_extreme = n // 6
    extreme_idx = np.random.choice(n, n_extreme, replace=False)
    for idx in extreme_idx:
        event_type = np.random.choice(['heat', 'cold', 'haze', 'rain', 'sand', 'ozone'])
        if event_type == 'heat':
            df.loc[idx, 'temperature'] = np.random.uniform(36, 42)
            df.loc[idx, 'humidity'] = np.random.uniform(25, 45)
            df.loc[idx, 'o3'] = np.random.uniform(160, 280)
            df.loc[idx, 'wind_speed'] = np.random.uniform(0, 4)
        elif event_type == 'cold':
            df.loc[idx, 'temperature'] = np.random.uniform(-18, -8)
            df.loc[idx, 'pressure'] = np.random.uniform(1025, 1045)
            df.loc[idx, 'wind_speed'] = np.random.uniform(8, 20)
        elif event_type == 'haze':
            df.loc[idx, 'pm25'] = np.random.uniform(160, 350)
            df.loc[idx, 'pm10'] = np.random.uniform(200, 450)
            df.loc[idx, 'humidity'] = np.random.uniform(65, 90)
            df.loc[idx, 'wind_speed'] = np.random.uniform(0, 3)
            df.loc[idx, 'visibility'] = np.random.uniform(0.5, 3)
        elif event_type == 'rain':
            df.loc[idx, 'precipitation'] = np.random.uniform(18, 45)
            df.loc[idx, 'humidity'] = np.random.uniform(80, 98)
            df.loc[idx, 'pressure'] = np.random.uniform(985, 1005)
        elif event_type == 'sand':
            df.loc[idx, 'pm10'] = np.random.uniform(350, 700)
            df.loc[idx, 'wind_speed'] = np.random.uniform(10, 25)
            df.loc[idx, 'visibility'] = np.random.uniform(0.1, 2)
        elif event_type == 'ozone':
            df.loc[idx, 'o3'] = np.random.uniform(180, 280)
            df.loc[idx, 'temperature'] = np.random.uniform(30, 38)
            df.loc[idx, 'humidity'] = np.random.uniform(30, 50)

    # Severity assignment
    severity = np.zeros(n, dtype=int)
    event_label = np.full(n, '无异常', dtype=object)

    # Heat wave
    heat = (df['temperature'] > 36).values & (df['o3'] > 150).values
    severity[heat] = np.maximum(severity[heat], 2)
    event_label[heat] = '高温热浪'
    mild_heat = (df['temperature'] > 33).values & (df['o3'] > 120).values
    severity[mild_heat] = np.maximum(severity[mild_heat], 1)
    event_label[mild_heat & ~heat] = '高温热浪'

    # Cold wave
    cold = (df['temperature'] < -10).values
    severity[cold] = np.maximum(severity[cold], 2)
    event_label[cold] = '寒潮低温'
    mild_cold = (df['temperature'] < -5).values & (df['wind_speed'] > 8).values
    severity[mild_cold] = np.maximum(severity[mild_cold], 1)
    event_label[mild_cold & ~cold] = '寒潮低温'

    # Heavy haze
    haze = (df['pm25'] > 200).values & (df['wind_speed'] < 4).values
    severity[haze] = np.maximum(severity[haze], 2)
    event_label[haze] = '雾霾严重'
    mild_haze = (df['pm25'] > 120).values & (df['wind_speed'] < 4).values
    severity[mild_haze] = np.maximum(severity[mild_haze], 1)
    event_label[mild_haze & ~haze] = '雾霾严重'

    # Rain
    rain = (df['precipitation'] > 20).values & (df['humidity'] > 80).values
    severity[rain] = np.maximum(severity[rain], 2)
    event_label[rain] = '暴雨预警'
    mild_rain = (df['precipitation'] > 10).values & (df['humidity'] > 75).values
    severity[mild_rain] = np.maximum(severity[mild_rain], 1)
    event_label[mild_rain & ~rain] = '暴雨预警'

    # Sand
    sand = (df['pm10'] > 350).values & (df['wind_speed'] > 8).values
    severity[sand] = np.maximum(severity[sand], 2)
    event_label[sand] = '沙尘暴'

    # Ozone
    ozone = (df['o3'] > 200).values & (df['temperature'] > 30).values
    severity[ozone] = np.maximum(severity[ozone], 2)
    event_label[ozone] = '臭氧污染'
    mild_ozone = (df['o3'] > 150).values & (df['temperature'] > 28).values
    severity[mild_ozone] = np.maximum(severity[mild_ozone], 1)
    event_label[mild_ozone & ~ozone] = '臭氧污染'

    # Emergency compound events
    compound = ((df['temperature'] > 38).values & (df['o3'] > 220).values) | \
               ((df['pm25'] > 280).values & (df['wind_speed'] > 8).values) | \
               ((df['temperature'] < -15).values & (df['wind_speed'] > 15).values)
    severity[compound] = np.minimum(severity[compound] + 1, 3)

    df['severity_level'] = severity
    df['severity_label'] = [EVENT_LEVELS[s] for s in severity]
    df['event_type'] = event_label

    # Log distribution
    sev_dist = df['severity_label'].value_counts()
    log.info(f"Generated {n} records, severity: {sev_dist.to_dict()}")
    for cat in EVENT_LEVELS:
        count = sev_dist.get(cat, 0)
        log.info(f"  {cat}: {count} ({count/n*100:.1f}%)")
    return df


def build_features(df):
    """Build feature set."""
    f = pd.DataFrame()

    # Raw + log AQ
    for col in ['pm25', 'pm10', 'o3', 'no2', 'so2', 'co']:
        f[col] = df[col]
        f[f'{col}_log'] = np.log1p(df[col])

    # Meteorology
    for col in ['temperature', 'humidity', 'pressure', 'wind_speed', 'precipitation']:
        f[col] = df[col]

    # Wind direction cyclic
    f['wind_dir_sin'] = np.sin(2 * np.pi * df['wind_direction'] / 360)
    f['wind_dir_cos'] = np.cos(2 * np.pi * df['wind_direction'] / 360)

    # Temporal
    f['season'] = df['season']
    f['is_extreme_season'] = df['is_extreme_season']

    # Derived indices (used in enhanced_routes.py)
    f['aqi_estimate'] = 0.5 * df['pm25'] + 0.3 * df['pm10'] + 0.1 * df['o3'] + 0.1 * df['no2']
    f['temp_humidity_index'] = df['temperature'] * df['humidity'] / 100
    f['discomfort_index'] = 0.8 * df['temperature'] + 0.01 * df['humidity'] * (0.99 * df['temperature'] - 14.3) + 46.4
    f['pm25_pm10_ratio'] = df['pm25'] / (df['pm10'] + 1)
    wind_chill = 13.12 + 0.6215 * df['temperature'] - 11.37 * df['wind_speed']**0.16 + 0.3965 * df['temperature'] * df['wind_speed']**0.16
    f['wind_chill'] = np.minimum(wind_chill, df['temperature'])

    # Historical
    f['aqi_trend_3d'] = df['aqi_trend_3d']
    f['temp_anomaly'] = df['temp_anomaly']
    f['consecutive_high_aqi'] = df['consecutive_high_aqi']

    # Interactions
    f['heat_stress'] = df['temperature'] * (df['humidity'] / 100) * df['o3'] / 100
    f['cold_stress'] = np.maximum(0, -df['temperature']) * df['wind_speed'] / 10
    f['pollution_buildup'] = df['consecutive_high_aqi'] * (df['pm25'] / 100)
    f['dust_potential'] = df['pm10'] * df['wind_speed'] / 100
    return f


def main():
    log.info("=" * 60)
    log.info(f"Extreme Weather Classifier ({N_SAMPLES} records)")
    log.info("=" * 60)

    df = generate_weather_data(N_SAMPLES)

    sample_path = os.path.join(os.path.dirname(BASE_DIR), 'data', 'sample_extreme_weather.csv')
    df.head(1000).to_csv(sample_path, index=False)

    features = build_features(df)
    feature_names = list(features.columns)
    X = features.values.astype(np.float64)

    le = LabelEncoder()
    y = le.fit_transform(df['severity_label'])

    log.info(f"Features: {len(feature_names)}, X: {X.shape}")
    log.info(f"Classes: {list(le.classes_)}")

    # Stratified split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=SEED, stratify=y
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    # Class weights
    classes = np.unique(y_train)
    cw = compute_class_weight('balanced', classes=classes, y=y_train)
    cw_dict = dict(zip(classes, cw))
    log.info(f"Class weights: {cw_dict}")

    # Train
    log.info("Training RandomForest...")
    model = RandomForestClassifier(
        n_estimators=400, max_depth=18, min_samples_leaf=5,
        class_weight='balanced', n_jobs=-1, random_state=SEED
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)
    acc = accuracy_score(y_test, y_pred)

    log.info(f"\n📊 Evaluation:")
    log.info(f"   Accuracy: {acc:.2%}")
    log.info(f"\n   Report:")
    for line in classification_report(y_test, y_pred, target_names=le.classes_).split('\n'):
        log.info(f"   {line}")

    cm = confusion_matrix(y_test, y_pred)
    log.info(f"\n   Confusion Matrix:")
    for i, row_label in enumerate(le.classes_):
        row_vals = '  '.join(f'{cm[i,j]:4d}' for j in range(len(le.classes_)))
        log.info(f"   {row_label:>10}: {row_vals}")

    # Feature importance
    imp = sorted(zip(feature_names, model.feature_importances_), key=lambda x: -x[1])
    log.info(f"\n   Top 10 features:")
    for name, score in imp[:10]:
        log.info(f"     {name}: {score:.4f}")

    # Save
    mdata = {'model': model, 'scaler': scaler, 'label_encoder': le,
             'features': feature_names, 'event_levels': EVENT_LEVELS, 'event_types': EVENT_TYPES}
    model_path = os.path.join(MODELS_DIR, 'environment_extreme_weather.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(mdata, f)
    log.info(f"\n✅ Model saved to {model_path}")

    config = {'model_file': 'environment_extreme_weather.pkl', 'features': feature_names,
              'n_features': len(feature_names), 'n_samples': N_SAMPLES,
              'accuracy': round(float(acc), 4), 'classes': list(le.classes_)}
    config_path = os.path.join(MODELS_DIR, 'extreme_weather_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # Demo predictions
    log.info(f"\n📌 Sample Predictions:")
    test_rows = pd.DataFrame([
        {'pm25': 35, 'pm10': 60, 'o3': 120, 'no2': 30, 'so2': 10, 'co': 0.8,
         'temperature': 28, 'humidity': 45, 'pressure': 1010, 'wind_speed': 5,
         'wind_direction': 180, 'precipitation': 0, 'season': 1, 'is_extreme_season': 0,
         'aqi_trend_3d': 0.05, 'temp_anomaly': 2, 'consecutive_high_aqi': 1},
        {'pm25': 280, 'pm10': 350, 'o3': 50, 'no2': 60, 'so2': 25, 'co': 2.5,
         'temperature': 5, 'humidity': 75, 'pressure': 1025, 'wind_speed': 2,
         'wind_direction': 90, 'precipitation': 0, 'season': 0, 'is_extreme_season': 1,
         'aqi_trend_3d': 0.3, 'temp_anomaly': -5, 'consecutive_high_aqi': 5},
        {'pm25': 15, 'pm10': 30, 'o3': 60, 'no2': 15, 'so2': 5, 'co': 0.3,
         'temperature': 22, 'humidity': 50, 'pressure': 1015, 'wind_speed': 8,
         'wind_direction': 270, 'precipitation': 0, 'season': 1, 'is_extreme_season': 0,
         'aqi_trend_3d': -0.05, 'temp_anomaly': 0.5, 'consecutive_high_aqi': 0},
    ])
    for i, (_, row) in enumerate(test_rows.iterrows()):
        feat = build_features(pd.DataFrame([row.to_dict()]))
        feat_scaled = scaler.transform(feat.values)
        probs = model.predict_proba(feat_scaled)[0]
        pred = le.inverse_transform([model.predict(feat_scaled)[0]])[0]
        conf = probs.max()
        log.info(f"  Case {i+1}: {pred} (conf={conf:.1%})")
        for lv, pr in zip(le.classes_, probs):
            bar = '█' * int(pr * 20)
            log.info(f"    {lv:>10}: {bar} {pr:.1%}")

    log.info("\n🎉 Extreme Weather Classifier training complete!")


if __name__ == '__main__':
    main()
