"""
CT 诊断报告分类器 — 3D CNN 多标签分类
=========================================
用于替换 report 端点，基于真实 CT 数据生成 AI 诊断报告。

模型架构: 3D CNN 编码器 + 全局池化 + 全连接分类头
训练脚本: python/scripts/train_ct_report_classifier.py

用法:
    from server.ct.report_model import load_report_classifier, predict_report
    model = load_report_classifier("models/ct_report_classifier.pth")
    findings = predict_report(model, volume)
"""
import json
import os
import logging
import numpy as np
import torch
import torch.nn as nn
from scipy import ndimage

log = logging.getLogger(__name__)

# 标签名称（与 train_ct_report_classifier.py 一致）
DEFAULT_LABEL_NAMES = [
    "ICH", "IPH", "IVH", "SDH", "EDH", "SAH",
    "LeftBleed", "RightBleed", "ChronicBleed",
    "Fracture", "CalvarialFracture", "OtherFracture",
    "MassEffect", "MidlineShift",
]

TARGET_SHAPE = (128, 128, 64)
_REPORT_CLF_CACHE = None
_LABEL_MAP_CACHE = None


# ---------------------------------------------------------------------------
# 模型架构（与训练脚本一致）
# ---------------------------------------------------------------------------

class _ConvBlock3D(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv3d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm3d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class CTReportClassifier3D(nn.Module):
    """3D CNN 多标签分类器"""

    def __init__(self, in_channels=1, num_classes=14, dropout=0.3):
        super().__init__()
        self.enc1 = _ConvBlock3D(in_channels, 32)
        self.enc2 = _ConvBlock3D(32, 64)
        self.enc3 = _ConvBlock3D(64, 128)
        self.enc4 = _ConvBlock3D(128, 256)
        self.pool = nn.MaxPool3d(2)
        self.global_pool = nn.AdaptiveAvgPool3d(1)
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout * 0.5),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        x = self.pool(self.enc1(x))
        x = self.pool(self.enc2(x))
        x = self.pool(self.enc3(x))
        x = self.pool(self.enc4(x))
        x = self.global_pool(x).flatten(1)
        return self.classifier(x)


# ---------------------------------------------------------------------------
# 模型加载
# ---------------------------------------------------------------------------

def load_report_classifier(model_path: str = None, device: torch.device = None,
                           num_classes: int = 14) -> CTReportClassifier3D:
    """
    加载 CT 诊断报告分类器。

    Parameters
    ----------
    model_path : str or None
        .pth 文件路径。None 时自动查找。
    device : torch.device or None
    num_classes : int
        分类数（默认 14）。

    Returns
    -------
    CTReportClassifier3D (eval mode) 或 None
    """
    global _REPORT_CLF_CACHE
    if _REPORT_CLF_CACHE is not None:
        return _REPORT_CLF_CACHE

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if model_path is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_path = os.path.join(base, "models", "ct_report_classifier.pth")

    if not os.path.isfile(model_path):
        log.warning("CT 报告分类器模型不存在: %s (将使用模板报告)", model_path)
        return None

    try:
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        model = CTReportClassifier3D(in_channels=1, num_classes=num_classes).to(device)

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
        _REPORT_CLF_CACHE = model
        log.info("✅ CT 报告分类器加载成功: %s", model_path)
        return model

    except Exception as e:
        log.error("❌ CT 报告分类器加载失败: %s", e)
        return None


def _load_label_map(model_dir: str = None) -> dict:
    """加载标签映射文件"""
    global _LABEL_MAP_CACHE
    if _LABEL_MAP_CACHE is not None:
        return _LABEL_MAP_CACHE

    if model_dir is None:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_dir = os.path.join(base, "models")

    label_path = os.path.join(model_dir, "ct_report_label_map.json")
    if os.path.isfile(label_path):
        with open(label_path, "r", encoding="utf-8") as f:
            _LABEL_MAP_CACHE = json.load(f)
        return _LABEL_MAP_CACHE

    # 回退到默认标签
    _LABEL_MAP_CACHE = {str(i): name for i, name in enumerate(DEFAULT_LABEL_NAMES)}
    return _LABEL_MAP_CACHE


# ---------------------------------------------------------------------------
# 预处理 / 推理
# ---------------------------------------------------------------------------

def preprocess_volume(volume: np.ndarray) -> np.ndarray:
    """预处理 CT 体数据为分类器输入 (1, 1, D, H, W)"""
    ct = np.clip(volume.astype(np.float32), -1000, 2000)
    ct = (ct + 1000) / 3000.0
    zoom = [t / s for t, s in zip(TARGET_SHAPE, ct.shape)]
    resized = ndimage.zoom(ct, zoom, order=1)
    return resized[np.newaxis, np.newaxis, ...].astype(np.float32)


def predict_report(model: CTReportClassifier3D, volume: np.ndarray,
                   device: torch.device = None, threshold: float = 0.5) -> dict:
    """
    对 CT 体数据进行诊断报告推理。

    Parameters
    ----------
    model : CTReportClassifier3D
    volume : np.ndarray
        原始 CT 体数据 (D, H, W)。
    device : torch.device
    threshold : float
        二分类阈值。

    Returns
    -------
    dict: {
        "findings": [找到的异常列表],
        "impression": str,
        "probabilities": {标签名: 概率},
        "positive_labels": [阳性标签列表],
    }
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if model is None:
        return _fallback_report(volume)

    input_tensor = preprocess_volume(volume)
    input_tensor = torch.from_numpy(input_tensor).to(device)

    with torch.no_grad():
        logits = model(input_tensor)
        probs = torch.sigmoid(logits).cpu().numpy()[0]  # (num_classes,)

    label_map = _load_label_map()
    num_classes = len(label_map)

    # 构建结果
    findings = []
    positive_labels = []
    probabilities = {}

    for i in range(num_classes):
        label = label_map.get(str(i), f"class_{i}")
        prob = float(probs[i]) if i < len(probs) else 0.0
        probabilities[label] = round(prob, 4)
        if prob >= threshold:
            positive_labels.append(label)

    # 生成 findings 文字
    if not positive_labels:
        findings = ["CT扫描未见明显急性颅内异常"]
        impression = "No acute intracranial abnormality detected."
    else:
        for label in positive_labels:
            findings.append(f"{_label_to_chinese(label)}阳性 (置信度: {probabilities[label]:.1%})")
        impression = f"检测到 {len(positive_labels)} 项异常: {', '.join(positive_labels)}"

    return {
        "findings": findings,
        "impression": impression,
        "probabilities": probabilities,
        "positive_labels": positive_labels,
        "is_deep_learning": True,
    }


def _label_to_chinese(label: str) -> str:
    """标签名转中文描述"""
    mapping = {
        "ICH": "颅内出血", "IPH": "脑实质出血", "IVH": "脑室内出血",
        "SDH": "硬膜下出血", "EDH": "硬膜外出血", "SAH": "蛛网膜下腔出血",
        "LeftBleed": "左侧出血", "RightBleed": "右侧出血",
        "ChronicBleed": "慢性出血", "Fracture": "骨折",
        "CalvarialFracture": "颅骨骨折", "OtherFracture": "其他骨折",
        "MassEffect": "占位效应", "MidlineShift": "中线偏移",
    }
    return mapping.get(label, label)


def _fallback_report(volume: np.ndarray) -> dict:
    """模型未加载时的回退报告"""
    return {
        "findings": [f"CT扫描显示{volume.shape[0]}层头部影像，模型未加载，使用统计信息"],
        "impression": "Model not available — statistical summary only.",
        "probabilities": {},
        "positive_labels": [],
        "is_deep_learning": False,
    }
