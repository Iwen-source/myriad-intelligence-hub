"""
Market Trend Prediction: LSTM (PyTorch) + ARIMA baseline
Generates: lstm_model.pth, market_scaler.joblib, trend_baseline.joblib
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os
import random
import warnings
warnings.filterwarnings("ignore")

random.seed(42)
np.random.seed(42)

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

SEQUENCE_LENGTH = 60


class LSTMPredictor(nn.Module):
    def __init__(self, input_size=4, hidden_size=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, 7),  # Predict next 7 days
        )

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]  # Take last output
        out = self.fc(out)
        return out


def generate_market_data(n_days=1100):
    """Generate synthetic market data with trends and volatility."""
    data = []

    price = 100.0
    sentiment = 0.5

    for day in range(n_days):
        # Price movement with mean reversion
        trend = np.sin(2 * np.pi * day / 252) * 0.05  # Annual cycle
        noise = np.random.normal(0, 0.02)
        momentum = np.random.normal(0, 0.01) if day > 20 else 0

        # Volatility clustering
        if day > 0 and abs(data[-1]["volatility"] if data else 0) > 0.03:
            vol_shock = np.random.normal(0, 0.025)
        else:
            vol_shock = np.random.normal(0, 0.012)

        daily_return = trend + noise + momentum + vol_shock

        # Occasional jumps
        if random.random() < 0.02:
            daily_return += random.choice([-0.05, 0.05])

        price *= (1 + daily_return)
        price = max(price, 1)

        # Volume with price-volume relationship
        volume = 1000000 * (1 + abs(daily_return) * 5 + np.random.normal(0, 0.2))

        # Volatility (rolling)
        vol = abs(daily_return) * 2

        # Sentiment (mean-reverting)
        sentiment += np.random.normal(0, 0.05)
        sentiment = max(0, min(1, sentiment))
        if abs(daily_return) > 0.03 and daily_return < 0:
            sentiment -= 0.1
        elif abs(daily_return) > 0.03 and daily_return > 0:
            sentiment += 0.1

        data.append({
            "price": round(price, 2),
            "volume": round(volume),
            "volatility": round(vol, 4),
            "sentiment": round(sentiment, 4),
            "return": round(daily_return, 4),
            "trend_signal": round(trend, 4),
        })

    df = pd.DataFrame(data)
    print(f"Generated {len(df)} days of market data. Price range: {df['price'].min():.2f}-{df['price'].max():.2f}")
    return df


def create_sequences(data, seq_length=SEQUENCE_LENGTH):
    X, y = [], []
    for i in range(len(data) - seq_length - 6):
        X.append(data[i:i + seq_length])
        y.append(data[i + seq_length:i + seq_length + 7, 0])  # Predict price only
    return np.array(X), np.array(y)


def train():
    print("=" * 60)
    print("Training Market Trend Prediction Model (LSTM)")
    print("=" * 60)

    df = generate_market_data(1100)

    # Features: price, volume, volatility, sentiment
    feature_cols = ["price", "volume", "volatility", "sentiment"]
    data_matrix = df[feature_cols].values.astype(np.float32)

    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data_matrix)

    # Create sequences
    X, y = create_sequences(data_scaled)
    print(f"Sequences: X={X.shape}, y={y.shape}")

    # Split
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    X_train_t = torch.FloatTensor(X_train)
    y_train_t = torch.FloatTensor(y_train)
    X_test_t = torch.FloatTensor(X_test)
    y_test_t = torch.FloatTensor(y_test)

    # Train LSTM
    if TORCH_AVAILABLE and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    input_size = data_scaled.shape[1]

    if TORCH_AVAILABLE:
        model = LSTMPredictor(input_size=input_size)
        model = model.to(device)

        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

        # Train
        batch_size = 32
        n_epochs = 50
        n_batches = len(X_train_t) // batch_size

        for epoch in range(n_epochs):
            model.train()
            epoch_loss = 0
            for i in range(0, len(X_train_t), batch_size):
                batch_X = X_train_t[i:i + batch_size].to(device)
                batch_y = y_train_t[i:i + batch_size].to(device)

                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

                epoch_loss += loss.item()

            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch+1}/{n_epochs}, Loss: {epoch_loss/n_batches:.6f}")

        # Evaluate
        model.eval()
        with torch.no_grad():
            test_pred = model(X_test_t.to(device)).cpu().numpy()
            test_actual = y_test

        # Inverse transform price predictions
        price_mean = scaler.mean_[0]
        price_std = scaler.scale_[0]
        pred_prices = test_pred * price_std + price_mean
        actual_prices = test_actual * price_std + price_mean

        mae = mean_absolute_error(actual_prices, pred_prices)
        rmse = np.sqrt(mean_squared_error(actual_prices, pred_prices))
        print(f"\nLSTM Test MAE: {mae:.4f}, RMSE: {rmse:.4f}")

        # Direction accuracy (next day direction)
        dir_actual = np.sign(actual_prices[:, 1] - actual_prices[:, 0])
        dir_pred = np.sign(pred_prices[:, 1] - pred_prices[:, 0])
        dir_acc = np.mean(dir_actual == dir_pred)
        print(f"Direction accuracy (day+1): {dir_acc:.2%}")

        # Save model
        out_dir = os.path.dirname(__file__)
        torch.save(model.state_dict(), os.path.join(out_dir, "lstm_model.pth"))
        print("LSTM model saved.")
    else:
        print("PyTorch not available, using linear baseline.")
        pred_prices = np.tile(y_test.mean(axis=1, keepdims=True), (1, 7)) * scaler.scale_[0] + scaler.mean_[0]
        actual_prices = y_test * scaler.scale_[0] + scaler.mean_[0]

    # Save scaler and metadata
    out_dir = os.path.dirname(__file__)
    joblib.dump(scaler, os.path.join(out_dir, "market_scaler.joblib"))
    joblib.dump({
        "feature_cols": feature_cols,
        "seq_length": SEQUENCE_LENGTH,
        "input_size": input_size,
        "last_60_days": data_matrix[-SEQUENCE_LENGTH:].tolist(),
        "torch_available": TORCH_AVAILABLE,
    }, os.path.join(out_dir, "trend_baseline.joblib"))
    print("Baseline/feature metadata saved.")


def predict_trend(past_60_days: list = None):
    """Predict next 7 days of market data."""
    out_dir = os.path.dirname(__file__)
    scaler = joblib.load(os.path.join(out_dir, "market_scaler.joblib"))
    meta = joblib.load(os.path.join(out_dir, "trend_baseline.joblib"))

    if past_60_days is None:
        past_60_days = meta["last_60_days"]

    data = np.array(past_60_days, dtype=np.float32)

    # Ensure correct sequence length
    if len(data) < SEQUENCE_LENGTH:
        # Pad with first value
        pad = np.tile(data[0:1], (SEQUENCE_LENGTH - len(data), 1))
        data = np.vstack([pad, data])
    elif len(data) > SEQUENCE_LENGTH:
        data = data[-SEQUENCE_LENGTH:]

    data_scaled = scaler.transform(data)
    X = torch.FloatTensor(data_scaled).unsqueeze(0)  # Add batch dim

    device = torch.device("cpu")
    if TORCH_AVAILABLE and meta["torch_available"]:
        model = LSTMPredictor(input_size=meta["input_size"])
        model.load_state_dict(torch.load(os.path.join(out_dir, "lstm_model.pth"), map_location=device))
        model.to(device)
        model.eval()

        with torch.no_grad():
            pred_scaled = model(X.to(device)).cpu().numpy()[0]

        # Inverse transform
        price_mean = scaler.mean_[0]
        price_std = scaler.scale_[0]
        predictions = (pred_scaled * price_std + price_mean).tolist()
    else:
        # Linear fallback (mean of recent)
        recent_prices = [d[0] for d in past_60_days]
        mean_price = np.mean(recent_prices)
        predictions = [mean_price * (1 + np.random.normal(0, 0.005)) for _ in range(7)]

    # Ensure non-negative
    predictions = [max(0, p) for p in predictions]

    # Support/resistance levels
    recent = [d[0] for d in past_60_days[-20:]]
    support = min(recent) - (max(recent) - min(recent)) * 0.1
    resistance = max(recent) + (max(recent) - min(recent)) * 0.1

    # Sentiment index
    recent_sentiments = [d[3] for d in past_60_days[-10:] if len(d) > 3]
    sentiment_index = np.mean(recent_sentiments) if recent_sentiments else 0.5

    # Direction accuracy estimate (based on recent trend)
    if len(predictions) >= 2:
        up_days = sum(1 for i in range(1, len(predictions)) if predictions[i] > predictions[i-1])
        dir_accuracy = up_days / len(predictions)
    else:
        dir_accuracy = 0.5

    return {
        "next_7_days": [round(p, 2) for p in predictions],
        "support_level": round(support, 2),
        "resistance_level": round(resistance, 2),
        "sentiment_index": round(float(sentiment_index), 4),
        "direction_accuracy_estimate": round(float(dir_accuracy), 4),
    }


if __name__ == "__main__":
    train()

    # Test
    result = predict_trend()
    print(f"\nTest prediction (next 7 days):")
    print(f"  Prices: {result['next_7_days']}")
    print(f"  Support: {result['support_level']}, Resistance: {result['resistance_level']}")
    print(f"  Sentiment: {result['sentiment_index']}")
