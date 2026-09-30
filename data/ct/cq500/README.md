# CQ500 颅脑CT数据集 — 整合说明

## 概述

CQ500 (Qure.ai CQ500 Head CT Dataset) 是一个公开的头部CT急诊数据集，
包含 **490例** 头部CT扫描，总计 **34万+** DICOM切片。
该数据集已整合到本项目的CT影像工作台中，替代了之前仅有1-2个体数据的旧方案。

## 数据位置

```
data/ct/
├── cq500/                          # CQ500 数据集根目录
│   ├── metadata/                   # 元数据
│   │   ├── reads.csv               # 3位放射科医师标注（491例）
│   │   └── prediction_probabilities.csv  # AI预测概率
│   ├── docs/                       # 参考文档
│   │   ├── CQ500 颅脑CT急诊数据集详细介绍.md
│   │   ├── CQ500-CT 数据集字段释义（reads.csv）.md
│   │   ├── CQ500-CT 数据集字段释义（prediction_probabilities.csv）.md
│   │   ├── 标注方法.md
│   │   ├── SimpleITK编程基础.md
│   │   ├── SimpleITK滤波金属伪影掩码滤波器介绍.md
│   │   ├── VTK编程基础.md
│   │   └── 伪影掩码标注使用的滤波器原理与应用详解.md
│   ├── volumes/                    # 转换后的NIfTI体数据
│   │   └── CQ500-CT-*.nii.gz      # 每个病例一个文件
│   └── processed/                  # 处理后的索引文件
│       ├── cq500_index.joblib      # 完整索引
│       ├── cq500_index.json        # JSON格式索引
│       ├── volume_index.json       # 已转换NIfTI的索引
│       └── volume_index.joblib     # Joblib格式
└── (旧数据已归档到 data/ct_archive/)
```

## 数据统计

| 统计项 | 数值 |
|--------|------|
| 总病例数 | 490 |
| 出血阳性病例 | 205 (41.8%) |
| 阴性病例 | 285 (58.2%) |
| CT平扫(厚层)病例 | 142 |
| CT薄扫病例 | 173 |
| 总DICOM文件 | 341,458 |
| ICH阳性(≥2票) | 205 |
| SDH阳性 | 53 |
| EDH阳性 | 13 |

## 标注体系

- 由3位资深放射科医师独立标注（R1/R2/R3）
- 标注内容：六大出血类型 + 骨折 + 占位效应 + 中线移位
- 每项标注为二分类（0=无，1=有）
- 多数投票（≥2/3）作为金标准

## API 接口

### 新增CQ500相关接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/medical/ct/cq500/stats` | 获取数据集统计 |
| GET/POST | `/api/medical/ct/cq500/cases` | 病例列表浏览 |
| POST | `/api/medical/ct/cq500/load` | 加载指定病例 |

### 病例浏览筛选参数

```json
{
  "is_positive": true,       // 是否阳性
  "category": "B2",          // B1/B2分级
  "has_ich": true,           // 是否脑内出血
  "has_sdh": true,           // 是否硬膜下血肿
  "only_with_volume": true,  // 仅已转换的NIfTI
  "page": 1,
  "page_size": 50
}
```

## 模型

### 异常检测模型 v3

- **位置**: `python/models/brain_ct_model_v3.joblib`
- **方法**: ResNet18特征 + PCA降维 + 马氏距离
- **数据**: CQ500全量转换病例
- **窗口**: 脑组织窗、硬膜下窗、骨窗

### 3D自编码器 v3

- **位置**: `python/models/brain_ct_3d_ae_v3.pth`
- **方法**: 3D卷积自编码器 + 重建误差异常检测
- **Patch**: 32×32×32
- **数据**: CQ500全量NIfTI体数据

## 使用流程

1. **数据转换**: `python scripts/cq500_convert.py`
2. **训练模型**: `python scripts/train_brain_ct_v3.py` 或 `python scripts/train_brain_ct_3dae_v3.py`
3. **启动服务**: 运行 Python 后端后，CT工作站支持从CQ500数据集选择病例
