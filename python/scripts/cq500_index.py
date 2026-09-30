"""
CQ500 数据集索引器
===================
扫描所有490例头部CT病例，建立完整的元数据索引。
支持按病例编号、扫描序列、病灶类型查询。

输出: cq500_index.joblib (包含所有病例索引信息)
"""

import os, sys, glob, csv, json, re
import joblib
import numpy as np
from pathlib import Path
from collections import OrderedDict
import warnings
warnings.filterwarnings('ignore')

# ======================== 路径配置 ========================

# CQ500原始数据根目录
CQ500_ORIG_DIR = r"D:\东软实习\CT_Junior\CQ500\CQ500_orig"
# 项目数据目录
PROJECT_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'ct', 'cq500'))
# 模型保存目录
MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

# ======================== 扫描序列别名映射 ========================

# 每个case的Unknown Study下可能有各种子目录名称，这里映射到标准类型
SERIES_TYPE_MAP = {
    # 厚层平扫 (annotated)
    'CT Plain': 'plain_thick',
    'CT Plain-2': 'plain_thick',
    'CT Plain-3': 'plain_thick',
    'CT 5mm': 'plain_thick',
    'CT 5mm-2': 'plain_thick',
    'CT 5mm-3': 'plain_thick',
    'CT 5mm-4': 'plain_thick',
    'CT 55mm Plain': 'plain_thick',
    'CT 55mm Plain-2': 'plain_thick',
    'CT Plain 3mm': 'plain_thick',
    'CT Plain 3mm-2': 'plain_thick',
    'CT 3.753.75mm Plain': 'plain_thick',
    'CT BRAIN PLAIN': 'plain_thick',
    'CT I To S': 'plain_thick',
    'CT 5 MM': 'plain_thick',
    'CT 5 MM PRE CONTRAST': 'plain_thick',
    'CT 5 MM PRE CONTRAST-2': 'plain_thick',
    'CT 1.25MM': 'plain_thick',
    'CT 1.25 MMC': 'plain_thick',
    'CT 1.25mm std': 'plain_thick',
    'CT 1.25': 'plain_thick',
    'CT PRE CONTRAST 5MM STD': 'plain_thick',
    'CT C': 'plain_thick',
    'CT C-2': 'plain_thick',
    'CT 2.55mm': 'plain_thick',
    'CT 2.55mm-2': 'plain_thick',
    'CT 2.55mm-3': 'plain_thick',
    'CT 2.55mm-4': 'plain_thick',
    'CT Helical': 'plain_thick',
    'CT HELICAL-2': 'plain_thick',
    
    # 薄层平扫
    'CT PLAIN THIN': 'plain_thin',
    'CT PLAIN THIN-2': 'plain_thin',
    'CT Thin Plain': 'plain_thin',
    'CT Thin Plain-2': 'plain_thin',
    'CT Thin Plain-3': 'plain_thin',
    'CT PRE CONTRAST THIN': 'plain_thin',
    'CT 0.625mm': 'plain_thin',
    'CT 0.625mm-2': 'plain_thin',
    'CT 0.625mm-3': 'plain_thin',
    'CT 0.625 MM HI RES': 'plain_thin',
    'CT 0.625mm DMPR on HiRes VS40': 'plain_thin',
    'CT Axial 0.625 HiResVS40': 'plain_thin',
    'CT THIN': 'plain_thin',
    'CT THIN-2': 'plain_thin',
    'CT THIN STD': 'plain_thin',
    'CT C THIN': 'plain_thin',
    'CT C THIN-2': 'plain_thin',
    'CT Thin Stnd': 'plain_thin',
    'CT Thin Stand': 'plain_thin',
    'CT SOFT THIN': 'plain_thin',
    'CT Thin Soft': 'plain_thin',
    'CT Thin Details': 'plain_thin',
    'CT LT THIN BONE': 'plain_thin',
    'CT RT THIN BONE': 'plain_thin',
    'CT THIN BONE PNS': 'plain_thin',
    'CT THIN BONE PNS 55': 'plain_thin',
    'CT BONE THIN': 'plain_thin',
    'CT BONE THIN-2': 'plain_thin',
    'CT DE THIN': 'plain_thin',
    'CT HRCT': 'plain_thin',
    'CT HELICAL': 'plain_thin',
    
    # 骨窗
    'CT BONE': 'bone',
    'CT BONE-2': 'bone',
    'CT PRE CONTRAST BONE': 'bone',
    'CT Thin Bone': 'bone',
    
    # 增强扫描
    'CT 4cc sec 150cc D3D on': 'enhanced',
    'CT 4cc sec 150cc D3D on-2': 'enhanced',
    'CT 4cc sec 150cc D3D on-3': 'enhanced',
    'CT POST CONTRAST': 'enhanced',
    'CT POST CONTRAST-2': 'enhanced',
    'CT POST CONTRAST-3': 'enhanced',
    'CT POST CONTRAST-4': 'enhanced',
    'CT CONTRAST': 'enhanced',
    'CT CONTRAST-2': 'enhanced',
    'CT CONTRAST-3': 'enhanced',
    'CT 5mm POST CONTRAST': 'enhanced',
    'CT ORAL IV': 'enhanced',
    'CT ORAL IV-2': 'enhanced',
    'CT ORAL IV-3': 'enhanced',
    'CT 55mm Contrast': 'enhanced',
    'CT Thin Contrast': 'enhanced',
    'CT CECT THIN': 'enhanced',
    'CT 3D CT HEADORBIT': 'enhanced',
    'CT DE': 'enhanced',
}

SERIES_PRIORITY = {
    'plain_thick': 1,  # 最高优先级 - 标注用的序列
    'plain_thin': 2,
    'bone': 3,
    'enhanced': 4,
}


# ======================== 工具函数 ========================

def get_case_id(folder_name: str) -> int:
    """从文件夹名提取病例编号"""
    match = re.search(r'CQ500CT(\d+)', folder_name)
    if match:
        return int(match.group(1))
    return -1


def get_dicom_count(directory: str) -> int:
    """统计目录下的DICOM文件数量"""
    if not os.path.isdir(directory):
        return 0
    return len(glob.glob(os.path.join(directory, '*.dcm')) +
               glob.glob(os.path.join(directory, '*.DCM')))


def get_first_dicom_info(directory: str) -> dict:
    """从第一个DICOM文件读取关键元信息"""
    if not os.path.isdir(directory):
        return {}
    files = sorted(glob.glob(os.path.join(directory, '*.dcm')) +
                   glob.glob(os.path.join(directory, '*.DCM')))
    if not files:
        return {}
    try:
        import SimpleITK as sitk
        img = sitk.ReadImage(files[0])
        info = {
            'size': list(img.GetSize()),
            'spacing': list(img.GetSpacing()),
            'origin': list(img.GetOrigin()),
            'pixel_type': img.GetPixelIDTypeAsString(),
        }
        # 尝试读取DICOM tag
        try:
            reader = sitk.ImageFileReader()
            reader.SetFileName(files[0])
            reader.LoadPrivateTagsOff()
            reader.ReadImageInformation()
            tags = {}
            for tag_key in ['0010|0010', '0010|0020', '0010|0030', '0010|0040',
                           '0008|0020', '0008|0030', '0008|0060', '0008|0070',
                           '0018|0050', '0018|0088', '0028|0030', '0028|0010']:
                try:
                    tags[tag_key] = reader.GetMetaData(tag_key)
                except:
                    pass
            info['dicom_tags'] = tags
        except:
            pass
        return info
    except Exception as e:
        return {'error': str(e)}


# ======================== 主索引构建 ========================

def build_index(verbose=True):
    """
    扫描所有CQ500病例，构建完整索引
    返回: dict 包含所有病例的元数据
    """
    def log(msg):
        if verbose:
            print(msg)
            sys.stdout.flush()
    
    log("=" * 65)
    log("  CQ500 数据集索引构建")
    log("=" * 65)
    log(f"  数据源: {CQ500_ORIG_DIR}")
    
    # 获取所有病例文件夹
    case_folders = sorted(
        [f for f in os.listdir(CQ500_ORIG_DIR) 
         if os.path.isdir(os.path.join(CQ500_ORIG_DIR, f)) and f.startswith('CQ500CT')],
        key=lambda x: get_case_id(x)
    )
    log(f"  发现 {len(case_folders)} 个病例文件夹")
    
    # 加载CSV元数据
    reads_path = os.path.join(PROJECT_DATA_DIR, 'metadata', 'reads.csv')
    prob_path = os.path.join(PROJECT_DATA_DIR, 'metadata', 'prediction_probabilities.csv')
    
    reads_data = {}
    prob_data = {}
    
    if os.path.exists(reads_path):
        with open(reads_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                reads_data[row['name']] = row
    
    if os.path.exists(prob_path):
        with open(prob_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prob_data[row['name']] = row
    
    log(f"  加载 reads.csv: {len(reads_data)} 条标注")
    log(f"  加载 prediction_probabilities.csv: {len(prob_data)} 条预测")
    
    # 构建索引
    index = {
        'total_cases': len(case_folders),
        'cases': OrderedDict(),
        'series_summary': {},
        'statistics': {},
        'data_dir': CQ500_ORIG_DIR,
        'project_dir': PROJECT_DATA_DIR,
    }
    
    plain_thick_count = 0
    plain_thin_count = 0
    total_dicom_count = 0
    series_counts = {}
    
    for folder_name in case_folders:
        case_id_val = get_case_id(folder_name)
        case_key = f"CQ500-CT-{case_id_val}"
        case_dir = os.path.join(CQ500_ORIG_DIR, folder_name)
        study_dir = os.path.join(case_dir, 'Unknown Study')
        
        if not os.path.isdir(study_dir):
            continue
        
        # 扫描所有子目录
        series_list = []
        if os.path.isdir(study_dir):
            for sub_dir in sorted(os.listdir(study_dir)):
                full_path = os.path.join(study_dir, sub_dir)
                if os.path.isdir(full_path):
                    dcm_count = get_dicom_count(full_path)
                    if dcm_count > 0:
                        series_type = SERIES_TYPE_MAP.get(sub_dir, 'other')
                        series_info = {
                            'dir_name': sub_dir,
                            'dir_path': full_path,
                            'series_type': series_type,
                            'dicom_count': dcm_count,
                            'priority': SERIES_PRIORITY.get(series_type, 99),
                        }
                        series_list.append(series_info)
                        
                        # 统计
                        series_counts[sub_dir] = series_counts.get(sub_dir, 0) + 1
                        if series_type == 'plain_thick':
                            plain_thick_count += 1
                        elif series_type == 'plain_thin':
                            plain_thin_count += 1
                        total_dicom_count += dcm_count
        
        # 按优先级排序（厚层平扫优先）
        series_list.sort(key=lambda x: x['priority'])
        
        # 获取标注信息
        label_info = reads_data.get(case_key, {})
        pred_info = prob_data.get(case_key, {})
        
        # 判断是否有出血
        has_ich = False
        for reader_key in ['R1:ICH', 'R2:ICH', 'R3:ICH']:
            val = label_info.get(reader_key, '0')
            if val == '1':
                has_ich = True
                break
        
        # 计算血肿综合评分 (3位专家多数投票)
        ich_votes = sum(1 for r in ['R1:ICH', 'R2:ICH', 'R3:ICH'] if label_info.get(r, '0') == '1')
        iph_votes = sum(1 for r in ['R1:IPH', 'R2:IPH', 'R3:IPH'] if label_info.get(r, '0') == '1')
        ivh_votes = sum(1 for r in ['R1:IVH', 'R2:IVH', 'R3:IVH'] if label_info.get(r, '0') == '1')
        sdh_votes = sum(1 for r in ['R1:SDH', 'R2:SDH', 'R3:SDH'] if label_info.get(r, '0') == '1')
        edh_votes = sum(1 for r in ['R1:EDH', 'R2:EDH', 'R3:EDH'] if label_info.get(r, '0') == '1')
        sah_votes = sum(1 for r in ['R1:SAH', 'R2:SAH', 'R3:SAH'] if label_info.get(r, '0') == '1')
        
        fracture_votes = sum(1 for r in ['R1:Fracture', 'R2:Fracture', 'R3:Fracture'] if label_info.get(r, '0') == '1')
        mass_effect_votes = sum(1 for r in ['R1:MassEffect', 'R2:MassEffect', 'R3:MassEffect'] if label_info.get(r, '0') == '1')
        midline_shift_votes = sum(1 for r in ['R1:MidlineShift', 'R2:MidlineShift', 'R3:MidlineShift'] if label_info.get(r, '0') == '1')
        
        category = label_info.get('Category', '')
        pred_ich = float(pred_info.get('ICH', 0))
        pred_sdh = float(pred_info.get('SDH', 0))
        
        case_entry = {
            'case_id': case_id_val,
            'case_key': case_key,
            'folder_name': folder_name,
            'case_dir': case_dir,
            'study_dir': study_dir,
            'series': series_list,
            'has_series': len(series_list) > 0,
            'best_series_type': series_list[0]['series_type'] if series_list else None,
            'best_series_dir': series_list[0]['dir_path'] if series_list else None,
            'best_series_name': series_list[0]['dir_name'] if series_list else None,
            'total_dicom_files': sum(s['dicom_count'] for s in series_list),
            
            # 标注信息
            'category': category,
            'has_ich': has_ich,
            'ich_votes': ich_votes,
            'iph_votes': iph_votes,
            'ivh_votes': ivh_votes,
            'sdh_votes': sdh_votes,
            'edh_votes': edh_votes,
            'sah_votes': sah_votes,
            'fracture_votes': fracture_votes,
            'mass_effect_votes': mass_effect_votes,
            'midline_shift_votes': midline_shift_votes,
            'majority_ich': ich_votes >= 2,
            'majority_sdh': sdh_votes >= 2,
            'majority_edh': edh_votes >= 2,
            
            # AI预测
            'pred_ich': pred_ich,
            'pred_sdh': pred_sdh,
            
            # 标签
            'is_positive': ich_votes >= 2 or sdh_votes >= 2 or edh_votes >= 2,
            'is_negative': not (ich_votes >= 2 or sdh_votes >= 2 or edh_votes >= 2),
        }
        
        index['cases'][case_key] = case_entry
    
    # 统计数据
    positive_cases = sum(1 for c in index['cases'].values() if c['is_positive'])
    negative_cases = sum(1 for c in index['cases'].values() if c['is_negative'])
    
    index['statistics'] = {
        'total_cases': len(index['cases']),
        'cases_with_ct_plain': plain_thick_count,
        'cases_with_ct_plain_thin': plain_thin_count,
        'total_dicom_files': total_dicom_count,
        'positive_cases': positive_cases,
        'negative_cases': negative_cases,
        'ich_cases': sum(1 for c in index['cases'].values() if c['majority_ich']),
        'sdh_cases': sum(1 for c in index['cases'].values() if c['majority_sdh']),
        'edh_cases': sum(1 for c in index['cases'].values() if c['majority_edh']),
        'mass_effect_cases': sum(1 for c in index['cases'].values() if c['mass_effect_votes'] >= 2),
        'fracture_cases': sum(1 for c in index['cases'].values() if c['fracture_votes'] >= 2),
    }
    
    index['series_summary'] = dict(sorted(series_counts.items(), key=lambda x: -x[1]))
    
    log(f"\n[统计]")
    log(f"  有效索引病例: {len(index['cases'])}")
    log(f"  含CT平扫 (厚层): {plain_thick_count}")
    log(f"  含CT薄扫: {plain_thin_count}")
    log(f"  总DICOM文件数: {total_dicom_count:,}")
    log(f"  阳性病例 (出血): {positive_cases}")
    log(f"  阴性病例: {negative_cases}")
    log(f"  ICH阳性(多数投票): {index['statistics']['ich_cases']}")
    log(f"  SDH阳性: {index['statistics']['sdh_cases']}")
    log(f"  EDH阳性: {index['statistics']['edh_cases']}")
    
    return index


def export_index():
    """构建并导出索引"""
    index = build_index()
    
    # 保存索引
    save_path = os.path.join(PROJECT_DATA_DIR, 'processed', 'cq500_index.joblib')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    joblib.dump(index, save_path)
    print(f"\n[保存] 索引文件 -> {save_path}")
    
    # 同时导出JSON格式（人类可读）
    def _make_serializable(obj):
        if isinstance(obj, OrderedDict):
            return {k: _make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, dict):
            return {k: _make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_make_serializable(v) for v in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    json_path = os.path.join(PROJECT_DATA_DIR, 'processed', 'cq500_index.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(_make_serializable(index), f, ensure_ascii=False, indent=2)
    print(f"[保存] JSON索引 -> {json_path}")
    
    # 输出简要总结
    print(f"\n{'=' * 65}")
    print(f"  CQ500 索引构建完成！")
    print(f"  {'=' * 65}")
    stats = index['statistics']
    for k, v in stats.items():
        print(f"    {k}: {v}")
    
    return index


def load_index():
    """加载已构建的索引"""
    path = os.path.join(PROJECT_DATA_DIR, 'processed', 'cq500_index.joblib')
    if os.path.exists(path):
        return joblib.load(path)
    return None


# ======================== 病例查询接口 ========================

def get_case_info(index: dict, case_key: str) -> dict:
    """获取指定病例的信息"""
    return index['cases'].get(case_key)


def list_cases(index: dict, 
               series_type: str = None,
               is_positive: bool = None,
               has_ich: bool = None,
               has_sdh: bool = None,
               category: str = None,
               min_dicom: int = 10,
               max_results: int = None) -> list:
    """
    按条件筛选病例列表
    
    Args:
        series_type: 'plain_thick', 'plain_thin', 'bone', 'enhanced'
        is_positive: True=阳性, False=阴性
        has_ich: True=有ICH
        has_sdh: True=有SDH
        category: 'B1' or 'B2'
        min_dicom: 最少DICOM文件数
        max_results: 最大返回数
    """
    results = []
    for case_key, case in index['cases'].items():
        if series_type and case['best_series_type'] != series_type:
            continue
        if is_positive is not None and case['is_positive'] != is_positive:
            continue
        if has_ich is not None and case['majority_ich'] != has_ich:
            continue
        if has_sdh is not None and case['majority_sdh'] != has_sdh:
            continue
        if category and case['category'] != category:
            continue
        if case['total_dicom_files'] < min_dicom:
            continue
        
        results.append(case)
    
    results.sort(key=lambda x: x['case_id'])
    
    if max_results:
        results = results[:max_results]
    
    return results


def print_case_summary(case: dict):
    """打印病例摘要"""
    print(f"\n{'─' * 50}")
    print(f"  病例: {case['case_key']}")
    print(f"  分类: {case['category']}")
    print(f"  目录: {os.path.basename(case['case_dir'])}")
    print(f"  最佳序列: {case['best_series_name']} ({case['best_series_type']})")
    print(f"  DICOM总数: {case['total_dicom_files']}")
    
    labels = []
    if case['majority_ich']: labels.append('ICH')
    if case['majority_sdh']: labels.append('SDH')
    if case['majority_edh']: labels.append('EDH')
    if case['mass_effect_votes'] >= 2: labels.append('MassEffect')
    if case['midline_shift_votes'] >= 2: labels.append('MidlineShift')
    print(f"  标注: {', '.join(labels) if labels else '正常/阴性'}")
    print(f"  ICH投票: {case['ich_votes']}/3, SDH: {case['sdh_votes']}/3")
    print(f"  AI预测ICH概率: {case['pred_ich']:.3f}")
    print(f"  {'─' * 50}")


# ======================== 主入口 ========================

if __name__ == '__main__':
    index = export_index()
    
    print("\n\n[示例] 查看前5个病例:")
    for case_key in list(index['cases'].keys())[:5]:
        print_case_summary(index['cases'][case_key])
    
    print(f"\n\n[示例] 厚层平扫阳性病例数: {len(list_cases(index, series_type='plain_thick', is_positive=True))}")
    print(f"[示例] 薄层扫描病例数: {len(list_cases(index, series_type='plain_thin'))}")
