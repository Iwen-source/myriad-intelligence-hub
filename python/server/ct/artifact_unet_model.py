"""
脑CT伪影分割模型 — UNet3D 定义 + 加载器

直接从 temp.py / optimized_train_artifact_segmentation.py 中提取的 UNet3D 架构，
用于加载 best_artifact_unet.pth 并进行推理。
"""
import os
import logging
import numpy as np
import torch
import torch.nn as nn
from scipy import ndimage

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# UNet3D 模型架构（与训练脚本一致）
# ---------------------------------------------------------------------------

class DoubleConv3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch), nn.ReLU(inplace=True),
            nn.Conv3d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.conv(x)


class Down3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.pool = nn.MaxPool3d(2)
        self.conv = DoubleConv3D(in_ch, out_ch)

    def forward(self, x):
        return self.conv(self.pool(x))


class Up3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.up = nn.ConvTranspose3d(in_ch, in_ch // 2, 2, 2)
        self.conv = DoubleConv3D(in_ch, out_ch)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        d = x2.size()[2] - x1.size()[2]
        h = x2.size()[3] - x1.size()[3]
        w = x2.size()[4] - x1.size()[4]
        x1 = nn.functional.pad(x1, [w//2, w-w//2, h//2, h-h//2, d//2, d-d//2])
        return self.conv(torch.cat([x2, x1], dim=1))


class UNet3D(nn.Module):
    """3D U-Net — CQ500 脑CT伪影分割"""
    def __init__(self, in_ch=1, out_ch=1, base_ch=16):
        super().__init__()
        self.inc = DoubleConv3D(in_ch, base_ch)
        self.down1 = Down3D(base_ch, base_ch * 2)
        self.down2 = Down3D(base_ch * 2, base_ch * 4)
        self.down3 = Down3D(base_ch * 4, base_ch * 8)
        self.up1 = Up3D(base_ch * 8, base_ch * 4)
        self.up2 = Up3D(base_ch * 4, base_ch * 2)
        self.up3 = Up3D(base_ch * 2, base_ch)
        self.outc = nn.Conv3d(base_ch, out_ch, 1)

    def forward(self, x):
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x = self.up1(x4, x3)
        x = self.up2(x, x2)
        x = self.up3(x, x1)
        return self.outc(x)


# ---------------------------------------------------------------------------
# 模型加载
# ---------------------------------------------------------------------------

def _checkpoint_with_model(checkpoint: dict) -> bool:
    """检查 checkpoint 里的 key 是 'model' 还是 'model_state_dict'"""
    return 'model' in checkpoint


def load_artifact_unet(model_path: str, device: torch.device = None) -> UNet3D:
    """
    加载训练好的 best_artifact_unet.pth，返回 UNet3D 模型（eval 模式）。

    Parameters
    ----------
    model_path : str
        .pth 文件路径
    device : torch.device
        推理设备（默认 cuda/cpu 自动选择）

    Returns
    -------
    UNet3D 模型 (eval mode)，加载失败返回 None
    """
    try:
        if device is None:
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        checkpoint = torch.load(model_path, map_location=device, weights_only=False)

        # 构建模型
        model = UNet3D(in_ch=1, out_ch=1, base_ch=16).to(device)

        # 兼容两种 checkpoint 格式
        if 'model' in checkpoint:
            state_dict = checkpoint['model']
        elif 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
        else:
            # 直接是 state_dict
            state_dict = checkpoint

        # 处理 DataParallel 打包的权重前缀 'module.'
        from collections import OrderedDict
        new_state_dict = OrderedDict()
        for k, v in state_dict.items():
            name = k[7:] if k.startswith('module.') else k
            new_state_dict[name] = v

        model.load_state_dict(new_state_dict, strict=False)
        model.eval()
        log.info("✅ 伪影分割模型加载成功: %s (epoch=%s, best_dice=%.4f)",
                 model_path,
                 checkpoint.get('epoch', '?'),
                 checkpoint.get('best_dice', 0.0))
        return model

    except Exception as e:
        log.error("❌ 伪影分割模型加载失败: %s", e)
        import traceback
        traceback.print_exc()
        return None


# ---------------------------------------------------------------------------
# 推理预处理 / 后处理
# ---------------------------------------------------------------------------

TARGET_SHAPE = (128, 128, 64)  # 训练时输入尺寸


def preprocess_volume(volume: np.ndarray, target_shape=TARGET_SHAPE) -> np.ndarray:
    """
    将任意尺寸的 CT 体数据预处理为模型输入。

    步骤：
    1. HU 裁剪 [-1000, 2000]
    2. 归一化到 [0, 1]
    3. 重采样到 target_shape (D, H, W)
    """
    # HU 裁剪
    ct = np.clip(volume.astype(np.float32), -1000, 2000)
    # 归一化
    ct = (ct + 1000) / 3000.0

    # 重采样
    zoom = [t / s for t, s in zip(target_shape, ct.shape)]
    resized = ndimage.zoom(ct, zoom, order=1)

    # (D, H, W) → (1, 1, D, H, W)
    resized = resized[np.newaxis, np.newaxis, ...].astype(np.float32)
    return resized


def postprocess_mask(raw_logits: np.ndarray, original_shape, threshold=0.35) -> np.ndarray:
    """
    将模型输出（logits）还原到原始体数据尺寸。

    Parameters
    ----------
    raw_logits : np.ndarray
        模型输出 shape (1, 1, D, H, W)，即 sigmoid 前的 logits
    original_shape : tuple
        原始 CT shape (D, H, W)
    threshold : float
        二值化阈值

    Returns
    -------
    mask : np.ndarray
        原始尺寸的二值掩码
    """
    # sigmoid + 阈值
    mask = (1.0 / (1.0 + np.exp(-raw_logits)) > threshold).astype(np.float32)
    mask = np.squeeze(mask)  # (D, H, W)

    # 重采样回原始尺寸
    zoom = [t / s for t, s in zip(original_shape, mask.shape)]
    mask_resized = ndimage.zoom(mask, zoom, order=0)
    mask_resized = (mask_resized > 0.5).astype(np.float32)
    return mask_resized


def predict_artifact(model: UNet3D, volume: np.ndarray, device: torch.device = None) -> np.ndarray:
    """
    对完整体数据进行伪影分割推理。

    Parameters
    ----------
    model : UNet3D
        已加载的模型
    volume : np.ndarray
        原始 CT 体数据 shape (D, H, W)
    device : torch.device

    Returns
    -------
    mask : np.ndarray
        原始尺寸的二值伪影掩码 (D, H, W)
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    original_shape = volume.shape[:3]

    # 预处理
    input_tensor = preprocess_volume(volume)  # (1, 1, D, H, W)
    input_tensor = torch.from_numpy(input_tensor).to(device)

    # 推理（无梯度）
    with torch.no_grad():
        output = model(input_tensor)  # (1, 1, D', H', W')
        logits = output.cpu().numpy()

    # 后处理
    mask = postprocess_mask(logits, original_shape)
    return mask
