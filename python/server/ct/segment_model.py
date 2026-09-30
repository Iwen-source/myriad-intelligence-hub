"""
脑CT三维分割模型 — 3D UNet (复用 artifact_unet_model.py 架构)
===========================================================
用于替换 segment-3d 端点的阈值分割，提供真实的深度学习分割。

架构与 artifact_unet_model.py 中的 UNet3D 相同，但加载不同的权重。
训练脚本: python/scripts/train_ct_segmentation_3d.py

用法:
    from server.ct.segment_model import load_seg_model, predict_segmentation
    model = load_seg_model("models/ct_seg_unet.pth")
    mask = predict_segmentation(model, volume)
"""
import os
import logging
import numpy as np
import torch
from scipy import ndimage
from server.ct.artifact_unet_model import UNet3D

log = logging.getLogger(__name__)

# 训练时使用的统一尺寸 (D, H, W)
TARGET_SHAPE = (128, 128, 64)

# ---------------------------------------------------------------------------
# 模型加载
# ---------------------------------------------------------------------------

_SEG_MODEL_CACHE = None


def load_seg_model(model_path: str = None, device: torch.device = None) -> UNet3D:
    """
    加载三维分割 UNet3D 模型。

    Parameters
    ----------
    model_path : str or None
        .pth 文件路径。None 时自动在 models/ 目录查找。
    device : torch.device or None
        推理设备。

    Returns
    -------
    UNet3D (eval mode) 或 None
    """
    global _SEG_MODEL_CACHE
    if _SEG_MODEL_CACHE is not None:
        return _SEG_MODEL_CACHE

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if model_path is None:
        # 自动查找
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base, "models", "ct_seg_unet.pth")

    if not os.path.isfile(model_path):
        log.warning("三维分割模型文件不存在: %s (将使用阈值回退)", model_path)
        return None

    try:
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        model = UNet3D(in_ch=1, out_ch=1, base_ch=16).to(device)

        # 兼容多种 checkpoint 格式
        if isinstance(checkpoint, dict):
            sd = checkpoint.get("model") or checkpoint.get("model_state_dict") or checkpoint
        else:
            sd = checkpoint

        from collections import OrderedDict
        new_sd = OrderedDict()
        for k, v in sd.items():
            new_sd[k[7:] if k.startswith("module.") else k] = v

        model.load_state_dict(new_sd, strict=False)
        model.eval()
        _SEG_MODEL_CACHE = model
        log.info("✅ 三维分割模型加载成功: %s", model_path)
        return model

    except Exception as e:
        log.error("❌ 三维分割模型加载失败: %s", e)
        return None


def preprocess_volume(volume: np.ndarray) -> np.ndarray:
    """预处理 CT 体数据为模型输入 (1, 1, D, H, W)"""
    ct = np.clip(volume.astype(np.float32), -1000, 2000)
    ct = (ct + 1000) / 3000.0  # 归一化到 [0, 1]
    zoom = [t / s for t, s in zip(TARGET_SHAPE, ct.shape)]
    resized = ndimage.zoom(ct, zoom, order=1)
    return resized[np.newaxis, np.newaxis, ...].astype(np.float32)


def postprocess_mask(raw_logits: np.ndarray, original_shape: tuple,
                     threshold: float = 0.5) -> np.ndarray:
    """后处理：将模型输出还原到原始 CT 尺寸"""
    mask = (1.0 / (1.0 + np.exp(-raw_logits)) > threshold).astype(np.float32)
    mask = np.squeeze(mask)
    zoom = [t / s for t, s in zip(original_shape, mask.shape)]
    mask_resized = ndimage.zoom(mask, zoom, order=0)
    return (mask_resized > 0.5).astype(np.float32)


def predict_segmentation(model: UNet3D, volume: np.ndarray,
                         device: torch.device = None) -> np.ndarray:
    """
    对 CT 体数据进行三维分割推理。

    Parameters
    ----------
    model : UNet3D
        已加载的模型。
    volume : np.ndarray
        原始 CT 体数据 shape (D, H, W)。
    device : torch.device

    Returns
    -------
    mask : np.ndarray
        原始尺寸的二值掩码 (D, H, W)，1=分割目标。
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if model is None:
        raise RuntimeError("模型未加载")

    original_shape = volume.shape[:3]
    input_tensor = preprocess_volume(volume)
    input_tensor = torch.from_numpy(input_tensor).to(device)

    with torch.no_grad():
        output = model(input_tensor)
        logits = output.cpu().numpy()

    return postprocess_mask(logits, original_shape)
