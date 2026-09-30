"""
Robust model loader module for the AI Empowerment Platform.
Caches loaded models in a global dict using lazy loading,
with retry logic, graceful missing-file handling, and
support for joblib, pickle, CSV, and PyTorch .pth files.
"""
from __future__ import annotations

import os
import pickle
import logging
import time
import threading
from typing import Any, Dict, Optional

import pandas as pd
import torch

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR: str = os.path.join(BASE_DIR, "models")

# ---------------------------------------------------------------------------
# Global cache
# ---------------------------------------------------------------------------

_cache: Dict[str, Any] = {}
_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _get_lock(name: str) -> threading.Lock:
    """Return a per-model lock, creating it atomically if needed."""
    with _locks_guard:
        return _locks.setdefault(name, threading.Lock())

# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

def _retry_load(
    loader_fn: Any,
    filepath: str,
    description: str,
    max_attempts: int = 3,
    base_delay: float = 0.5,
) -> Any:
    """
    Attempt to load a model with exponential backoff.

    Parameters
    ----------
    loader_fn : callable
        Zero-argument callable that performs the actual load.
    filepath : str
        Full path to the file (used only for logging).
    description : str
        Human-readable description of what is being loaded.
    max_attempts : int, default 3
        Number of retry attempts.
    base_delay : float, default 0.5
        Initial delay in seconds before the first retry (doubles each attempt).

    Returns
    -------
    Any
        The loaded object, or None if all attempts fail.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return loader_fn()
        except (FileNotFoundError, ModuleNotFoundError, ImportError,
                pickle.UnpicklingError, RuntimeError, OSError, EOFError) as exc:
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                log.warning(
                    "Attempt %d/%d failed loading %s (%s). Retrying in %.1fs …",
                    attempt, max_attempts, description, exc, delay,
                )
                time.sleep(delay)
            else:
                log.warning(
                    "All %d attempts failed loading %s (%s). Returning None.",
                    max_attempts, description, exc,
                )
    return None

# ---------------------------------------------------------------------------
# File-type specific loaders
# ---------------------------------------------------------------------------

def _load_joblib(filepath: str) -> Any:
    """Load a joblib file."""
    import joblib
    return joblib.load(filepath)


def _load_pickle(filepath: str) -> Any:
    """Load a pickle file, falling back to joblib.

    Some ``.pkl`` artifacts in this repo were written with ``joblib.dump``
    (notably scikit-learn scalers/models), which produces a stream that plain
    :mod:`pickle` cannot read (raises ``invalid load key``). Try :mod:`pickle`
    first, then fall back to :mod:`joblib`.
    """
    try:
        with open(filepath, "rb") as fh:
            return pickle.load(fh)
    except Exception as pickle_exc:
        try:
            import joblib
            return joblib.load(filepath)
        except Exception:
            raise pickle_exc


def _load_pytorch(filepath: str, map_location: Optional[str] = None) -> Dict[str, Any]:
    """Load a PyTorch ``.pth`` state-dict file.

    Prefer ``weights_only=True`` (safe: no arbitrary code execution via pickle).
    Fall back to ``weights_only=False`` only for legacy files that embed
    non-tensor metadata; such files are trusted (shipped with the repo).
    """
    loc = map_location or ("cuda" if torch.cuda.is_available() else "cpu")
    try:
        return torch.load(filepath, map_location=loc, weights_only=True)
    except Exception:
        log.warning(
            "weights_only=True failed for %s; falling back to weights_only=False", filepath,
        )
        return torch.load(filepath, map_location=loc, weights_only=False)


def _load_csv(filepath: str) -> pd.DataFrame:
    """Load a CSV file as a pandas DataFrame."""
    return pd.read_csv(filepath)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_model(name: str) -> Any:
    """
    Return a cached model by logical *name*, loading it lazily on first call.

    The module maintains a built-in mapping of well-known model names to their
    corresponding file paths on disk. If *name* is not recognised, ``None`` is
    returned and a warning is logged.

    Parameters
    ----------
    name : str
        Logical model name (e.g. ``"medical"``, ``"diabetes_dnn"``).

    Returns
    -------
    Any
        The loaded model object, or ``None`` if the file is missing or
        all loading attempts failed.
    """
    if name in _cache:
        return _cache[name]

    with _get_lock(name):
        # Double-checked locking: another thread may have loaded it meanwhile.
        if name in _cache:
            return _cache[name]
        return _load_model_uncached(name)


def _load_model_uncached(name: str) -> Any:
    """Load a model by name (no cache check, no lock) — called under the per-name lock."""
    filepath: Optional[str] = None
    loader_fn: Any = None
    description: str = name

    # ── 1. Check built-in mapping ──────────────────────────────────────
    mapping = _get_file_mapping()
    if name in mapping:
        info = mapping[name]
        filepath = os.path.join(MODELS_DIR, info["filename"])
        kind = info.get("kind", "joblib")

        if kind == "joblib":
            loader_fn = lambda fp=filepath: _load_joblib(fp)                        # noqa: E731
        elif kind == "pickle":
            loader_fn = lambda fp=filepath: _load_pickle(fp)                        # noqa: E731
        elif kind == "csv":
            loader_fn = lambda fp=filepath: _load_csv(fp)                           # noqa: E731
        elif kind == "pytorch":
            loader_fn = lambda fp=filepath: _load_pytorch(fp)                       # noqa: E731
        else:
            log.warning("Unknown file kind '%s' for model '%s'", kind, name)
            return None
    else:
        log.warning("Unknown model name '%s' – no file mapping registered.", name)
        return None

    # ── 2. Early exit if file does not exist ────────────────────────────
    if not os.path.isfile(filepath):
        log.warning("Model file not found: %s (for '%s')", filepath, name)
        _cache[name] = None
        return None

    # ── 3. Load with retry ─────────────────────────────────────────────
    result = _retry_load(loader_fn, filepath, description)
    _cache[name] = result
    return result


def get_models_dict() -> Dict[str, Any]:
    """
    Return the internal model cache dictionary.

    Calling this function does **not** trigger any lazy loading; it merely
    exposes whatever models have already been requested via :func:`get_model`.

    Returns
    -------
    Dict[str, Any]
        The dict mapping model names to their loaded objects (or ``None``
        if loading failed).
    """
    return _cache


def warmup_models(names: Optional[list[str]] = None) -> Dict[str, bool]:
    """
    Pre-load (warm up) a list of models.

    Parameters
    ----------
    names : list[str] or None
        Model names to warm up. If ``None``, all models defined in the
        built-in mapping are loaded.

    Returns
    -------
    Dict[str, bool]
        Mapping of model name → whether it loaded successfully.
    """
    if names is None:
        names = list(_get_file_mapping().keys())

    status: Dict[str, bool] = {}
    for name in names:
        result = get_model(name)
        status[name] = result is not None
        log.info("Warmup %s: %s", name, "✅" if result is not None else "❌")
    return status

# ---------------------------------------------------------------------------
# Built-in file mapping
# ---------------------------------------------------------------------------

def _get_file_mapping() -> Dict[str, Dict[str, str]]:
    """
    Return the authoritative mapping of logical model names to file info.

    The returned dict has the structure::

        {"medical": {"filename": "medical_model.joblib", "kind": "joblib"}, …}
    """
    return {
        # ---- Core V1 ----
        "medical":              {"filename": "medical_model.joblib",              "kind": "joblib"},
        "medical_vec":          {"filename": "medical_vectorizer.joblib",         "kind": "joblib"},
        "medical_label":        {"filename": "medical_label_encoder.joblib",      "kind": "joblib"},
        "finance":              {"filename": "finance_model.joblib",              "kind": "joblib"},
        "finance_anomaly":      {"filename": "finance_anomaly_model.joblib",      "kind": "joblib"},
        "finance_scaler":       {"filename": "finance_scaler.joblib",             "kind": "joblib"},
        "environment":          {"filename": "environment_model.joblib",          "kind": "joblib"},
        "env_scaler":           {"filename": "environment_scaler.joblib",         "kind": "joblib"},

        # ---- V2 Medical ----
        "drug_vec":             {"filename": "drug_vectorizer.joblib",            "kind": "joblib"},
        "drug_sim":             {"filename": "drug_similarity_matrix.joblib",     "kind": "joblib"},
        "drug_features":        {"filename": "drug_features.joblib",              "kind": "joblib"},
        "drug_database":        {"filename": "drug_database.csv",                 "kind": "csv"},
        "epidemic":             {"filename": "epidemic_models.joblib",            "kind": "joblib"},
        "health_scoring":       {"filename": "health_scoring_model.joblib",       "kind": "joblib"},
        "health_scaler":        {"filename": "health_scaler.joblib",              "kind": "joblib"},
        "complication":         {"filename": "complication_model.joblib",         "kind": "joblib"},
        "resource":             {"filename": "resource_model.joblib",             "kind": "joblib"},
        "resource_scaler":      {"filename": "resource_scaler.joblib",            "kind": "joblib"},
        "resource_meta":        {"filename": "resource_metadata.joblib",          "kind": "joblib"},
        "search_vec":           {"filename": "search_vectorizer.joblib",          "kind": "joblib"},
        "search_tfidf":         {"filename": "search_tfidf_matrix.joblib",        "kind": "joblib"},
        "search_records":       {"filename": "search_records.joblib",             "kind": "joblib"},

        # ---- V2 Finance ----
        "loan":                 {"filename": "loan_model.joblib",                 "kind": "joblib"},
        "loan_scaler":          {"filename": "loan_scaler.joblib",                "kind": "joblib"},
        "loan_features":        {"filename": "loan_features.joblib",              "kind": "joblib"},
        "kmeans":               {"filename": "kmeans_model.joblib",               "kind": "joblib"},
        "pca":                  {"filename": "pca_model.joblib",                  "kind": "joblib"},
        "segment_profiles":     {"filename": "segment_profiles.joblib",           "kind": "joblib"},
        "asset_data":           {"filename": "asset_data.joblib",                 "kind": "joblib"},
        "fraud_ensemble":       {"filename": "fraud_ensemble.joblib",             "kind": "joblib"},
        "fraud_scaler":         {"filename": "fraud_scaler.joblib",               "kind": "joblib"},
        "financial_health":     {"filename": "financial_health_model.joblib",     "kind": "joblib"},
        "health_dims":          {"filename": "health_dimension_weights.joblib",   "kind": "joblib"},
        "market_scaler":        {"filename": "market_scaler.joblib",              "kind": "joblib"},
        "trend_baseline":       {"filename": "trend_baseline.joblib",             "kind": "joblib"},

        # ---- V2 Environment ----
        "nmf":                  {"filename": "nmf_model.joblib",                  "kind": "joblib"},
        "pca_env":              {"filename": "pca_model_env.joblib",              "kind": "joblib"},
        "source_profiles":      {"filename": "source_profiles.joblib",            "kind": "joblib"},
        "aqi_forecast":         {"filename": "aqi_forecast_model.joblib",         "kind": "joblib"},
        "aqi_scaler":           {"filename": "aqi_forecast_scaler.joblib",        "kind": "joblib"},
        "aqi_encoder":          {"filename": "aqi_level_encoder.joblib",          "kind": "joblib"},
        "carbon":               {"filename": "carbon_model.joblib",               "kind": "joblib"},
        "carbon_scaler":        {"filename": "carbon_scaler.joblib",              "kind": "joblib"},

        # ---- V2 Traffic ----
        "traffic":              {"filename": "traffic_model.joblib",              "kind": "joblib"},
        "traffic_scaler":       {"filename": "traffic_scaler.joblib",             "kind": "joblib"},
        "traffic_anomaly":      {"filename": "traffic_anomaly_model.joblib",      "kind": "joblib"},
        "traffic_features":     {"filename": "traffic_features.joblib",           "kind": "joblib"},

        # ---- V5 Traffic 增强模型 (拥堵预测/异常检测/天气/事故/场景仿真) ----
        "traffic_congestion":           {"filename": "traffic_congestion_model.pkl",            "kind": "pickle"},
        "traffic_congestion_scaler":    {"filename": "traffic_congestion_scaler.pkl",           "kind": "pickle"},
        "traffic_congestion_encoders":  {"filename": "traffic_congestion_encoders.pkl",         "kind": "pickle"},
        "traffic_anomaly_iforest":      {"filename": "traffic_anomaly_iforest.pkl",             "kind": "pickle"},
        "traffic_anomaly_scaler":       {"filename": "traffic_anomaly_scaler.pkl",              "kind": "pickle"},
        "traffic_anomaly_threshold":    {"filename": "traffic_anomaly_threshold.pkl",            "kind": "pickle"},
        "traffic_weather":              {"filename": "traffic_weather_model.pkl",                "kind": "pickle"},
        "traffic_weather_scaler":       {"filename": "traffic_weather_scaler.pkl",               "kind": "pickle"},
        "traffic_weather_encoders":     {"filename": "traffic_weather_encoders.pkl",             "kind": "pickle"},
        "traffic_accident_impact":      {"filename": "traffic_accident_impact_model.pkl",        "kind": "pickle"},
        "traffic_accident_impact_scaler":{"filename": "traffic_accident_impact_scaler.pkl",      "kind": "pickle"},
        "traffic_scenario":             {"filename": "traffic_scenario_model.pkl",               "kind": "pickle"},
        "traffic_scenario_scaler":      {"filename": "traffic_scenario_scaler.pkl",              "kind": "pickle"},
        "traffic_scenario_encoders":    {"filename": "traffic_scenario_encoders.pkl",            "kind": "pickle"},

        # ---- V4 V4 Enhanced Models (Energy/Forum/Dev/Traffic/Finance/Environment) ----
        "energy_load_lstm":            {"filename": "energy_load_lstm.pth",                    "kind": "pytorch"},
        "energy_load_scaler":          {"filename": "energy_load_scaler.pkl",                   "kind": "pickle"},
        "energy_device_failure":       {"filename": "energy_device_failure.pkl",                "kind": "pickle"},
        "forum_nlp_pipeline":          {"filename": "forum_nlp_pipeline.pkl",                   "kind": "pickle"},
        "learning_path_rec":           {"filename": "learning_path_recommender.pkl",             "kind": "pickle"},
        "development_trend_analyzer":  {"filename": "development_trend_analyzer.pkl",            "kind": "pickle"},
        "traffic_accident":            {"filename": "traffic_accident_risk.pkl",                 "kind": "pickle"},
        "finance_churn":               {"filename": "finance_churn_prediction.pkl",              "kind": "pickle"},
        "env_extreme_weather":         {"filename": "environment_extreme_weather.pkl",            "kind": "pickle"},

        # ---- V3 Medical (Real-Data Models) ----
        "diabetes_risk":            {"filename": "diabetes_risk_model.joblib",         "kind": "joblib"},
        "diabetes_risk_scaler":     {"filename": "diabetes_risk_scaler.joblib",        "kind": "joblib"},
        "diabetes_risk_info":       {"filename": "diabetes_risk_info.joblib",          "kind": "joblib"},
        "glucose_forecast":         {"filename": "glucose_forecast_model.joblib",      "kind": "joblib"},
        "glucose_forecast_scaler":  {"filename": "glucose_forecast_scaler.joblib",     "kind": "joblib"},
        "glucose_forecast_info":    {"filename": "glucose_forecast_info.joblib",       "kind": "joblib"},

        # ---- PyTorch DNN ----
        "diabetes_dnn_model":       {"filename": "diabetes_dnn_model.pth",             "kind": "pytorch"},
        "diabetes_ensemble":        {"filename": "diabetes_ensemble.pth",              "kind": "pytorch"},
        "glucose_lstm_30min":       {"filename": "glucose_lstm_30min.pth",             "kind": "pytorch"},
        "glucose_lstm_30min_bilstm":{"filename": "glucose_lstm_30min_bilstm.pth",     "kind": "pytorch"},
        "glucose_lstm_60min":       {"filename": "glucose_lstm_60min.pth",             "kind": "pytorch"},
        "lstm_model":               {"filename": "lstm_model.pth",                     "kind": "pytorch"},
        # ---- CT Brain (CQ500 v3) ----
        "brain_ct_v3":              {"filename": "brain_ct_model_v3.joblib",          "kind": "joblib"},
        "brain_ct_info_v3":         {"filename": "brain_ct_info_v3.joblib",           "kind": "joblib"},
        "brain_ct_3d_ae_v3":        {"filename": "brain_ct_3d_ae_v3.pth",              "kind": "pytorch"},
        "brain_ct_scaler_v3":       {"filename": "brain_ct_scaler_v3.joblib",          "kind": "joblib"},
        # NOTE: "brain_ct_3d_ae" (v1) 已被 v3 取代，模型文件已归档至
        # models_archive_v1/，且无任何路由引用，故移除该失效映射。

        # ---- CQ500 脑CT伪影分割 (UNet3D) ----
        "artifact_unet":           {"filename": "best_artifact_unet.pth",             "kind": "pytorch"},

        # ---- CT 三维分割 (UNet3D, 替换阈值分割) ----
        "ct_seg_unet":             {"filename": "ct_seg_unet.pth",                     "kind": "pytorch"},

        # ---- CT 金属伪影检测 (UNet3D, 替换HU阈值) ----
        "ct_metal_unet":           {"filename": "ct_metal_unet.pth",                   "kind": "pytorch"},

        # ---- CT 诊断报告分类器 (3D CNN, 替换模板报告) ----
        "ct_report_classifier":    {"filename": "ct_report_classifier.pth",             "kind": "pytorch"},
    }


# ---------------------------------------------------------------------------
# Convenience: register extra models at runtime
# ---------------------------------------------------------------------------

# Internal mutable copy so callers can extend the mapping at runtime if needed.
_extra_mapping: Dict[str, Dict[str, str]] = {}


def register_model(name: str, filename: str, kind: str = "joblib") -> None:
    """
    Register an additional model to be loadable via :func:`get_model`.

    Parameters
    ----------
    name : str
        Logical name used to retrieve the model.
    filename : str
        File name (relative to ``MODELS_DIR``).
    kind : str, default ``"joblib"``
        One of ``"joblib"``, ``"pickle"``, ``"csv"``, ``"pytorch"``.
    """
    if kind not in {"joblib", "pickle", "csv", "pytorch"}:
        log.warning("Unsupported kind '%s' – falling back to 'joblib'", kind)
        kind = "joblib"
    _extra_mapping[name] = {"filename": filename, "kind": kind}


def _get_file_mapping_combined() -> Dict[str, Dict[str, str]]:
    """Built-in mapping merged with runtime-registered extras."""
    base = _original_file_mapping()
    base.update(_extra_mapping)
    return base


# Save original before monkey-patch
_original_file_mapping = _get_file_mapping
_get_file_mapping = _get_file_mapping_combined  # noqa: E305
