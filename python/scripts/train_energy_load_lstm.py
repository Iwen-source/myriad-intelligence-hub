"""
Energy Load Forecasting - LSTM Model
======================================
Train an LSTM neural network to predict energy consumption patterns.
Generates synthetic realistic energy load data based on typical consumption curves.

Dataset: 25,000 hourly records (~3 years of data) → ~24,000 training samples
Output model: ../models/energy_load_lstm.pth + ../models/energy_load_scaler.pkl

Usage: python train_energy_load_lstm.py
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

# ─────────────── Try PyTorch ───────────────
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    log.warning("PyTorch not installed. Falling back to sklearn ensemble.")

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    log.error("Neither PyTorch nor sklearn available. Install: pip install torch sklearn")
    exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

SEED = 42
np.random.seed(SEED)
if TORCH_AVAILABLE:
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)

SEQ_LEN = 48       # 48 hours lookback
FORECAST_HORIZON = 24  # predict next 24 hours
N_DAYS = 1200      # ~3.3 years of hourly data → ~30,000 samples
TEST_RATIO = 0.15
EPOCHS = 60
BATCH_SIZE = 128
HIDDEN_SIZE = 128
NUM_LAYERS = 3
LEARNING_RATE = 0.001
DROPOUT = 0.25


def generate_synthetic_load_data(n_days=1200):
    """
    Generate synthetic energy load data with realistic patterns:
    - Daily seasonality (low at night, peaks at 9-11am and 6-8pm)
    - Weekly seasonality (lower on weekends)
    - Seasonal trends (higher in summer/winter)
    - Year-over-year trend
    - Multiple noise components
    """
    n_points = n_days * 24  # hourly data
    hours = np.tile(np.arange(24), n_days)
    days = np.repeat(np.arange(n_days), 24)
    day_of_week = days % 7

    # Base load with annual seasonality and slight upward trend
    year_frac = (days % 365) / 365.0
    trend = 1.0 + 0.0001 * days  # very slight upward trend
    base_load = (150 + 30 * np.sin(2 * np.pi * year_frac - np.pi/2)
                 + 15 * np.cos(2 * np.pi * year_frac + np.pi/3)) * trend

    # Hourly pattern (double peak: morning + evening)
    hour_angle = np.pi * (hours - 6) / 12
    morning_peak = 0.5 * np.maximum(0, np.sin(hour_angle))
    evening_peak = 0.35 * np.maximum(0, np.sin(np.pi * (hours - 16) / 8))
    hour_factor = 0.3 + morning_peak + evening_peak
    hour_factor = np.clip(hour_factor, 0.25, 1.15)

    # Weekend effect (25-30% drop on weekends, gradual on Friday/Sunday)
    weekend_mask = (day_of_week >= 5).astype(float)
    friday_factor = (day_of_week == 4).astype(float) * 0.08  # slight Friday evening drop
    sunday_factor = (day_of_week == 6).astype(float) * 0.05  # Sunday recovery
    base_weekend = 1.0 - 0.28 * weekend_mask
    weekday_factor = base_weekend + friday_factor + sunday_factor

    # Temperature effect
    temp = 15 + 15 * np.sin(2 * np.pi * year_frac - np.pi/3)
    temp_effect = 1.0 - 0.04 * (temp - 20) / 20 + 0.015 * (temp - 20)**2 / 200

    # Random noise components
    noise_ar1 = np.zeros(n_points)  # AR(1) autocorrelated noise
    phi = 0.7
    noise_innov = np.random.normal(0, 0.02, n_points)
    for t in range(1, n_points):
        noise_ar1[t] = phi * noise_ar1[t-1] + noise_innov[t]

    noise_iid = np.random.normal(1.0, 0.025, n_points)
    combined_noise = noise_iid + noise_ar1 * 0.3

    # Combine all components
    load = base_load * hour_factor * weekday_factor * temp_effect * combined_noise
    load = np.maximum(load, 15)  # floor

    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=n_points, freq='h'),
        'load': load,
        'hour': hours,
        'day_of_week': day_of_week,
        'is_weekend': weekend_mask.astype(int),
        'season': ((days % 365) // 91).astype(int),
        'temperature': temp,
    })
    daily_mean = df.groupby(df['timestamp'].dt.date)['load'].mean()
    log.info(f"Daily load: mean={daily_mean.mean():.1f}, std={daily_mean.std():.1f}, "
             f"min={daily_mean.min():.1f}, max={daily_mean.max():.1f}")
    return df


def create_sequences(data, seq_len, horizon, predict_col=0):
    """
    Create (X, y) sequences for time series forecasting.
    X: seq_len timesteps × all features
    y: only the load column (predict_col) for the next `horizon` timesteps
    Returns X with shape (samples, seq_len, n_features), y with shape (samples, horizon)
    """
    X, y = [], []
    n_features = data.shape[1]
    for i in range(len(data) - seq_len - horizon):
        X.append(data[i:i + seq_len])                      # all features
        y.append(data[i + seq_len:i + seq_len + horizon, predict_col])  # only load
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


class LoadLSTM(nn.Module):
    def __init__(self, input_dim, hidden_size, num_layers, output_dim, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_size, num_layers,
                            batch_first=True, dropout=dropout)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size // 2, output_dim)
        )

    def forward(self, x):
        out, _ = self.lstm(x)         # out: (batch, seq_len, hidden_size)
        out = out[:, -1, :]           # take last timestep → (batch, hidden_size)
        out = self.fc(out)            # → (batch, output_dim)
        return out


def train_pytorch_lstm(X_train, y_train, X_test, y_test, input_dim):
    """Train LSTM model with PyTorch."""
    log.info("Training PyTorch LSTM...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    log.info(f"Using device: {device}")

    model = LoadLSTM(input_dim, HIDDEN_SIZE, NUM_LAYERS, FORECAST_HORIZON, DROPOUT).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)

    train_dataset = TensorDataset(torch.FloatTensor(X_train), torch.FloatTensor(y_train))
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True)

    best_test_loss = float('inf')
    best_state = None
    patience_counter = 0
    max_patience = 10

    for epoch in range(EPOCHS):
        model.train()
        epoch_loss = 0
        for batch_X, batch_y in train_loader:
            batch_X = batch_X.to(device)
            batch_y = batch_y.to(device)
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            epoch_loss += loss.item()

        # Evaluate
        model.eval()
        with torch.no_grad():
            test_tensor = torch.FloatTensor(X_test).to(device)
            test_preds = model(test_tensor).cpu().numpy()
            test_loss = np.mean((test_preds - y_test) ** 2)
            test_mae = np.mean(np.abs(test_preds - y_test))

        scheduler.step(test_loss)

        # Early stopping
        if test_loss < best_test_loss:
            best_test_loss = test_loss
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1

        if (epoch + 1) % 5 == 0 or epoch == 0:
            log.info(f"  Epoch {epoch+1:3d}/{EPOCHS} | Train Loss: {epoch_loss/len(train_loader):.6f} "
                     f"| Test Loss: {test_loss:.4f} | Test MAE: {test_mae:.2f} | LR: {optimizer.param_groups[0]['lr']:.6f}")

        if patience_counter >= max_patience:
            log.info(f"  Early stopping at epoch {epoch+1}")
            break

    # Restore best model
    if best_state:
        model.load_state_dict(best_state)

    # Save model
    model_path = os.path.join(MODELS_DIR, 'energy_load_lstm.pth')
    torch.save({
        'model_state_dict': model.state_dict(),
        'input_dim': input_dim,
        'hidden_size': HIDDEN_SIZE,
        'num_layers': NUM_LAYERS,
        'output_dim': FORECAST_HORIZON,
        'seq_len': SEQ_LEN,
    }, model_path)
    log.info(f"✅ Model saved to {model_path}")

    model.eval()
    with torch.no_grad():
        preds = model(torch.FloatTensor(X_test).to(device)).cpu().numpy()
    return model, preds


def train_sklearn_rf(X_train, y_train, X_test, y_test):
    """Fallback: Random Forest for multi-output regression."""
    log.info("Training sklearn RandomForest (fallback)...")

    # Flatten time dimension
    X_train_2d = X_train.reshape(X_train.shape[0], -1)
    X_test_2d = X_test.reshape(X_test.shape[0], -1)

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=25,
        min_samples_leaf=2,
        min_samples_split=5,
        n_jobs=-1,
        random_state=SEED
    )
    model.fit(X_train_2d, y_train)

    preds = model.predict(X_test_2d)

    # Save model
    model_path = os.path.join(MODELS_DIR, 'energy_load_rf.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump({
            'model': model,
            'seq_len': SEQ_LEN,
            'horizon': FORECAST_HORIZON,
            'n_features': X_train.shape[2],
            'feature_names': ['load_history_48h', 'hour', 'day_of_week',
                              'is_weekend', 'season', 'temperature',
                              'lag1', 'lag24', 'lag48', 'rolling_7d']
        }, f)
    log.info(f"✅ Model saved to {model_path}")
    return model, preds


def main():
    log.info("=" * 60)
    log.info(f"Energy Load Forecasting Model Training ({N_DAYS} days of data)")
    log.info("=" * 60)

    # 1. Generate data
    log.info("Generating synthetic energy load data...")
    df = generate_synthetic_load_data(n_days=N_DAYS)
    log.info(f"Generated {len(df)} hourly records ({N_DAYS} days)")

    # Save sample data
    sample_dir = os.path.join(BASE_DIR, '..', 'data')
    sample_path = os.path.join(sample_dir, 'sample_energy_load.csv')
    df.head(2000).to_csv(sample_path, index=False)
    log.info(f"Sample data saved to {sample_path}")

    # 2. Feature engineering
    df['load_lag_1'] = df['load'].shift(1)
    df['load_lag_24'] = df['load'].shift(24)
    df['load_lag_48'] = df['load'].shift(48)
    df['load_lag_168'] = df['load'].shift(168)  # 1 week lag
    df['load_rolling_7d'] = df['load'].rolling(168).mean()
    df['load_rolling_24h'] = df['load'].rolling(24).mean()
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

    feature_cols = ['load', 'hour_sin', 'hour_cos', 'dow_sin', 'dow_cos',
                    'is_weekend', 'season', 'temperature',
                    'load_lag_1', 'load_lag_24', 'load_lag_48', 'load_lag_168',
                    'load_rolling_7d', 'load_rolling_24h']
    df_clean = df.dropna().reset_index(drop=True)
    data_array = df_clean[feature_cols].values

    log.info(f"Feature dimensions: {data_array.shape}")
    log.info(f"Features ({len(feature_cols)}): {feature_cols}")

    # 3. Create sequences
    X, y = create_sequences(data_array, SEQ_LEN, FORECAST_HORIZON, predict_col=0)
    log.info(f"Sequences created: X {X.shape}, y {y.shape}")
    log.info(f"Total samples: {len(X)}")
    log.info(f"Training samples: ~{int(len(X) * (1 - TEST_RATIO))}")
    log.info(f"Test samples: ~{int(len(X) * TEST_RATIO)}")

    # 4. Train/test split (temporal, not random)
    split_idx = int(len(X) * (1 - TEST_RATIO))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # 5. Scale features
    n_features = X_train.shape[2]
    scaler = StandardScaler()
    X_train_2d = X_train.reshape(-1, n_features)
    X_test_2d = X_test.reshape(-1, n_features)
    X_train_scaled = scaler.fit_transform(X_train_2d).reshape(X_train.shape)
    X_test_scaled = scaler.transform(X_test_2d).reshape(X_test.shape)

    # Save scaler
    scaler_path = os.path.join(MODELS_DIR, 'energy_load_scaler.pkl')
    with open(scaler_path, 'wb') as f:
        pickle.dump({
            'scaler': scaler,
            'feature_names': feature_cols,
            'seq_len': SEQ_LEN,
            'horizon': FORECAST_HORIZON,
            'n_features': n_features,
        }, f)
    log.info(f"✅ Scaler saved to {scaler_path}")

    # 6. Train model
    if TORCH_AVAILABLE:
        model, preds = train_pytorch_lstm(X_train_scaled, y_train, X_test_scaled, y_test, n_features)
    else:
        model, preds = train_sklearn_rf(X_train_scaled, y_train, X_test_scaled, y_test)

    # 7. Evaluate
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    mape = np.mean(np.abs((y_test - preds) / (y_test + 1e-6))) * 100
    log.info(f"\n📊 Evaluation on test set ({len(y_test)} sequences):")
    log.info(f"   MAE:  {mae:.2f} kW")
    log.info(f"   MAPE: {mape:.2f}%")
    log.info(f"   R²:   {r2:.4f}")

    # Per-hour analysis
    hourly_mae = np.mean(np.abs(preds - y_test), axis=0)
    log.info(f"\n   Hourly MAE (hours 1-24):")
    for h in range(0, 24, 4):
        log.info(f"     h{h+1:2d}-h{h+4:2d}: {np.mean(hourly_mae[h:h+4]):.2f} kW")

    # 8. Save config
    model_type = 'pytorch_lstm' if TORCH_AVAILABLE else 'sklearn_rf'
    model_file = 'energy_load_lstm.pth' if TORCH_AVAILABLE else 'energy_load_rf.pkl'
    config = {
        'seq_len': SEQ_LEN,
        'horizon': FORECAST_HORIZON,
        'n_features': n_features,
        'features': feature_cols,
        'n_days': N_DAYS,
        'n_samples': len(X),
        'mae': round(float(mae), 2),
        'mape': round(float(mape), 2),
        'r2': round(float(r2), 4),
        'model_type': model_type,
        'model_file': model_file,
    }
    config_path = os.path.join(MODELS_DIR, 'energy_load_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    log.info(f"✅ Config saved to {config_path}")

    # 9. Demo prediction
    sample_idx = np.random.randint(0, min(10, len(X_test)))
    sample_input = X_test[sample_idx:sample_idx+1]
    sample_actual = y_test[sample_idx]
    if TORCH_AVAILABLE:
        model.eval()
        with torch.no_grad():
            sample_pred = model(torch.FloatTensor(sample_input).to(
                torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            )).cpu().numpy()[0]
    else:
        sample_pred = model.predict(sample_input.reshape(1, -1))[0]

    log.info(f"\n📌 Sample 24h forecast (sample {sample_idx}):")
    log.info(f"   Actual first 6h: {[f'{v:.1f}' for v in sample_actual[:6]]}")
    log.info(f"   Predicted first 6h: {[f'{v:.1f}' for v in sample_pred[:6]]}")
    log.info(f"   Actual peak: {sample_actual.max():.1f} @ h{sample_actual.argmax()+1}")
    log.info(f"   Predicted peak: {sample_pred.max():.1f} @ h{sample_pred.argmax()+1}")

    log.info("\n🎉 Energy Load Forecasting Model training complete!")


if __name__ == '__main__':
    main()
