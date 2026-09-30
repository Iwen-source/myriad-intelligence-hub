"""
CT 影像工作台 — 图像处理模块
从 ct_workstation_api.py 拆分而来
"""
import base64
import io
from typing import Optional, Tuple
import numpy as np
import SimpleITK as sitk


def apply_window(slice_2d: np.ndarray, ww: float, wl: float) -> np.ndarray:
    """CT窗宽窗位调整"""
    lower = wl - ww / 2.0
    upper = wl + ww / 2.0
    windowed = np.clip(slice_2d, lower, upper)
    windowed = (windowed - lower) / (upper - lower + 1e-6)
    return (windowed * 255).astype(np.uint8)


def filter_slice(slice_2d: np.ndarray, mode: str, variance: float) -> np.ndarray:
    """CT图像滤波"""
    from scipy.ndimage import gaussian_filter, median_filter
    if mode == 'gaussian':
        return gaussian_filter(slice_2d, sigma=variance)
    elif mode == 'median':
        size = max(3, int(variance * 10))
        if size % 2 == 0:
            size += 1
        return median_filter(slice_2d, size=size)
    elif mode == 'bilateral':
        from skimage.restoration import denoise_bilateral
        return denoise_bilateral(slice_2d, sigma_color=variance, sigma_spatial=1)
    return slice_2d


def edge_slice_advanced(slice_2d: np.ndarray, method: str, threshold: float) -> np.ndarray:
    """边缘检测"""
    from skimage import filters, feature
    if method == 'canny':
        return feature.canny(slice_2d, sigma=threshold).astype(np.uint8) * 255
    elif method == 'sobel':
        return filters.sobel(slice_2d)
    elif method == 'prewitt':
        return filters.prewitt(slice_2d)
    elif method == 'roberts':
        return filters.roberts(slice_2d)
    return slice_2d


def threshold_slice(slice_2d: np.ndarray, low: float, high: float) -> np.ndarray:
    """阈值分割"""
    mask = np.logical_and(slice_2d >= low, slice_2d <= high)
    return mask.astype(np.uint8) * 255


def view_planes(volume: np.ndarray, z: int, y: int, x: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """获取三视图切面"""
    axial = np.rot90(volume[z, :, :]) if z < volume.shape[0] else np.rot90(volume[volume.shape[0] // 2, :, :])
    coronal = np.rot90(volume[:, y, :]) if y < volume.shape[1] else np.rot90(volume[:, volume.shape[1] // 2, :])
    sagittal = np.rot90(volume[:, :, x]) if x < volume.shape[2] else np.rot90(volume[:, :, volume.shape[2] // 2])
    return axial, coronal, sagittal


def build_3d_mask(volume: np.ndarray, lower: float, upper: float) -> np.ndarray:
    """构建3D二值掩膜"""
    return np.logical_and(volume >= lower, volume <= upper).astype(np.uint8)


def build_metal_artifact_mask(volume: np.ndarray, threshold: float = 2000) -> np.ndarray:
    """金属伪影检测"""
    return (volume > threshold).astype(np.uint8)


def compute_histogram_data(slice_2d: np.ndarray, bins: int = 120) -> dict:
    """计算直方图数据"""
    hist, edges = np.histogram(slice_2d, bins=bins)
    return {
        "histogram": hist.tolist(),
        "binEdges": [round(float(e), 1) for e in edges],
        "mean": float(np.mean(slice_2d)),
        "std": float(np.std(slice_2d)),
        "min": float(np.min(slice_2d)),
        "max": float(np.max(slice_2d)),
        "median": float(np.median(slice_2d)),
        "p5": float(np.percentile(slice_2d, 5)),
        "p95": float(np.percentile(slice_2d, 95))
    }


def compute_ct_statistics(volume: np.ndarray) -> dict:
    """CT影像统计分析"""
    brain_mask = volume > 0
    brain_voxels = volume[brain_mask]
    if brain_voxels.size == 0:
        return {"error": "No brain tissue detected"}
    gray_matter_mask = (brain_voxels >= 20) & (brain_voxels <= 50)
    white_matter_mask = (brain_voxels > 50) & (brain_voxels <= 80)
    return {
        "volume_shape": list(volume.shape),
        "total_voxels": int(volume.size),
        "brain_voxels": int(np.sum(brain_mask)),
        "mean_hu": float(np.mean(brain_voxels)),
        "std_hu": float(np.std(brain_voxels)),
        "min_hu": float(np.min(brain_voxels)),
        "max_hu": float(np.max(brain_voxels)),
        "gray_matter_ratio": float(np.sum(gray_matter_mask) / brain_voxels.size) if brain_voxels.size > 0 else 0,
        "white_matter_ratio": float(np.sum(white_matter_mask) / brain_voxels.size) if brain_voxels.size > 0 else 0,
        "cerebrospinal_fluid_ratio": float(np.sum(brain_voxels < 20) / brain_voxels.size) if brain_voxels.size > 0 else 0
    }


def array_to_b64(arr: np.ndarray, cmap: str = 'gray') -> str:
    """numpy数组转base64图片"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(arr, cmap=cmap)
    ax.axis('off')
    plt.tight_layout(pad=0)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=72, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()


def fig_to_b64(fig) -> str:
    """matplotlib figure转base64"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()


def overlay_to_b64(gray: np.ndarray, mask: np.ndarray, mask_color: tuple = (1, 0, 0)) -> str:
    """灰度图上叠加掩膜并转base64"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(gray, cmap='gray')
    overlay = np.zeros((*gray.shape, 4))
    overlay[..., 0] = mask * mask_color[0]
    overlay[..., 3] = mask * 0.5
    ax.imshow(overlay)
    ax.axis('off')
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=72, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()
