"""
Pollution Source Apportionment - PCA + NMF
Synthetic data generation and model training
"""
import numpy as np
from sklearn.decomposition import PCA, NMF
from sklearn.preprocessing import StandardScaler
import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def train():
    print("=" * 60)
    print("Training Pollution Source Apportionment (PCA + NMF)")
    print("=" * 60)
    np.random.seed(42)
    n_samples = 1000
    source_profiles = np.array([
        [0.35, 0.25, 0.10, 0.15, 0.05, 0.10],
        [0.20, 0.30, 0.25, 0.10, 0.05, 0.10],
        [0.10, 0.05, 0.35, 0.25, 0.10, 0.15],
        [0.15, 0.20, 0.10, 0.30, 0.10, 0.15],
        [0.10, 0.05, 0.10, 0.10, 0.20, 0.45],
    ])
    source_weights = np.random.dirichlet(np.ones(5), n_samples)
    pollutant_data = source_weights @ source_profiles
    noise = np.random.normal(0, 0.02, pollutant_data.shape)
    pollutant_data = np.clip(pollutant_data + noise, 0, 1)

    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(pollutant_data)

    pca = PCA(n_components=4, random_state=42)
    pca_result = pca.fit_transform(data_scaled)
    print("PCA explained variance:", pca.explained_variance_ratio_.cumsum())

    nmf = NMF(n_components=5, init="random", random_state=42)
    w = nmf.fit_transform(np.maximum(pollutant_data, 0))
    h = nmf.components_
    print("NMF reconstruction error:", nmf.reconstruction_err_)

    source_labels = ["工业排放", "交通尾气", "扬尘污染", "生活排放", "自然源"]
    source_profiles_data = {
        "names": source_labels,
        "profiles": h.tolist(),
        "pollutants": ["pm25", "pm10", "so2", "no2", "co", "o3"]
    }

    joblib.dump(nmf, os.path.join(BASE_DIR, "nmf_model.joblib"))
    joblib.dump(pca, os.path.join(BASE_DIR, "pca_model_env.joblib"))
    joblib.dump(source_profiles_data, os.path.join(BASE_DIR, "source_profiles.joblib"))
    print("Models saved to", BASE_DIR)

if __name__ == "__main__":
    train()
