"""
Brain CT Abnormality Detection Model
====================================
Unsupervised anomaly detection on brain CT scans using:
  - SimpleITK for DICOM/MHD volume reading
  - Pre-trained ResNet18 for per-slice feature extraction
  - Mahalanobis distance for anomaly scoring
  - Multiple windowing for comprehensive analysis

Generates: brain_ct_model.joblib, brain_ct_info.joblib
"""

import os
import sys
import numpy as np
import joblib
from collections import OrderedDict
from scipy.spatial.distance import mahalanobis
from scipy import ndimage
import warnings
warnings.filterwarnings('ignore')

import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from sklearn.decomposition import PCA

import SimpleITK as sitk

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
CT_DIR1 = r"D:\东软实习\CQ500CT0 CQ500CT0\Unknown Study\CT Plain"
CT_DIR2 = r"D:\东软实习\simpleitk\data\CT Plain"
MHD_PATH = r"D:\东软实习\simpleitk\data\mhd"

WINDOWS = OrderedDict([
    ("brain",     {"center": 40,   "width": 80}),
    ("subdural",  {"center": 75,   "width": 200}),
    ("bone",      {"center": 300,  "width": 1500}),
])

IMG_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

np.random.seed(42)
torch.manual_seed(42)
if torch.cuda.is_available():
    torch.cuda.manual_seed(42)


# ---------------------------------------------------------------------------
# Logging helper (no Unicode)
# ---------------------------------------------------------------------------
def log(msg):
    print(f"[BrainCT] {msg}")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Windowing
# ---------------------------------------------------------------------------
def apply_window(volume: np.ndarray, center: float, width: float) -> np.ndarray:
    """Apply CT windowing: clip HU values to [center-width/2, center+width/2]."""
    half = width / 2.0
    low = center - half
    high = center + half
    return np.clip(volume.astype(np.float32), low, high)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_dicom_series(directory: str) -> np.ndarray:
    """Load a DICOM series from a directory. Returns (Z, H, W) numpy array."""
    if not os.path.isdir(directory):
        log(f"  Directory not found: {directory}")
        return None
    try:
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(directory)
        if not dicom_names:
            log(f"  No DICOM files in {directory}")
            return None
        log(f"  Found {len(dicom_names)} DICOM files in {directory}")
        img = sitk.ReadImage(dicom_names)
        arr = sitk.GetArrayFromImage(img).astype(np.float32)
        log(f"  Loaded volume shape={arr.shape}, HU range=[{arr.min():.0f}, {arr.max():.0f}]")
        return arr
    except Exception as e:
        log(f"  Error loading DICOM series: {e}")
        return None


def load_mhd_volume(mhd_file: str) -> np.ndarray:
    """Load a 3D volume from MHD+RAW pair."""
    if not os.path.isfile(mhd_file):
        log(f"  MHD file not found: {mhd_file}")
        return None
    try:
        # Change to the directory so the relative raw path resolves
        saved_cwd = os.getcwd()
        os.chdir(os.path.dirname(mhd_file))
        img = sitk.ReadImage(os.path.basename(mhd_file))
        os.chdir(saved_cwd)
        arr = sitk.GetArrayFromImage(img).astype(np.float32)
        log(f"  Loaded MHD volume shape={arr.shape}, HU range=[{arr.min():.0f}, {arr.max():.0f}]")
        return arr
    except Exception as e:
        log(f"  Error loading MHD volume: {e}")
        return None


def load_nifti_volume(nii_file: str) -> np.ndarray:
    """Load a 3D volume from NIfTI file."""
    if not os.path.isfile(nii_file):
        log(f"  NIfTI file not found: {nii_file}")
        return None
    try:
        saved_cwd = os.getcwd()
        os.chdir(os.path.dirname(nii_file))
        img = sitk.ReadImage(os.path.basename(nii_file))
        os.chdir(saved_cwd)
        arr = sitk.GetArrayFromImage(img).astype(np.float32)
        log(f"  Loaded NIfTI volume shape={arr.shape}, HU range=[{arr.min():.0f}, {arr.max():.0f}]")
        return arr
    except Exception as e:
        log(f"  Error loading NIfTI volume: {e}")
        return None


# ---------------------------------------------------------------------------
# Feature extraction setup
# ---------------------------------------------------------------------------
class ResNetFeatureExtractor(nn.Module):
    """ResNet18 truncated at avgpool to produce 512-d features."""
    def __init__(self):
        super().__init__()
        backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        self.features = nn.Sequential(*list(backbone.children())[:-2])  # up to last conv
        self.pool = nn.AdaptiveAvgPool2d((1, 1))

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x)
        return x.view(x.size(0), -1)


def build_extractor():
    model = ResNetFeatureExtractor().to(DEVICE).eval()
    return model


def preprocess_slice(slice_2d: np.ndarray, img_size: int = IMG_SIZE) -> torch.Tensor:
    """
    Normalize a windowed slice to [0,1], resize to img_size, repeat 3x for RGB.
    Returns (1, 3, H, W) tensor.
    """
    # Resize
    zoom = img_size / slice_2d.shape[0]
    resized = ndimage.zoom(slice_2d, zoom, order=1)
    # Normalize to [0, 1]
    mn, mx = resized.min(), resized.max()
    if mx - mn > 1e-6:
        normed = (resized - mn) / (mx - mn)
    else:
        normed = np.zeros_like(resized)
    # Repeat grayscale 3x for RGB, add batch dim
    tensor = torch.from_numpy(normed).float().unsqueeze(0).repeat(3, 1, 1).unsqueeze(0)
    # imagenet normalization
    tensor = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])(tensor)
    return tensor.to(DEVICE)


# ---------------------------------------------------------------------------
# Slice feature extraction
# ---------------------------------------------------------------------------
def extract_slice_features(volume: np.ndarray, extractor, window_name: str = "brain"):
    """
    Extract per-slice features for a given windowing.
    Returns (num_slices, 512) numpy array.
    """
    w = WINDOWS[window_name]
    windowed = apply_window(volume, w["center"], w["width"])
    features = []
    with torch.no_grad():
        for z in range(windowed.shape[0]):
            sl = windowed[z]
            tensor = preprocess_slice(sl)
            feat = extractor(tensor).cpu().numpy().flatten()
            features.append(feat)
    return np.array(features)


def extract_volume_features(volume: np.ndarray, extractor) -> dict:
    """
    Extract features for all windowings from a volume.
    Returns dict of {window_name: (num_slices, 512) features}
    """
    result = {}
    for wname in WINDOWS:
        result[wname] = extract_slice_features(volume, extractor, wname)
    return result


# ---------------------------------------------------------------------------
# HU statistics per slice
# ---------------------------------------------------------------------------
def compute_hu_statistics(volume: np.ndarray) -> np.ndarray:
    """
    Compute HU statistics per slice: mean, std, min, max.
    Returns (num_slices, 4) array.
    """
    stats = []
    for z in range(volume.shape[0]):
        sl = volume[z].flatten()
        # Exclude background (air outside head)
        head = sl[sl > -500]
        if len(head) > 0:
            stats.append([head.mean(), head.std(), head.min(), head.max()])
        else:
            stats.append([0, 0, -3024, 3071])
    return np.array(stats)


# ---------------------------------------------------------------------------
# Symmetry analysis
# ---------------------------------------------------------------------------
def compute_symmetry_features(volume: np.ndarray, window_name: str = "brain") -> np.ndarray:
    """
    Compute left-right symmetry difference per slice.
    Returns (num_slices, 1) array of asymmetry scores.
    """
    w = WINDOWS[window_name]
    windowed = apply_window(volume, w["center"], w["width"])
    scores = []
    for z in range(windowed.shape[0]):
        sl = windowed[z]
        h, w = sl.shape
        mid = w // 2
        left = sl[:, :mid]
        right = np.fliplr(sl[:, mid:])  # flip to match left orientation
        # Trim to same width
        min_w = min(left.shape[1], right.shape[1])
        left = left[:, :min_w]
        right = right[:, :min_w]
        # MSE difference
        diff = ((left - right) ** 2).mean()
        scores.append(diff)
    return np.array(scores).reshape(-1, 1)


# ---------------------------------------------------------------------------
# Training: build anomaly detection model
# ---------------------------------------------------------------------------
def train_model(volumes: list):
    """
    Train the anomaly detection model.
    
    Args:
        volumes: list of (name, numpy_volume) tuples
    
    Returns:
        dict with model parameters
    """
    log(f"Building feature extractor on {DEVICE}...")
    extractor = build_extractor()
    
    all_features = {}  # window_name -> list of feature vectors
    for wname in WINDOWS:
        all_features[wname] = []
    
    hu_stats_list = []
    symmetry_list = []
    
    for name, vol in volumes:
        log(f"\nProcessing volume: {name}")
        log(f"  Volume shape: {vol.shape}")
        
        # Extract features for each window
        feat_dict = extract_volume_features(vol, extractor)
        for wname in WINDOWS:
            all_features[wname].append(feat_dict[wname])
            log(f"  {wname} window: {feat_dict[wname].shape[0]} slices, {feat_dict[wname].shape[1]} features")
        
        # HU statistics
        hu_stats = compute_hu_statistics(vol)
        hu_stats_list.append(hu_stats)
        log(f"  HU stats mean: {hu_stats.mean(axis=0)}")
        
        # Symmetry
        sym = compute_symmetry_features(vol)
        symmetry_list.append(sym)
        log(f"  Symmetry mean: {sym.mean():.4f}")
    
    # Concatenate all features across volumes
    log("\nBuilding reference distribution...")
    model = {}
    
    for wname in WINDOWS:
        stacked = np.vstack(all_features[wname])
        n_samples, n_features = stacked.shape
        log(f"  {wname} total samples: {stacked.shape[0]}")
        
        # Step 1: Apply PCA to reduce dimensionality (preserve 95% variance)
        n_components = min(n_samples - 1, n_features)
        log(f"  Applying PCA (max components={n_components})...")
        pca = PCA(n_components=n_components, whiten=False)
        stacked_pca = pca.fit_transform(stacked)
        log(f"  PCA components retained: {stacked_pca.shape[1]}, "
            f"explained variance ratio: {pca.explained_variance_ratio_.sum():.4f}")
        
        # Step 2: Compute mean and covariance in PCA space
        mean_vec = np.mean(stacked_pca, axis=0)
        centered = stacked_pca - mean_vec
        cov = np.cov(centered, rowvar=False)
        
        # Shrinkage/regularization for the covariance
        # Use a convex combination with identity matrix
        shrinkage = 0.1
        cov_reg = (1 - shrinkage) * cov + shrinkage * np.eye(cov.shape[0]) * np.mean(np.diag(cov))
        
        try:
            inv_cov = np.linalg.inv(cov_reg)
        except np.linalg.LinAlgError:
            log(f"  Covariance still singular for {wname}, using pseudoinverse")
            inv_cov = np.linalg.pinv(cov_reg)
        
        # Compute Mahalanobis distances in PCA space for reference
        distances = np.array([
            mahalanobis(f, mean_vec, inv_cov) for f in stacked_pca
        ])
        
        # Scale to approximate chi-squared distribution (z-score)
        dist_mean = float(np.mean(distances))
        dist_std = float(np.std(distances))
        
        model[f"{wname}_mean"] = mean_vec
        model[f"{wname}_inv_cov"] = inv_cov
        model[f"{wname}_pca"] = pca
        model[f"{wname}_dist_mean"] = dist_mean
        model[f"{wname}_dist_std"] = dist_std
        model[f"{wname}_dist_max"] = float(np.max(distances))
        model[f"{wname}_dist_p95"] = float(np.percentile(distances, 95))
        
        log(f"  Distance stats - mean={dist_mean:.4f}, "
            f"std={dist_std:.4f}, "
            f"p95={model[f'{wname}_dist_p95']:.4f}")
    
    # Aggregate HU statistics
    all_hu = np.vstack(hu_stats_list)
    model["hu_mean_mean"] = float(np.mean(all_hu[:, 0]))
    model["hu_std_mean"] = float(np.mean(all_hu[:, 1]))
    model["hu_min_mean"] = float(np.mean(all_hu[:, 2]))
    model["hu_max_mean"] = float(np.mean(all_hu[:, 3]))
    
    # Aggregate symmetry
    all_sym = np.vstack(symmetry_list)
    model["symmetry_mean"] = float(np.mean(all_sym))
    model["symmetry_std"] = float(np.std(all_sym))
    model["symmetry_p95"] = float(np.percentile(all_sym, 95))
    
    log(f"\nHU reference - mean: {model['hu_mean_mean']:.1f}, "
        f"std: {model['hu_std_mean']:.1f}")
    log(f"Symmetry reference - mean: {model['symmetry_mean']:.4f}, "
        f"std: {model['symmetry_std']:.4f}")
    
    # Store window config
    model["windows"] = dict(WINDOWS)
    
    return model


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
def analyze_volume(volume: np.ndarray, model: dict, extractor=None):
    """
    Run full inference on a CT volume.
    
    Args:
        volume: (Z, H, W) numpy array of HU values
        model: model parameters dict from train_model()
        extractor: ResNetFeatureExtractor instance
    
    Returns:
        dict with analysis results
    """
    if extractor is None:
        extractor = build_extractor()
    
    num_slices = volume.shape[0]
    
    # Per-slice anomaly scores for each window
    per_slice = {}
    per_slice_anomaly = {}
    
    for wname in WINDOWS:
        w = model["windows"][wname]
        features = extract_slice_features(volume, extractor, wname)
        
        # Transform through PCA
        pca = model[f"{wname}_pca"]
        features_pca = pca.transform(features)
        
        mean_vec = model[f"{wname}_mean"]
        inv_cov = model[f"{wname}_inv_cov"]
        
        scores = []
        for f in features_pca:
            d = mahalanobis(f, mean_vec, inv_cov)
            scores.append(float(d))
        scores = np.array(scores)
        
        # Normalize scores: z-score relative to reference distribution
        ref_mean = model[f"{wname}_dist_mean"]
        ref_std = model[f"{wname}_dist_std"]
        zscores = (scores - ref_mean) / max(ref_std, 1e-8)
        
        per_slice[wname] = scores.tolist()
        per_slice_anomaly[wname] = zscores.tolist()
    
    # Compute HU statistics
    hu_stats = compute_hu_statistics(volume)
    hu_mean = float(hu_stats[:, 0].mean())
    hu_std = float(hu_stats[:, 1].mean())
    hu_min = float(hu_stats[:, 2].min())
    hu_max = float(hu_stats[:, 3].max())
    
    # Entropy of HU distribution
    from scipy.stats import entropy
    hist, _ = np.histogram(volume[volume > -500], bins=64)
    hist_entropy = float(entropy(hist + 1e-10))
    
    # Symmetry analysis
    sym_scores = compute_symmetry_features(volume, "brain")
    avg_asymmetry = float(sym_scores.mean())
    max_asymmetry = float(sym_scores.max())
    
    # Composite anomaly score: average z-scores across windows
    all_anomaly = np.array([
        np.array(per_slice_anomaly[wname]).mean() for wname in WINDOWS
    ])
    avg_anomaly = float(all_anomaly.mean())
    max_anomaly = float(all_anomaly.max())
    
    # Aggregate assessment
    if avg_anomaly > 3.0:
        assessment = "abnormal"
    elif avg_anomaly > 1.5:
        assessment = "suspicious"
    else:
        assessment = "normal"
    
    # Abnormality probability (sigmoid of normalized score)
    prob = 1.0 / (1.0 + np.exp(-avg_anomaly))
    
    # Generate findings
    findings = []
    if avg_anomaly > 1.5:
        findings.append("Abnormal feature patterns detected across multiple windows")
    if max_asymmetry > model.get("symmetry_p95", 0.5) * 1.5:
        findings.append("Significant left-right asymmetry detected")
    if abs(hu_mean - model.get("hu_mean_mean", 35)) > 50:
        findings.append("Atypical HU distribution (mean deviates from reference)")
    
    for wname in WINDOWS:
        high_score_count = sum(1 for s in per_slice_anomaly[wname] if s > 2.0)
        if high_score_count > max(2, num_slices * 0.1):
            findings.append(f"{wname} window: {high_score_count}/{num_slices} slices show elevated anomaly scores")
    
    if not findings:
        findings.append("No significant abnormalities detected")
    
    # Slice-level detail
    top_anomaly_slices = []
    combined_anomaly = np.zeros(num_slices)
    for wname in WINDOWS:
        combined_anomaly += np.array(per_slice_anomaly[wname])
    combined_anomaly /= len(WINDOWS)
    
    # Report top 5 most anomalous slices
    top_indices = np.argsort(combined_anomaly)[-5:][::-1]
    for idx in top_indices:
        top_anomaly_slices.append({
            "slice": int(idx),
            "anomaly_score": float(combined_anomaly[idx]),
            "brain_window_zscore": per_slice_anomaly["brain"][idx],
            "hu_mean": float(hu_stats[idx, 0])
        })
    
    # Advice
    if assessment == "normal":
        advice = "CT scan appears normal. Routine follow-up as clinically indicated."
    elif assessment == "suspicious":
        advice = "CT scan shows some atypical features. Clinical correlation recommended."
    else:
        advice = "CT scan shows significant abnormalities. Urgent clinical review recommended."
    
    return {
        "assessment": assessment,
        "abnormality_score": round(prob, 4),
        "abnormality_zscore": round(avg_anomaly, 4),
        "findings": findings,
        "per_slice_analysis": {
            "total_slices": num_slices,
            "top_anomalous_slices": top_anomaly_slices,
            "brain_window_scores": {
                "min": round(min(per_slice_anomaly["brain"]), 4),
                "max": round(max(per_slice_anomaly["brain"]), 4),
                "mean": round(np.mean(per_slice_anomaly["brain"]), 4)
            }
        },
        "statistics": {
            "num_slices": num_slices,
            "dimensions": list(volume.shape[1:]),
            "hu_range": [round(hu_min, 1), round(hu_max, 1)],
            "hu_mean": round(hu_mean, 1),
            "hu_std": round(hu_std, 1),
            "hu_entropy": round(hist_entropy, 4),
            "symmetry_asymmetry": round(avg_asymmetry, 4),
            "max_asymmetry": round(max_asymmetry, 4)
        },
        "advice": advice
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log("=" * 60)
    log("Brain CT Anomaly Detection Model Training")
    log("=" * 60)
    
    # Load all available volumes
    volumes = []
    
    # 1. CQ500 DICOM series
    log("\n[1/4] Loading CQ500 DICOM series...")
    vol1 = load_dicom_series(CT_DIR1)
    if vol1 is not None:
        volumes.append(("CQ500_DICOM", vol1))
    
    # 2. SimpleITK data CT Plain (may be same data, but try anyway)
    log("\n[2/4] Loading SimpleITK CT Plain DICOM...")
    vol2 = load_dicom_series(CT_DIR2)
    if vol2 is not None:
        # Check if it's different from first
        if not volumes or not np.array_equal(vol2, volumes[0][1]):
            volumes.append(("SITK_DICOM", vol2))
        else:
            log("  (same as CQ500, skipping duplicate)")
    
    # 3. MHD volume
    log("\n[3/4] Loading MHD volume...")
    mhd_file = os.path.join(MHD_PATH, "1.mhd")
    vol3 = load_mhd_volume(mhd_file)
    if vol3 is not None:
        volumes.append(("MHD_Volume", vol3))
    
    # 4. NIfTI volume
    log("\n[4/4] Loading NIfTI volume...")
    nii_file = os.path.join(MHD_PATH, "result.nii.gz")
    vol4 = load_nifti_volume(nii_file)
    if vol4 is not None:
        volumes.append(("NIfTI_Volume", vol4))
    
    if not volumes:
        log("ERROR: No CT volumes loaded. Check data paths.")
        sys.exit(1)
    
    log(f"\nTotal volumes loaded: {len(volumes)}")
    for name, vol in volumes:
        log(f"  {name}: shape={vol.shape}, HU range=[{vol.min():.0f}, {vol.max():.0f}]")
    
    # Train model
    log("\n" + "=" * 60)
    log("Training anomaly detection model...")
    log("=" * 60)
    model = train_model(volumes)
    
    # Save model
    log("\n" + "=" * 60)
    log("Saving model files...")
    model_path = os.path.join(MODEL_DIR, "brain_ct_model.joblib")
    joblib.dump(model, model_path)
    log(f"  Model saved to: {model_path}")
    
    # Build and save model info
    model_info = {
        "name": "Brain CT Anomaly Detection",
        "version": "1.0.0",
        "description": "Unsupervised anomaly detection on brain CT using ResNet18 features + Mahalanobis distance",
        "windows": dict(WINDOWS),
        "num_volumes_trained": len(volumes),
        "volume_shapes": {name: list(vol.shape) for name, vol in volumes},
        "feature_dim": 512,
        "device": str(DEVICE),
        "backbone": "resnet18_imagenet1k_v1",
        "algorithm": "mahalanobis_distance",
        "hu_reference": {
            "mean": model["hu_mean_mean"],
            "std": model["hu_std_mean"]
        },
        "symmetry_reference": {
            "mean": model["symmetry_mean"],
            "std": model["symmetry_std"]
        }
    }
    
    info_path = os.path.join(MODEL_DIR, "brain_ct_info.joblib")
    joblib.dump(model_info, info_path)
    log(f"  Info saved to: {info_path}")
    
    # Test inference on the first volume
    log("\n" + "=" * 60)
    log("Running test inference on loaded data...")
    log("=" * 60)
    
    extractor = build_extractor()
    for name, vol in volumes[:1]:
        log(f"\nAnalyzing: {name}")
        result = analyze_volume(vol, model, extractor)
        log(f"  Assessment: {result['assessment']}")
        log(f"  Abnormality score: {result['abnormality_score']:.4f}")
        log(f"  Z-score: {result['abnormality_zscore']:.4f}")
        log(f"  Findings ({len(result['findings'])}):")
        for f in result['findings']:
            log(f"    - {f}")
        log(f"  Statistics:")
        for k, v in result['statistics'].items():
            log(f"    {k}: {v}")
        log(f"  Advice: {result['advice']}")
    
    log("\n" + "=" * 60)
    log("Training complete!")
    log("=" * 60)


if __name__ == "__main__":
    main()
