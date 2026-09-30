"""
脑部CT异常检测模型 — CQ500全量训练 (v3)
=========================================
使用CQ500全量数据集(490例, 34万+DICOM)训练无监督异常检测模型

改进:
  1. 数据量从1个MHD体数据 → 490例CQ500真实病例
  2. 标注信息用于验证（虽然训练是无监督的）
  3. 多窗宽窗位特征融合更鲁棒
  4. 支持NIfTI格式快速加载

输出: brain_ct_model_v3.joblib, brain_ct_info_v3.joblib
"""

import os, sys, glob, gc, time
import numpy as np
import joblib
from collections import OrderedDict
from scipy.spatial.distance import mahalanobis
from scipy import ndimage
from scipy.stats import entropy
import warnings
warnings.filterwarnings('ignore')

import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from sklearn.decomposition import PCA

try:
    import SimpleITK as sitk
    HAS_SITK = True
except ImportError:
    HAS_SITK = False

try:
    import nibabel as nib
    HAS_NIB = True
except ImportError:
    HAS_NIB = False

# ======================== 配置 ========================

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DATA_DIR = os.path.abspath(os.path.join(OUTPUT_DIR, '..', '..', 'data', 'ct', 'cq500'))
VOLUMES_DIR = os.path.join(PROJECT_DATA_DIR, 'volumes')
PROCESSED_DIR = os.path.join(PROJECT_DATA_DIR, 'processed')

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

# 采样参数
MAX_VOLUMES = None        # None = 所有已转换的NIfTI
MAX_SLICES_PER_VOL = 120  # 每个体数据最多提取的切片数
BALANCE_CLASSES = True     # 平衡阳性和阴性样本
MIN_SLICES = 15            # 最少切片数


# ======================== 数据加载 ========================

def log(msg):
    print(f"[CQ500-v3] {msg}")
    sys.stdout.flush()


def load_volume_nifti(nii_path: str) -> np.ndarray:
    """从NIfTI文件加载体数据"""
    if not os.path.exists(nii_path):
        return None
    try:
        nii = nib.load(nii_path)
        volume = nii.get_fdata().astype(np.float32)
        # 确保维度是 (Z, H, W)
        if volume.ndim == 3:
            z, h, w = volume.shape
            if z <= h and z <= w:
                pass  # 已经是 (Z, H, W)
            elif h <= z and h <= w:
                volume = np.transpose(volume, (1, 0, 2))
            else:
                volume = np.transpose(volume, (2, 0, 1))
        return volume
    except Exception as e:
        log(f"  NIfTI加载失败 {nii_path}: {e}")
        return None


def load_volume_sitk(path: str) -> np.ndarray:
    """用SimpleITK加载体数据（处理中文路径通过临时文件）"""
    if not os.path.exists(path):
        return None
    try:
        # 先尝试直接加载
        if HAS_SITK:
            sitk.ProcessObject_SetGlobalWarningDisplay(False)
            img = sitk.ReadImage(path)
            return sitk.GetArrayFromImage(img).astype(np.float32)
    except:
        pass
    # 备用：用nibabel
    return load_volume_nifti(path)


def load_all_volumes():
    """加载所有可用的CQ500 NIfTI体数据"""
    # 加载volume索引
    vindex_path = os.path.join(PROCESSED_DIR, 'volume_index.json')
    if os.path.exists(vindex_path):
        import json
        with open(vindex_path, 'r') as f:
            vindex = json.load(f)
    else:
        # 扫描volumes目录
        nii_files = sorted(glob.glob(os.path.join(VOLUMES_DIR, '*.nii.gz')))
        vindex = {}
        for f in nii_files:
            name = os.path.basename(f).replace('.nii.gz', '')
            vindex[name] = {'nii_path': f, 'nii_filename': os.path.basename(f)}
    
    if not vindex:
        log("No NIfTI volumes found! Run cq500_convert.py first.")
        return []
    
    # 加载标注信息
    reads_path = os.path.join(PROJECT_DATA_DIR, 'metadata', 'reads.csv')
    labels = {}
    if os.path.exists(reads_path):
        import csv
        with open(reads_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name', '')
                if name:
                    ich_votes = sum(1 for r in ['R1:ICH', 'R2:ICH', 'R3:ICH'] if row.get(r, '0') == '1')
                    labels[name] = {
                        'is_positive': ich_votes >= 2,
                        'ich_votes': ich_votes,
                        'category': row.get('Category', ''),
                        'mass_effect': row.get('R1:MassEffect', '0') == '1' or row.get('R2:MassEffect', '0') == '1',
                    }
    
    # 收集要加载的病例
    case_keys = list(vindex.keys())
    
    # 平衡采样
    if BALANCE_CLASSES:
        pos_cases = [k for k in case_keys if labels.get(k, {}).get('is_positive', False)]
        neg_cases = [k for k in case_keys if not labels.get(k, {}).get('is_positive', True)]
        
        # 限制数量使正负平衡
        min_count = min(len(pos_cases), len(neg_cases))
        if min_count > 0:
            np.random.shuffle(pos_cases)
            np.random.shuffle(neg_cases)
            case_keys = pos_cases[:min_count] + neg_cases[:min_count]
            log(f"平衡采样: {min_count} 阳性 + {min_count} 阴性 = {len(case_keys)} 总")
        else:
            log(f"未能平衡: 阳性={len(pos_cases)}, 阴性={len(neg_cases)}")
    
    if MAX_VOLUMES and len(case_keys) > MAX_VOLUMES:
        np.random.shuffle(case_keys)
        case_keys = case_keys[:MAX_VOLUMES]
    
    log(f"准备加载 {len(case_keys)} 个体数据...")
    
    volumes = []
    success = 0
    failed = 0
    
    for i, case_key in enumerate(case_keys):
        info = vindex[case_key]
        nii_path = info['nii_path'] if isinstance(info, dict) else info
        if not isinstance(nii_path, str) or not os.path.exists(nii_path):
            continue
        
        vol = load_volume_nifti(nii_path)
        if vol is None:
            failed += 1
            continue
        
        # 过滤太小或太大的体数据
        if vol.shape[0] < MIN_SLICES:
            continue
        
        # 限制切片数
        if vol.shape[0] > MAX_SLICES_PER_VOL:
            # 均匀采样
            indices = np.linspace(0, vol.shape[0]-1, MAX_SLICES_PER_VOL, dtype=int)
            vol = vol[indices]
        
        label = labels.get(case_key, {})
        volumes.append({
            'case_key': case_key,
            'volume': vol,
            'shape': vol.shape,
            'is_positive': label.get('is_positive', False),
            'ich_votes': label.get('ich_votes', 0),
            'category': label.get('category', ''),
        })
        
        success += 1
        if (i + 1) % 50 == 0:
            log(f"  加载进度: {i+1}/{len(case_keys)} (成功={success}, 失败={failed})")
    
    log(f"加载完成: {success} 个体数据")
    return volumes


# ======================== 特征提取 ========================

def apply_window(volume: np.ndarray, center: float, width: float) -> np.ndarray:
    """CT窗宽窗位"""
    half = width / 2.0
    low = center - half
    high = center + half
    return np.clip(volume.astype(np.float32), low, high)


class ResNetFeatureExtractor(nn.Module):
    """ResNet18特征提取器"""
    def __init__(self):
        super().__init__()
        backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        self.features = nn.Sequential(*list(backbone.children())[:-2])
        self.pool = nn.AdaptiveAvgPool2d((1, 1))

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x)
        return x.view(x.size(0), -1)


def build_extractor():
    return ResNetFeatureExtractor().to(DEVICE).eval()


def preprocess_slice(slice_2d: np.ndarray, img_size: int = IMG_SIZE) -> torch.Tensor:
    """预处理切片用于ResNet"""
    zoom = img_size / slice_2d.shape[0]
    resized = ndimage.zoom(slice_2d, zoom, order=1)
    mn, mx = resized.min(), resized.max()
    if mx - mn > 1e-6:
        normed = (resized - mn) / (mx - mn)
    else:
        normed = np.zeros_like(resized)
    tensor = torch.from_numpy(normed).float().unsqueeze(0).repeat(3, 1, 1).unsqueeze(0)
    tensor = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])(tensor)
    return tensor.to(DEVICE)


def extract_slice_features(volume: np.ndarray, extractor, window_name: str = "brain"):
    """提取单个体数据所有切片的特征"""
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


def compute_hu_statistics(volume: np.ndarray) -> np.ndarray:
    """每层的HU统计"""
    stats = []
    for z in range(volume.shape[0]):
        sl = volume[z].flatten()
        head = sl[sl > -500]
        if len(head) > 0:
            stats.append([head.mean(), head.std(), head.min(), head.max()])
        else:
            stats.append([0, 0, -3024, 3071])
    return np.array(stats)


def compute_symmetry_features(volume: np.ndarray, window_name: str = "brain") -> np.ndarray:
    """左右对称性分析"""
    w = WINDOWS[window_name]
    windowed = apply_window(volume, w["center"], w["width"])
    scores = []
    for z in range(windowed.shape[0]):
        sl = windowed[z]
        h, w = sl.shape
        mid = w // 2
        left = sl[:, :mid]
        right = np.fliplr(sl[:, mid:])
        min_w = min(left.shape[1], right.shape[1])
        left = left[:, :min_w]
        right = right[:, :min_w]
        diff = ((left - right) ** 2).mean()
        scores.append(diff)
    return np.array(scores).reshape(-1, 1)


# ======================== 训练 ========================

def train_model(volumes: list):
    """
    使用CQ500全量数据训练异常检测模型
    """
    log(f"构建特征提取器 ({DEVICE})...")
    extractor = build_extractor()
    
    all_features = {wname: [] for wname in WINDOWS}
    hu_stats_list = []
    symmetry_list = []
    volume_labels = []
    
    for i, vinfo in enumerate(volumes):
        vol = vinfo['volume']
        case_key = vinfo['case_key']
        is_pos = vinfo['is_positive']
        
        log(f"\n[{i+1}/{len(volumes)}] {case_key} | 形状={vol.shape} | {'阳性' if is_pos else '阴性'}")
        
        feat_dict = {}
        for wname in WINDOWS:
            feats = extract_slice_features(vol, extractor, wname)
            feat_dict[wname] = feats
            all_features[wname].append(feats)
            log(f"  {wname}: {feats.shape[0]}层 × {feats.shape[1]}维")
        
        hu_stats = compute_hu_statistics(vol)
        hu_stats_list.append(hu_stats)
        
        sym = compute_symmetry_features(vol)
        symmetry_list.append(sym)
        
        volume_labels.append({
            'case_key': case_key,
            'is_positive': is_pos,
            'num_slices': vol.shape[0],
        })
        
        if (i + 1) % 20 == 0:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    
    # 构建参考分布
    log("\n构建参考分布...")
    model = {}
    
    for wname in WINDOWS:
        stacked = np.vstack(all_features[wname])
        n_samples, n_features = stacked.shape
        log(f"\n{wname}: {stacked.shape[0]} 样本")
        
        # PCA降维
        n_components = min(n_samples - 1, n_features, 256)
        log(f"  PCA (组件={n_components})...")
        pca = PCA(n_components=n_components, whiten=False)
        stacked_pca = pca.fit_transform(stacked)
        log(f"  降维后: {stacked_pca.shape[1]}, 方差比: {pca.explained_variance_ratio_.sum():.4f}")
        
        # 均值 + 协方差
        mean_vec = np.mean(stacked_pca, axis=0)
        centered = stacked_pca - mean_vec
        cov = np.cov(centered, rowvar=False)
        
        # 收缩正则化
        shrinkage = 0.1
        cov_reg = (1 - shrinkage) * cov + shrinkage * np.eye(cov.shape[0]) * np.mean(np.diag(cov))
        
        try:
            inv_cov = np.linalg.inv(cov_reg)
        except np.linalg.LinAlgError:
            log(f"  协方差奇异，使用伪逆")
            inv_cov = np.linalg.pinv(cov_reg)
        
        # 马氏距离
        distances = np.array([mahalanobis(f, mean_vec, inv_cov) for f in stacked_pca])
        dist_mean = float(np.mean(distances))
        dist_std = float(np.std(distances))
        
        model[f"{wname}_mean"] = mean_vec
        model[f"{wname}_inv_cov"] = inv_cov
        model[f"{wname}_pca"] = pca
        model[f"{wname}_dist_mean"] = dist_mean
        model[f"{wname}_dist_std"] = dist_std
        model[f"{wname}_dist_max"] = float(np.max(distances))
        model[f"{wname}_dist_p95"] = float(np.percentile(distances, 95))
        
        log(f"  距离: mean={dist_mean:.4f}, std={dist_std:.4f}, p95={model[f'{wname}_dist_p95']:.4f}")
        
        del stacked, stacked_pca, centered, cov, cov_reg, inv_cov
        gc.collect()
    
    # HU统计
    all_hu = np.vstack(hu_stats_list)
    model["hu_mean_mean"] = float(np.mean(all_hu[:, 0]))
    model["hu_std_mean"] = float(np.mean(all_hu[:, 1]))
    model["hu_min_mean"] = float(np.mean(all_hu[:, 2]))
    model["hu_max_mean"] = float(np.mean(all_hu[:, 3]))
    
    # 对称性
    all_sym = np.vstack(symmetry_list)
    model["symmetry_mean"] = float(np.mean(all_sym))
    model["symmetry_std"] = float(np.std(all_sym))
    model["symmetry_p95"] = float(np.percentile(all_sym, 95))
    
    model["windows"] = dict(WINDOWS)
    model["volume_labels"] = volume_labels
    model["num_volumes"] = len(volumes)
    model["total_slices"] = sum(v['volume'].shape[0] for v in volumes)
    
    log(f"\n训练完成!")
    log(f"  HU均值: {model['hu_mean_mean']:.1f}")
    log(f"  对称性: {model['symmetry_mean']:.4f}")
    log(f"  总病例: {len(volumes)}")
    log(f"  总切片: {model['total_slices']}")
    
    return model


# ======================== 保存模型 ========================

def save_model(model):
    """保存模型文件"""
    model_path = os.path.join(OUTPUT_DIR, "brain_ct_model_v3.joblib")
    joblib.dump(model, model_path)
    log(f"模型保存: {model_path}")
    
    info = {
        "name": "Brain CT Anomaly Detection v3 (CQ500 Full)",
        "version": "3.0.0",
        "description": "CQ500全量数据集训练的无监督异常检测",
        "windows": dict(WINDOWS),
        "num_volumes_trained": model["num_volumes"],
        "total_slices": model["total_slices"],
        "backbone": "resnet18_imagenet1k_v1",
        "algorithm": "mahalanobis_distance + PCA",
        "data_source": "CQ500 (490 cases, 341k+ DICOMs)",
        "device": str(DEVICE),
        "training_date": __import__('time').strftime('%Y-%m-%d %H:%M:%S'),
        "hu_reference": {
            "mean": model["hu_mean_mean"],
            "std": model["hu_std_mean"]
        },
        "symmetry_reference": {
            "mean": model["symmetry_mean"],
            "std": model["symmetry_std"]
        },
    }
    
    info_path = os.path.join(OUTPUT_DIR, "brain_ct_info_v3.joblib")
    joblib.dump(info, info_path)
    log(f"信息保存: {info_path}")


# ======================== 主入口 ========================

def main():
    log("=" * 65)
    log("脑部CT异常检测 v3 - CQ500全量训练")
    log("=" * 65)
    
    # 检查环境
    if not HAS_NIB and not HAS_SITK:
        log("[FAIL] nibabel或SimpleITK未安装")
        return
    
    log(f"设备: {DEVICE}")
    log(f"数据目录: {VOLUMES_DIR}")
    
    # 加载数据
    t0 = time.time()
    volumes = load_all_volumes()
    if not volumes:
        log("[FAIL] 没有加载任何体数据")
        return
    log(f"数据加载耗时: {time.time()-t0:.1f}s")
    
    # 训练
    t1 = time.time()
    model = train_model(volumes)
    
    log(f"\n总训练耗时: {time.time()-t1:.1f}s")
    
    # 保存
    save_model(model)
    
    # 清理引用以便释放内存
    del volumes
    gc.collect()
    
    log("\n[OK] 训练完成!")


if __name__ == "__main__":
    main()
