"""
CQ500 数据加载器 — 服务端模块
================================
为CT影像工作台提供CQ500病例浏览和加载能力。
支持按条件筛选病例、快速加载NIfTI体数据。
"""

import os, json, csv, glob, time
import numpy as np
import logging
from pathlib import Path

log = logging.getLogger(__name__)

# ======================== 路径配置 ========================

CQ500_DATA_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'data', 'ct', 'cq500'
))
CQ500_METADATA_DIR = os.path.join(CQ500_DATA_DIR, 'metadata')
CQ500_VOLUMES_DIR = os.path.join(CQ500_DATA_DIR, 'volumes')
CQ500_PROCESSED_DIR = os.path.join(CQ500_DATA_DIR, 'processed')

# 元数据文件
READS_CSV = os.path.join(CQ500_METADATA_DIR, 'reads.csv')
PRED_CSV = os.path.join(CQ500_METADATA_DIR, 'prediction_probabilities.csv')
VOLUME_INDEX = os.path.join(CQ500_PROCESSED_DIR, 'volume_index.json')

# ======================== 缓存 ========================

_index_cache = None
_labels_cache = None


# ======================== 标签加载 ========================

def load_labels():
    """加载CQ500标注数据"""
    global _labels_cache
    if _labels_cache is not None:
        return _labels_cache
    
    labels = {}
    
    if os.path.exists(READS_CSV):
        with open(READS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get('name', '')
                if not name:
                    continue
                labels[name] = {
                    # 3位阅片者投票数
                    'ich': sum(1 for r in ['R1:ICH', 'R2:ICH', 'R3:ICH'] if row.get(r, '0') == '1'),
                    'iph': sum(1 for r in ['R1:IPH', 'R2:IPH', 'R3:IPH'] if row.get(r, '0') == '1'),
                    'ivh': sum(1 for r in ['R1:IVH', 'R2:IVH', 'R3:IVH'] if row.get(r, '0') == '1'),
                    'sdh': sum(1 for r in ['R1:SDH', 'R2:SDH', 'R3:SDH'] if row.get(r, '0') == '1'),
                    'edh': sum(1 for r in ['R1:EDH', 'R2:EDH', 'R3:EDH'] if row.get(r, '0') == '1'),
                    'sah': sum(1 for r in ['R1:SAH', 'R2:SAH', 'R3:SAH'] if row.get(r, '0') == '1'),
                    'fracture': sum(1 for r in ['R1:Fracture', 'R2:Fracture', 'R3:Fracture'] if row.get(r, '0') == '1'),
                    'mass_effect': sum(1 for r in ['R1:MassEffect', 'R2:MassEffect', 'R3:MassEffect'] if row.get(r, '0') == '1'),
                    'midline_shift': sum(1 for r in ['R1:MidlineShift', 'R2:MidlineShift', 'R3:MidlineShift'] if row.get(r, '0') == '1'),
                    'category': row.get('Category', ''),
                    'is_positive': sum(1 for r in ['R1:ICH', 'R2:ICH', 'R3:ICH'] if row.get(r, '0') == '1') >= 2,
                }
    
    _labels_cache = labels
    return labels


# ======================== 病例列表 ========================

def get_case_list(filters: dict = None) -> list:
    """
    获取CQ500病例列表
    
    Args:
        filters: {
            'is_positive': True/False,
            'category': 'B1'/'B2',
            'has_ich': True/False,
            'has_sdh': True/False,
            'page': 1,
            'page_size': 50,
            'sort': 'case_id',
        }
    Returns:
        病例列表
    """
    if filters is None:
        filters = {}
    
    labels = load_labels()
    
    # 检查已转换的NIfTI
    volume_index = {}
    if os.path.exists(VOLUME_INDEX):
        with open(VOLUME_INDEX, 'r') as f:
            volume_index = json.load(f)
    
    # 构建病例列表
    cases = []
    for name, label in labels.items():
        # 从name提取编号
        case_id_str = name.replace('CQ500-CT-', '')
        try:
            case_id = int(case_id_str)
        except ValueError:
            continue
        
        # 检查是否有NIfTI转换
        has_volume = name in volume_index
        volume_info = volume_index.get(name, {})
        
        # 应用筛选
        if 'is_positive' in filters and label['is_positive'] != filters['is_positive']:
            continue
        if 'category' in filters and filters['category'] and label['category'] != filters['category']:
            continue
        if filters.get('has_ich') and label['ich'] < 2:
            continue
        if filters.get('has_sdh') and label['sdh'] < 2:
            continue
        if filters.get('only_with_volume') and not has_volume:
            continue
        
        cases.append({
            'case_id': case_id,
            'name': name,
            'category': label['category'],
            'is_positive': label['is_positive'],
            'ich': label['ich'],
            'iph': label['iph'],
            'ivh': label['ivh'],
            'sdh': label['sdh'],
            'edh': label['edh'],
            'sah': label['sah'],
            'fracture': label['fracture'],
            'mass_effect': label['mass_effect'],
            'midline_shift': label['midline_shift'],
            'has_volume': has_volume,
            'volume_shape': volume_info.get('volume_shape', []),
            'dicom_count': volume_info.get('dicom_count', 0),
            'series_name': volume_info.get('series_name', ''),
        })
    
    # 排序
    sort_key = filters.get('sort', 'case_id')
    if sort_key == 'case_id':
        cases.sort(key=lambda x: x['case_id'])
    elif sort_key == 'ich':
        cases.sort(key=lambda x: x['ich'], reverse=True)
    
    # 分页
    page = filters.get('page', 1)
    page_size = filters.get('page_size', 100)
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        'total': len(cases),
        'page': page,
        'page_size': page_size,
        'cases': cases[start:end],
    }


# ======================== 体数据加载 ========================

def load_cq500_volume(case_key: str):
    """
    加载指定病例的CT体数据
    
    Args:
        case_key: 'CQ500-CT-XXX'
    
    Returns:
        numpy volume (Z, H, W) 或 None
    """
    nii_path = os.path.join(CQ500_VOLUMES_DIR, f'{case_key}.nii.gz')
    if not os.path.exists(nii_path):
        log.warning(f'NIfTI not found for {case_key}: {nii_path}')
        return None
    
    try:
        import nibabel as nib
        nii = nib.load(nii_path)
        volume = nii.get_fdata().astype(np.float32)
        log.info(f'Loaded {case_key}: shape={volume.shape}, range=[{volume.min():.0f}, {volume.max():.0f}]')
        return volume
    except Exception as e:
        log.error(f'Failed to load {case_key}: {e}')
        return None


# ======================== 数据统计 ========================

def get_dataset_stats() -> dict:
    """获取CQ500数据集统计"""
    labels = load_labels()
    
    total = len(labels)
    positive = sum(1 for l in labels.values() if l['is_positive'])
    negative = total - positive
    
    # 出血类型计数
    ich = sum(1 for l in labels.values() if l['ich'] >= 2)
    sdh = sum(1 for l in labels.values() if l['sdh'] >= 2)
    edh = sum(1 for l in labels.values() if l['edh'] >= 2)
    ivh = sum(1 for l in labels.values() if l['ivh'] >= 2)
    sah = sum(1 for l in labels.values() if l['sah'] >= 2)
    mass = sum(1 for l in labels.values() if l['mass_effect'] >= 2)
    shift = sum(1 for l in labels.values() if l['midline_shift'] >= 2)
    fracture = sum(1 for l in labels.values() if l['fracture'] >= 2)
    
    # 已转换的NIfTI
    nii_count = 0
    nii_total_size = 0
    if os.path.exists(CQ500_VOLUMES_DIR):
        nii_files = glob.glob(os.path.join(CQ500_VOLUMES_DIR, '*.nii.gz'))
        nii_count = len(nii_files)
        nii_total_size = sum(os.path.getsize(f) for f in nii_files) // (1024*1024)
    
    return {
        'total_cases': total,
        'positive_cases': positive,
        'negative_cases': negative,
        'ich_cases': ich,
        'sdh_cases': sdh,
        'edh_cases': edh,
        'ivh_cases': ivh,
        'sah_cases': sah,
        'mass_effect_cases': mass,
        'midline_shift_cases': shift,
        'fracture_cases': fracture,
        'converted_nifti': nii_count,
        'nifti_total_mb': nii_total_size,
    }
