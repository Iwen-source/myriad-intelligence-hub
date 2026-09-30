"""
CQ500 DICOM -> NIfTI 批量转换器
=================================
将CQ500数据集的DICOM序列转换为NIfTI格式，便于快速加载和模型训练。

只转换标注用的厚层平扫序列（CT Plain及其变体），因为：
1. 这是官方标注使用的序列
2. 薄层数据量太大（173例 x ~300张/例 ≈ 30GB+）

转换后的NIfTI保存在 data/ct/cq500/volumes/ 目录下，
同时生成 volume_index.json 记录映射关系。
"""

import os, sys, glob, json, time, csv, gc
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

try:
    import SimpleITK as sitk
    HAS_SITK = True
except ImportError:
    HAS_SITK = False
    print("[FAIL] SimpleITK not installed. Cannot convert DICOMs.")

try:
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False

# ======================== 配置 ========================

CQ500_ORIG_DIR = r"D:\东软实习\CT_Junior\CQ500\CQ500_orig"
PROJECT_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'ct', 'cq500'))

VOLUMES_DIR = os.path.join(PROJECT_DATA_DIR, 'volumes')
PROCESSED_DIR = os.path.join(PROJECT_DATA_DIR, 'processed')
METADATA_DIR = os.path.join(PROJECT_DATA_DIR, 'metadata')

# 最多转换多少个病例（设为None则转换所有）
MAX_CASES = None  # None = 全部
# 只转换含CT Plain（含别名）的病例
ONLY_PLAIN_THICK = True
# 输出压缩NIfTI
COMPRESS_NIFTI = True

# 窗宽窗位（用于预处理归一化）
WINDOW_CENTER = 40
WINDOW_WIDTH = 80


# ======================== DICOM加载 ========================

def read_dicom_series(dicom_dir: str) -> tuple:
    """
    读取DICOM系列文件夹，返回 (numpy_volume, metadata_dict)
    """
    import SimpleITK as sitk
    sitk.ProcessObject_SetGlobalWarningDisplay(False)
    
    if not os.path.isdir(dicom_dir):
        return None, None
    
    try:
        reader = sitk.ImageSeriesReader()
        dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
        if not dicom_names or len(dicom_names) == 0:
            return None, None
        
        reader.SetFileNames(dicom_names)
        img = reader.Execute()
        volume = sitk.GetArrayFromImage(img).astype(np.float32)
        
        metadata = {
            'size': list(img.GetSize()),
            'spacing': list(img.GetSpacing()),
            'origin': list(img.GetOrigin()),
            'direction': list(img.GetDirection()),
            'num_slices': volume.shape[0],
            'dtype': str(volume.dtype),
        }
        
        # 尝试获取DICOM标签
        try:
            reader2 = sitk.ImageFileReader()
            reader2.SetFileName(dicom_names[0])
            reader2.ReadImageInformation()
            tags = {}
            for key in ['0010|0010', '0010|0020', '0010|0030', '0010|0040',
                       '0008|0020', '0008|0030', '0008|0060', '0008|0070',
                       '0018|0050', '0018|0088', '0028|0030']:
                try:
                    tags[key] = reader2.GetMetaData(key)
                except:
                    pass
            metadata['dicom_tags'] = tags
        except:
            pass
        
        return volume, metadata
    except Exception as e:
        print(f"    [FAIL] 读取失败: {e}")
        return None, None


def apply_ct_window(volume: np.ndarray, center: int = 40, width: int = 80) -> np.ndarray:
    """
    CT窗宽窗位归一化到 [0, 1]
    """
    half = width / 2.0
    low = center - half
    high = center + half
    windowed = np.clip(volume, low, high)
    normalized = (windowed - low) / (high - low)
    return normalized.astype(np.float32)


# ======================== 批量转换 ========================

def convert_all_cases():
    """批量转换所有CQ500病例的DICOM到NIfTI"""
    
    if not HAS_SITK:
        print("[FAIL] SimpleITK not available. Cannot convert.")
        return
    
    # 加载索引
    index_path = os.path.join(PROCESSED_DIR, 'cq500_index.joblib')
    if not os.path.exists(index_path):
        print("[FAIL] Index not found. Run cq500_index.py first.")
        return
    
    os.makedirs(VOLUMES_DIR, exist_ok=True)
    
    index = joblib.load(index_path)
    volume_index = {}
    
    # 筛选要转换的病例
    cases_to_convert = []
    for case_key, case in index['cases'].items():
        if ONLY_PLAIN_THICK:
            # 优先用厚层平扫
            thick_series = [s for s in case['series'] if s['series_type'] == 'plain_thick']
            if thick_series:
                cases_to_convert.append((case_key, case, thick_series[0]))
            else:
                # 没有厚层平扫就用最好的可用序列
                thin_series = [s for s in case['series'] if s['series_type'] in ('plain_thin',)]
                if thin_series:
                    cases_to_convert.append((case_key, case, thin_series[0]))
        else:
            # 转换所有有平扫序列的病例
            plain_series = [s for s in case['series'] if s['series_type'] in ('plain_thick', 'plain_thin')]
            if plain_series:
                cases_to_convert.append((case_key, case, plain_series[0]))
    
    # 限制数量
    if MAX_CASES and len(cases_to_convert) > MAX_CASES:
        cases_to_convert = cases_to_convert[:MAX_CASES]
    
    total = len(cases_to_convert)
    print(f"\n{'=' * 65}")
    print(f"  [CQ500] DICOM -> NIfTI 批量转换")
    print(f"  {'=' * 65}")
    print(f"  待转换: {total} 病例")
    print(f"  输出: {VOLUMES_DIR}")
    print(f"  {'=' * 65}\n")
    
    success = 0
    failed = 0
    skipped = 0
    total_dicoms = 0
    total_time = 0
    
    for i, (case_key, case, series_info) in enumerate(cases_to_convert):
        nii_filename = f"{case_key}.nii.gz" if COMPRESS_NIFTI else f"{case_key}.nii"
        nii_path = os.path.join(VOLUMES_DIR, nii_filename)
        
        # 跳过已转换的
        if os.path.exists(nii_path) and os.path.getsize(nii_path) > 1000:
            skipped += 1
            case_info = index['cases'].get(case_key, {})
            nii_size = os.path.getsize(nii_path) / (1024*1024)
            total_dicoms += case_info.get('total_dicom_files', 0)
            if (i + 1) % 50 == 0 or i == 0:
                print(f"   [{i+1}/{total}] [SKIP] {case_key} (已存在, {nii_size:.1f}MB)")
            continue
        
        dicom_dir = series_info['dir_path']
        series_name = series_info['dir_name']
        dcm_count = series_info['dicom_count']
        
        # 跳过DICOM文件太少的
        if dcm_count < 5:
            skipped += 1
            continue
        
        t_start = time.time()
        
        # 读取DICOM序列
        volume, meta = read_dicom_series(dicom_dir)
        
        if volume is None:
            failed += 1
            print(f"   [{i+1}/{total}] [FAIL] {case_key} (读取失败)")
            continue
        
        # 使用nibabel写入NIfTI（支持中文路径）
        try:
            import nibabel as nib
            # 获取SimpleITK图像来保留空间信息
            sitk.ProcessObject_SetGlobalWarningDisplay(False)
            reader = sitk.ImageSeriesReader()
            dicom_names = reader.GetGDCMSeriesFileNames(dicom_dir)
            reader.SetFileNames(dicom_names)
            sitk_img = reader.Execute()
            
            # SimpleITK: (x,y,z), NumPy: (z,y,x)
            # 直接使用GetArrayFromImage得到(z,y,x)
            arr = sitk.GetArrayFromImage(sitk_img)
            spacing = list(sitk_img.GetSpacing())
            # nibabel affine: 需要对SimpleITK的空间信息做转换
            # SimpleITK spacing = (sx, sy, sz), array shape = (nz, ny, nx)
            sx, sy, sz = spacing[0], spacing[1], spacing[2]
            origin = sitk_img.GetOrigin()
            
            affine = np.array([
                [-sx, 0, 0, origin[0]],
                [0, -sy, 0, origin[1]],
                [0, 0, sz, origin[2]],
                [0, 0, 0, 1]
            ], dtype=np.float32)
            
            nii = nib.Nifti1Image(arr, affine)
            nib.save(nii, nii_path)
            
            elapsed = time.time() - t_start
            total_time += elapsed
            success += 1
            total_dicoms += dcm_count
            
            nii_size = os.path.getsize(nii_path) / (1024*1024)
            print(f"   [{i+1}/{total}] [OK] {case_key} | {series_name} | {dcm_count}张 -> {nii_size:.1f}MB | {elapsed:.1f}s")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            failed += 1
            print(f"   [{i+1}/{total}] [FAIL] {case_key} (写入失败: {e})")
            continue
        
        # 记录到volume_index
        volume_index[case_key] = {
            'nii_path': nii_path,
            'nii_filename': nii_filename,
            'nii_size_bytes': os.path.getsize(nii_path),
            'series_name': series_name,
            'series_type': series_info['series_type'],
            'dicom_count': dcm_count,
            'volume_shape': list(volume.shape) if volume is not None else None,
            'spacing': list(meta.get('spacing', [])) if meta else [],
            'converted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'is_positive': case['is_positive'],
            'category': case['category'],
        }
        
        # 每转换一定数量后保存进度
        if (success + failed) % 25 == 0:
            vindex_path = os.path.join(PROCESSED_DIR, 'volume_index.json')
            with open(vindex_path, 'w') as f:
                json.dump(volume_index, f, ensure_ascii=False, indent=2)
            print(f"   [进度保存] {len(volume_index)} 个病例")
        
        gc.collect()
    
    # 最终保存volume_index
    vindex_path = os.path.join(PROCESSED_DIR, 'volume_index.json')
    with open(vindex_path, 'w') as f:
        json.dump(volume_index, f, ensure_ascii=False, indent=2)
    
    # 同时保存joblib格式
    vindex_joblib_path = os.path.join(PROCESSED_DIR, 'volume_index.joblib')
    joblib.dump(volume_index, vindex_joblib_path)
    
    print(f"\n{'=' * 65}")
    print(f"  [完成] DICOM -> NIfTI 转换结束")
    print(f"  {'=' * 65}")
    print(f"  成功: {success}")
    print(f"  失败: {failed}")
    print(f"  跳过: {skipped}")
    print(f"  总耗时: {total_time:.1f}s")
    print(f"  总DICOM: {total_dicoms}")
    print(f"  索引位置: {vindex_path}")
    print(f"{'=' * 65}\n")


def convert_single_case(case_key: str):
    """转换单个病例（用于调试或增量转换）"""
    index_path = os.path.join(PROCESSED_DIR, 'cq500_index.joblib')
    if not os.path.exists(index_path):
        print("[FAIL] Index not found.")
        return
    
    index = joblib.load(index_path)
    case = index['cases'].get(case_key)
    if not case:
        print(f"[FAIL] Case {case_key} not found.")
        return
    
    # 找到最佳序列
    thick_series = [s for s in case['series'] if s['series_type'] == 'plain_thick']
    use_series = thick_series[0] if thick_series else case['series'][0]
    
    print(f"转换 {case_key}: {use_series['dir_name']} ({use_series['dicom_count']} DICOMs)")
    
    volume, meta = read_dicom_series(use_series['dir_path'])
    if volume is None:
        print("  [FAIL] 读取失败")
        return
    
    nii_path = os.path.join(VOLUMES_DIR, f"{case_key}.nii.gz")
    
    try:
        import nibabel as nib
        sitk.ProcessObject_SetGlobalWarningDisplay(False)
        reader = sitk.ImageSeriesReader()
        names = reader.GetGDCMSeriesFileNames(use_series['dir_path'])
        reader.SetFileNames(names)
        sitk_img = reader.Execute()
        arr = sitk.GetArrayFromImage(sitk_img)
        spacing = list(sitk_img.GetSpacing())
        origin = sitk_img.GetOrigin()
        sx, sy, sz = spacing[0], spacing[1], spacing[2]
        affine = np.array([
            [-sx, 0, 0, origin[0]],
            [0, -sy, 0, origin[1]],
            [0, 0, sz, origin[2]],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        nii = nib.Nifti1Image(arr, affine)
        nib.save(nii, nii_path)
        size = os.path.getsize(nii_path) / (1024*1024)
        print(f"  [OK] 写入成功: {nii_path} ({size:.1f}MB)")
    except Exception as e:
        print(f"  [FAIL] 写入失败: {e}")
        return None, None
    
    return volume, meta


# ======================== 数据统计 ========================

def print_dataset_stats():
    """打印CQ500数据集统计信息"""
    index_path = os.path.join(PROCESSED_DIR, 'cq500_index.joblib')
    if not os.path.exists(index_path):
        print("[FAIL] Index not found.")
        return
    
    index = joblib.load(index_path)
    stats = index['statistics']
    
    print(f"\n{'=' * 65}")
    print(f"  CQ500 数据集统计")
    print(f"  {'=' * 65}")
    print(f"  总病例数: {stats['total_cases']}")
    print(f"  阳性病例 (出血): {stats['positive_cases']}")
    print(f"  阴性病例: {stats['negative_cases']}")
    print(f"  ICH阳性: {stats['ich_cases']}")
    print(f"  SDH阳性: {stats['sdh_cases']}")
    print(f"  EDH阳性: {stats['edh_cases']}")
    print(f"  占位效应: {stats['mass_effect_cases']}")
    print(f"  骨折: {stats['fracture_cases']}")
    print(f"  总DICOM: {stats['total_dicom_files']:,}")
    
    # 统计已转换的NIfTI
    nii_files = sorted(glob.glob(os.path.join(VOLUMES_DIR, '*.nii.gz')))
    print(f"\n  已转换NIfTI: {len(nii_files)}")
    total_nii_size = sum(os.path.getsize(f) for f in nii_files) / (1024**3)
    print(f"  NIfTI总大小: {total_nii_size:.2f} GB")
    
    # 出血类型分布
    ich_count = stats['ich_cases']
    sdh_count = stats['sdh_cases']
    edh_count = stats['edh_cases']
    
    if ich_count > 0:
        print(f"\n  出血类型分布:")
        print(f"    脑内出血(ICH): {ich_count} ({ich_count/stats['positive_cases']*100:.1f}%)")
        print(f"    硬膜下血肿(SDH): {sdh_count} ({sdh_count/stats['positive_cases']*100:.1f}%)")
        print(f"    硬膜外血肿(EDH): {edh_count} ({edh_count/stats['positive_cases']*100:.1f}%)")
    
    print(f"{'=' * 65}\n")


# ======================== 主入口 ========================

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'stats':
            print_dataset_stats()
        elif sys.argv[1] == 'single' and len(sys.argv) > 2:
            convert_single_case(sys.argv[2])
        else:
            print(f"用法: python {sys.argv[0]} [stats|single <case_key>]")
    else:
        convert_all_cases()
