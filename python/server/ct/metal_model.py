"""
CT 金属伪影检测模型 — 3D UNet
=================================
用于替换 metal-detect 端点的 HU 阈值检测，提供真实的深度学习检测。

复用 UNet3D 架构（与 artifact_unet_model.py 相同），加载专用权重。
训练脚本: python/scripts/train_ct_artifact_3d.py

用法:
    from server.ct.metal_model import load_metal_model, detect_metal_artifact
    model = load_metal_model("models/ct_metal_unet.pth")
    mask = detect_metal_artifact(model, volume)
"""
import os
import logging
import numpy as np
import torch
from scipy import ndimage
from server.ct.artifact_unet_model import UNet3D

log = logging.getLogger(__name__)

TARGET_SHAPE = (128, 128, 64)
_METAL_MODEL_CACHE = None


def load_metal_model(model_path: str = None, device: torch.device = None) -> UNet3D:
    """
    加载金属伪影检测 UNet3D 模型。
    
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
    global _METAL_MODEL_CACHE
    if _METAL_MODEL_CACHE is not None:
        return _METAL_MODEL_CACHE

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if model_path is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base, "models", "ct_metal_unet.pth")

    if not os.path.isfile(model_path):
        log.warning("金属伪影模型文件不存在: %s (将使用阈值回退)", model_path)
        return None

    try:
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        model = UNet3D(in_ch=1, out_ch=1, base_ch=16).to(device)

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
        _METAL_MODEL_CACHE = model
        log.info("✅ 金属伪影检测模型加载成功: %s", model_path)
        return model

    except Exception as e:
        log.error("❌ 金属伪影检测模型加载失败: %s", e)
        return None


def preprocess_volume(volume: np.ndarray) -> np.ndarray:
    """预处理 CT 体数据 (1, 1, D, H, W)"""
    ct = np.clip(volume.astype(np.float32), -1000, 3000)
    ct = (ct + 1000) / 4000.0
    zoom = [t / s for t, s in zip(TARGET_SHAPE, ct.shape)]
    resized = ndimage.zoom(ct, zoom, order=1)
    return resized[np.newaxis, np.newaxis, ...].astype(np.float32)


def postprocess_mask(raw_logits: np.ndarray, original_shape: tuple,
                     threshold: float = 0.35) -> np.ndarray:
    """后处理：还原到原始尺寸"""
    mask = (1.0 / (1.0 + np.exp(-raw_logits)) > threshold).astype(np.float32)
    mask = np.squeeze(mask)
    zoom = [t / s for t, s in zip(original_shape, mask.shape)]
    mask_resized = ndimage.zoom(mask, zoom, order=0)
    return (mask_resized > 0.5).astype(np.float32)


def detect_metal_artifact(model: UNet3D, volume: np.ndarray,
                          device: torch.device = None) -> np.ndarray:
    """
    对 CT 体数据进行金属伪影检测推理。

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
        原始尺寸的二值伪影掩码 (D, H, W)，1=金属伪影。
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
