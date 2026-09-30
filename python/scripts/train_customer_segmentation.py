"""
Customer Segmentation: K-Means with PCA, automatic K via elbow method
Generates: kmeans_model.joblib, pca_model.joblib, segment_profiles.joblib
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import joblib
import os
import random

random.seed(42)
np.random.seed(42)


def generate_customers(n=2500):
    """Generate synthetic customer transaction data."""
    data = []

    # Define cluster centers (4-6 natural segments)
    segment_centers = [
        {"avg_amount": 50, "transaction_freq": 30, "type_distribution": 0.3, "active_hour": 12, "balance_volatility": 0.2},   # Regular shoppers
        {"avg_amount": 500, "transaction_freq": 5, "type_distribution": 0.6, "active_hour": 20, "balance_volatility": 0.5},  # Big spenders
        {"avg_amount": 200, "transaction_freq": 15, "type_distribution": 0.5, "active_hour": 9, "balance_volatility": 0.3},  # Mid-range
        {"avg_amount": 20, "transaction_freq": 50, "type_distribution": 0.2, "active_hour": 8, "balance_volatility": 0.1},   # High-frequency low-value
        {"avg_amount": 1000, "transaction_freq": 2, "type_distribution": 0.8, "active_hour": 22, "balance_volatility": 0.7}, # Premium rare
        {"avg_amount": 100, "transaction_freq": 8, "type_distribution": 0.4, "active_hour": 14, "balance_volatility": 0.1},  # Stable savers
    ]

    for i in range(n):
        center = random.choice(segment_centers)
        customer = {
            "avg_amount": max(1, center["avg_amount"] + np.random.normal(0, center["avg_amount"] * 0.3)),
            "transaction_freq": max(1, center["transaction_freq"] + np.random.normal(0, center["transaction_freq"] * 0.25)),
            "type_distribution": max(0, min(1, center["type_distribution"] + np.random.normal(0, 0.1))),
            "active_hour": max(0, min(23, center["active_hour"] + np.random.normal(0, 2))),
            "balance_volatility": max(0, min(1, center["balance_volatility"] + np.random.normal(0, 0.1))),
        }
        data.append(customer)

    df = pd.DataFrame(data)
    print(f"Generated {len(df)} customer records")
    return df


def train():
    print("=" * 60)
    print("Training Customer Segmentation Model")
    print("=" * 60)

    df = generate_customers(2500)
    feature_cols = ["avg_amount", "transaction_freq", "type_distribution", "active_hour", "balance_volatility"]
    X = df[feature_cols].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Elbow method to find optimal K
    inertias = []
    K_range = range(2, 10)
    for k in K_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)

    # Find elbow: choose k where inertia improvement drops below threshold
    k_optimal = 4
    if len(inertias) >= 3:
        diffs = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
        for idx, d in enumerate(diffs):
            if d < max(diffs) * 0.2:
                k_optimal = idx + 2
                break

    print(f"Optimal K = {k_optimal}")

    # Train final model
    kmeans = KMeans(n_clusters=k_optimal, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    # PCA for visualization
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    print(f"PCA explained variance ratio: {pca.explained_variance_ratio_}")

    # Generate segment profiles
    df["segment"] = labels
    segment_profiles = {}
    for seg_id in range(k_optimal):
        seg_data = df[df["segment"] == seg_id]
        profile = {
            "size": len(seg_data),
            "avg_amount": round(seg_data["avg_amount"].mean(), 2),
            "transaction_freq": round(seg_data["transaction_freq"].mean(), 2),
            "type_distribution": round(seg_data["type_distribution"].mean(), 3),
            "active_hour": round(seg_data["active_hour"].mean(), 1),
            "balance_volatility": round(seg_data["balance_volatility"].mean(), 3),
        }

        # Name the segment
        if profile["avg_amount"] > 500 and profile["transaction_freq"] < 8:
            name = "高端低频用户"
            desc = "高消费、低频次交易的高价值客户"
        elif profile["transaction_freq"] > 30 and profile["avg_amount"] < 80:
            name = "高频低额用户"
            desc = "频繁小额交易的活跃用户"
        elif profile["avg_amount"] > 200 and profile["transaction_freq"] > 10:
            name = "优质活跃用户"
            desc = "高消费高频次的核心优质客户"
        elif profile["balance_volatility"] < 0.2 and profile["transaction_freq"] < 15:
            name = "稳定型用户"
            desc = "消费习惯稳定的老客户"
        elif profile["avg_amount"] < 100 and profile["transaction_freq"] < 10:
            name = "潜力用户"
            desc = "消费频次和金额均较低但具有增长潜力的用户"
        else:
            name = f"混合型用户_{seg_id}"
            desc = "特征多元的普通用户"

        segment_profiles[int(seg_id)] = {
            "segment_name": name,
            "description": desc,
            "profile": profile,
        }
        print(f"  Segment {seg_id}: {name} ({profile['size']} users)")

    out_dir = os.path.dirname(__file__)
    joblib.dump(kmeans, os.path.join(out_dir, "kmeans_model.joblib"))
    joblib.dump(pca, os.path.join(out_dir, "pca_model.joblib"))
    joblib.dump({"scaler": scaler, "profiles": segment_profiles, "feature_cols": feature_cols, "k": k_optimal},
                os.path.join(out_dir, "segment_profiles.joblib"))
    print("Models saved.")


def predict_segment(user_features: dict):
    """Predict customer segment from features."""
    out_dir = os.path.dirname(__file__)
    kmeans = joblib.load(os.path.join(out_dir, "kmeans_model.joblib"))
    pca = joblib.load(os.path.join(out_dir, "pca_model.joblib"))
    meta = joblib.load(os.path.join(out_dir, "segment_profiles.joblib"))
    scaler = meta["scaler"]
    profiles = meta["profiles"]
    feature_cols = meta["feature_cols"]

    X = np.array([[user_features.get(f, 0) for f in feature_cols]])
    X_scaled = scaler.transform(X)

    seg_id = int(kmeans.predict(X_scaled)[0])
    distances = kmeans.transform(X_scaled)[0]
    # Confidence based on distance to nearest centroid vs second nearest
    sorted_dist = np.sort(distances)
    if len(sorted_dist) > 1:
        confidence = 1 - (sorted_dist[0] / (sorted_dist[1] + 1e-8))
    else:
        confidence = 1.0
    confidence = min(1, max(0, confidence))

    profile = profiles.get(seg_id, {"segment_name": f"未知_{seg_id}", "description": "未知分类"})

    return {
        "segment_id": seg_id,
        "segment_name": profile["segment_name"],
        "profile_description": profile["description"],
        "confidence": round(confidence, 4),
        "segment_profile": profile.get("profile", {}),
    }


if __name__ == "__main__":
    train()

    # Test
    test = {"avg_amount": 300, "transaction_freq": 12, "type_distribution": 0.5, "active_hour": 14, "balance_volatility": 0.3}
    result = predict_segment(test)
    print(f"\nTest: {test}")
    print(f"  Segment: {result['segment_name']} (ID={result['segment_id']})")
    print(f"  Confidence: {result['confidence']:.2%}")
