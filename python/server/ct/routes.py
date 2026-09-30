"""CT 影像工作台 — Flask 路由（增强版 + CQ500支持）"""
import base64
import io
import json
import os
import time
from io import BytesIO
from pathlib import Path

import numpy as np
from flask import Blueprint, jsonify, request

from .session import _get_or_create_session, _get_cache, _set_cache, make_response, DATA_DIR, OUTPUT_DIR
from .image_processing import (
    apply_window, filter_slice, edge_slice_advanced, threshold_slice,
    view_planes, build_3d_mask, build_metal_artifact_mask,
    compute_histogram_data, compute_ct_statistics,
    array_to_b64, fig_to_b64, overlay_to_b64
)
from .cq500_loader import get_case_list, load_cq500_volume, get_dataset_stats
from .segment_model import load_seg_model, predict_segmentation
from .metal_model import load_metal_model, detect_metal_artifact
from .report_model import load_report_classifier, predict_report

ct_bp = Blueprint('ct_workstation', __name__, url_prefix='/api/medical/ct')

import logging
log = logging.getLogger(__name__)


def _safe_ct_path(user_path):
    """Resolve a user-supplied CT path to an absolute path inside DATA_DIR.

    Accepts an absolute path already inside DATA_DIR, or a relative path
    (joined onto DATA_DIR). Returns ``None`` if the path is empty or escapes
    DATA_DIR, preventing arbitrary-file read (LFI) via the ``path``/``local_path``
    request fields.
    """
    if not user_path:
        return None
    try:
        raw = Path(user_path)
        candidate = raw if raw.is_absolute() else (DATA_DIR / raw)
        candidate = candidate.resolve()
        candidate.relative_to(DATA_DIR.resolve())
        return candidate
    except (ValueError, OSError, RuntimeError):
        return None


def _get_sid(req):
    """Get sessionId from query params or JSON body"""
    sid = req.args.get('sessionId')
    if sid:
        return sid
    try:
        data = req.get_json(silent=True) or {}
        return data.get('sessionId', 'default')
    except Exception:
        return 'default'


@ct_bp.route('/session/new', methods=['GET'])
def new_session():
    sid = _get_or_create_session()
    return jsonify(make_response(success=True, data={"sessionId": sid}, session_id=sid))


@ct_bp.route('/session/info', methods=['GET'])
def session_info():
    sid = _get_sid(request)
    cache = _get_cache(sid)
    if not cache:
        return jsonify(make_response(success=False, error="Session not found", session_id=sid)), 404
    return jsonify(make_response(success=True, data={
        "sessionId": sid, "created": cache.get('created'),
        "hasVolume": 'volume' in cache, "hasReport": 'report' in cache
    }, session_id=sid))


@ct_bp.route('/load', methods=['POST'])
def load_ct_data():
    """加载CT数据，支持多种模式"""
    sid = _get_sid(request)
    cache = _get_cache(sid) or {}
    cache['created'] = time.time()

    if 'volume' in cache:
        return jsonify(make_response(success=True, data={
            "loaded": True, "message": "Using cached volume",
            "sessionId": sid, "shape": list(cache['volume'].shape),
            "z_slices": cache['volume'].shape[0],
            "width": cache['volume'].shape[2], "height": cache['volume'].shape[1]
        }, session_id=sid))

    import SimpleITK as sitk
    volume = None
    source = None

    data = request.get_json() or {}
    mode = data.get('mode', 'auto')
    file_path = data.get('path', '')
    local_path = data.get('local_path', '')

    # 安全校验：用户提供的文件路径必须落在 CT 数据目录内（防任意文件读取 LFI）
    if file_path:
        safe_fp = _safe_ct_path(file_path)
        if safe_fp is None:
            return jsonify(make_response(success=False, error="路径不在允许的CT数据目录内")), 403
        file_path = str(safe_fp)

    # 优先处理 local_path (用户从本机选择的文件路径)
    if local_path:
        local_path = local_path.strip()
        safe_local = _safe_ct_path(local_path)
        if safe_local is None:
            return jsonify(make_response(success=False, error="路径不在允许的CT数据目录内")), 403
        local_path = str(safe_local)
        if safe_local.exists():
            mode = 'local_file'
            file_path = local_path
            log.info(f"Loading from user-specified path: {local_path}")

    if mode == 'dicom_series':
        if file_path and Path(file_path).exists():
            dcm_path = Path(file_path)
        elif file_path:
            dcm_path = DATA_DIR / file_path
        else:
            for subdir in ['dicom/CT PLAIN THIN', 'dicom/CT Plain', 'dicom']:
                candidate = DATA_DIR / subdir
                if candidate.exists() and list(candidate.glob('*.dcm')):
                    dcm_path = candidate
                    break
            else:
                return jsonify(make_response(success=False, error="未找到DICOM序列")), 404

        if dcm_path.is_dir():
            files = sorted(dcm_path.glob('*.dcm'))
            if not files:
                return jsonify(make_response(success=False, error=f"目录中无DICOM文件: {dcm_path}")), 404
            try:
                reader = sitk.ImageSeriesReader()
                reader.SetFileNames([str(f) for f in files])
                img = reader.Execute()
                volume = sitk.GetArrayFromImage(img)
                source = f"DICOM序列 ({len(files)}张, {dcm_path.name})"
            except Exception as e:
                return jsonify(make_response(success=False, error=f"DICOM加载失败: {e}")), 500
        elif dcm_path.suffix == '.dcm':
            try:
                img = sitk.ReadImage(str(dcm_path))
                volume = sitk.GetArrayFromImage(img)
                source = f"单张DICOM ({dcm_path.name})"
            except Exception as e:
                return jsonify(make_response(success=False, error=f"DICOM加载失败: {e}")), 500

    elif mode == 'mhd_volume':
        if file_path and Path(file_path).exists():
            mhd_path = Path(file_path)
        elif file_path:
            mhd_path = DATA_DIR / file_path
        else:
            candidates = list(DATA_DIR.glob('*.mhd'))
            if not candidates:
                return jsonify(make_response(success=False, error="未找到MHD文件")), 404
            mhd_path = candidates[0]
        try:
            img = sitk.ReadImage(str(mhd_path))
            volume = sitk.GetArrayFromImage(img)
            source = f"MHD ({mhd_path.name})"
        except Exception as e:
            return jsonify(make_response(success=False, error=f"MHD加载失败: {e}")), 500

    elif mode == 'single_image':
        if file_path and Path(file_path).exists():
            img_path = Path(file_path)
        elif file_path:
            img_path = DATA_DIR / file_path
        else:
            single_dir = DATA_DIR / 'single'
            candidates = list(single_dir.glob('*.*')) if single_dir.exists() else []
            if not candidates:
                return jsonify(make_response(success=False, error="未找到单张图像")), 404
            img_path = candidates[0]
        try:
            if img_path.suffix == '.dcm':
                img = sitk.ReadImage(str(img_path))
            else:
                from PIL import Image
                img_pil = Image.open(str(img_path)).convert('L')
                img = sitk.GetImageFromArray(np.array(img_pil))
            volume = sitk.GetArrayFromImage(img)
            if volume.ndim == 2:
                volume = volume[np.newaxis, :, :]
            source = f"单张图像 ({img_path.name})"
        except Exception as e:
            return jsonify(make_response(success=False, error=f"图像加载失败: {e}")), 500

    elif mode == 'nifti_nrrd':
        if file_path and Path(file_path).exists():
            vol_path = Path(file_path)
        elif file_path:
            vol_path = DATA_DIR / file_path
        else:
            from .cq500_loader import CQ500_VOLUMES_DIR
            for pattern in ['*.nii*', '*.nrrd']:
                # 先在 DATA_DIR 找
                candidates = list(DATA_DIR.glob(pattern))
                if not candidates:
                    # 再到 CQ500 volumes 找
                    candidates = list(Path(CQ500_VOLUMES_DIR).glob(pattern))
                if candidates:
                    vol_path = candidates[0]
                    break
            else:
                return jsonify(make_response(success=False, error="未找到NIfTI/NRRD文件")), 404
        try:
            if vol_path.suffix == '.nrrd':
                import nrrd
                vol, _ = nrrd.read(str(vol_path))
                volume = vol.astype(np.float32)
            elif vol_path.suffix == '.gz':
                try:
                    img = sitk.ReadImage(str(vol_path))
                    volume = sitk.GetArrayFromImage(img)
                except Exception:
                    import nibabel as nib
                    nii = nib.load(str(vol_path))
                    vol = nii.get_fdata()
                    volume = np.transpose(vol, (2, 1, 0)).astype(np.float32)
            else:
                img = sitk.ReadImage(str(vol_path))
                volume = sitk.GetArrayFromImage(img)
            source = f"体数据 ({vol_path.name})"
        except Exception as e:
            return jsonify(make_response(success=False, error=f"体数据加载失败: {e}")), 500

    elif mode == 'local_file':
        # 用户从本机选择的文件路径（已在入口处白名单校验）
        resolved_path = local_path if local_path else file_path
        if not resolved_path or not os.path.exists(resolved_path):
            return jsonify(make_response(success=False, error=f"路径不存在: {resolved_path}")), 404
        resolved_path = str(Path(resolved_path))
        ext = Path(resolved_path).suffix.lower()
        
        # 如果路径是目录 => DICOM目录
        if os.path.isdir(resolved_path):
            try:
                import SimpleITK as sitk2
                sitk2.ProcessObject_SetGlobalWarningDisplay(False)
                reader = sitk2.ImageSeriesReader()
                dicom_names = reader.GetGDCMSeriesFileNames(resolved_path)
                if dicom_names:
                    reader.SetFileNames(dicom_names)
                    volume = sitk2.GetArrayFromImage(reader.Execute())
                    source = f"DICOM序列 ({len(dicom_names)}张)"
                else:
                    files = sorted(Path(resolved_path).glob('*.dcm'))
                    if files:
                        reader.SetFileNames([str(f) for f in files])
                        volume = sitk2.GetArrayFromImage(reader.Execute())
                        source = f"DICOM序列 ({len(files)}张)"
            except Exception as e:
                return jsonify(make_response(success=False, error=f"读取DICOM目录失败: {e}")), 500
        else:
            # 单文件
            try:
                if ext == '.mhd':
                    img = sitk.ReadImage(resolved_path)
                    volume = sitk.GetArrayFromImage(img)
                    source = f"MHD - {Path(resolved_path).name}"
                elif ext in ('.nii', '.gz'):
                    if resolved_path.endswith('.nii') or resolved_path.endswith('.nii.gz'):
                        try:
                            import nibabel as nib
                            nii = nib.load(resolved_path)
                            vol = nii.get_fdata()
                            vol = np.transpose(vol, (2, 1, 0)).astype(np.float32) if vol.ndim == 3 else vol
                            volume = vol
                        except Exception as e2:
                            try:
                                img = sitk.ReadImage(resolved_path)
                                volume = sitk.GetArrayFromImage(img)
                            except:
                                raise e2
                        source = f"NIfTI - {Path(resolved_path).name}"
                elif ext == '.nrrd':
                    import nrrd
                    vol, _ = nrrd.read(resolved_path)
                    volume = vol.astype(np.float32)
                    source = f"NRRD - {Path(resolved_path).name}"
                elif ext == '.dcm':
                    img = sitk.ReadImage(resolved_path)
                    volume = sitk.GetArrayFromImage(img)
                    source = f"DICOM - {Path(resolved_path).name}"
                elif ext in ('.png', '.jpg', '.jpeg', '.bmp'):
                    from PIL import Image
                    img_pil = Image.open(resolved_path).convert('L')
                    volume = sitk.GetArrayFromImage(sitk.GetImageFromArray(np.array(img_pil)))
                    if volume.ndim == 2:
                        volume = volume[np.newaxis, :, :]
                    source = f"图像 - {Path(resolved_path).name}"
                else:
                    return jsonify(make_response(success=False, error=f"不支持的文件格式: {ext}")), 400
            except Exception as e:
                return jsonify(make_response(success=False, error=f"读取文件失败: {e}")), 500

    else:
        candidates = [('nifti', lambda: list(DATA_DIR.glob('*.nii*'))),
                      ('nrrd', lambda: list(DATA_DIR.glob('*.nrrd'))),
                      ('mhd', lambda: list(DATA_DIR.glob('*.mhd')))]
        for name, finder in candidates:
            files = finder()
            if files:
                try:
                    f = files[0]
                    if name == 'nrrd':
                        import nrrd
                        vol, _ = nrrd.read(str(f))
                        volume = vol.astype(np.float32)
                    elif f.suffix == '.gz':
                        import nibabel as nib
                        nii = nib.load(str(f))
                        vol = nii.get_fdata()
                        volume = np.transpose(vol, (2, 1, 0)).astype(np.float32)
                    else:
                        img = sitk.ReadImage(str(f))
                        volume = sitk.GetArrayFromImage(img)
                    source = f"{f.name}"
                    break
                except Exception:
                    continue
        if volume is None:
            # fallback: 尝试从 CQ500 volumes 目录加载
            from .cq500_loader import CQ500_VOLUMES_DIR
            cq500_vols = sorted(Path(CQ500_VOLUMES_DIR).glob('CQ500-CT-*.nii.gz'))
            if cq500_vols:
                try:
                    f = cq500_vols[0]
                    import nibabel as nib
                    nii = nib.load(str(f))
                    vol = nii.get_fdata()
                    volume = np.transpose(vol, (2, 1, 0)).astype(np.float32)
                    source = f"CQ500/{f.name}"
                except Exception:
                    pass
        if volume is None:
            for subdir in ['dicom/CT PLAIN THIN', 'dicom/CT Plain', 'dicom']:
                dcm_dir = DATA_DIR / subdir
                if dcm_dir.exists():
                    files = sorted(dcm_dir.glob('*.dcm'))
                    if files:
                        try:
                            reader = sitk.ImageSeriesReader()
                            reader.SetFileNames([str(f) for f in files])
                            volume = sitk.GetArrayFromImage(reader.Execute())
                            source = f"DICOM序列 ({len(files)}张)"
                            break
                        except Exception:
                            continue
        if volume is None:
            return jsonify(make_response(success=False, error="未找到CT数据，请确定data/ct/目录下有数据文件")), 404

    if volume.ndim == 2:
        volume = volume[np.newaxis, :, :]
    elif volume.ndim > 3:
        volume = np.squeeze(volume)
    if volume.ndim == 3 and volume.shape[0] > volume.shape[2]:
        volume = np.transpose(volume, (2, 1, 0))

    cache['volume'] = volume
    cache['source'] = source
    _set_cache(sid, cache)

    return jsonify(make_response(success=True, data={
        "loaded": True, "shape": list(volume.shape),
        "z_slices": volume.shape[0], "width": volume.shape[2],
        "height": volume.shape[1], "dtype": str(volume.dtype),
        "source": source, "description": source,
        "sessionId": sid, "min": float(volume.min()),
        "max": float(volume.max()), "mean": float(volume.mean())
    }, session_id=sid))


@ct_bp.route('/slice', methods=['POST'])
def get_slice():
    sid = _get_sid(request)
    data = request.get_json() or {}
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    volume = cache['volume']
    z = data.get('z', volume.shape[0] // 2)
    ww = data.get('ww', 80)
    wl = data.get('wl', 40)
    use_filter = data.get('filter')
    variance = data.get('variance', 1.0)
    slice_2d = np.rot90(volume[z, :, :])
    windowed = apply_window(slice_2d, ww, wl)
    if use_filter and use_filter != '不滤波':
        windowed = filter_slice(windowed.astype(np.float32), use_filter, variance)
        windowed = np.clip(windowed, 0, 255).astype(np.uint8)
    return jsonify(make_response(success=True, data={
        "image": array_to_b64(windowed), "z": z, "depth": volume.shape[0]
    }, session_id=sid))


@ct_bp.route('/mpr', methods=['POST'])
def get_mpr():
    sid = _get_sid(request)
    data = request.get_json() or {}
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    volume = cache['volume']
    z = data.get('z', volume.shape[0] // 2)
    y = data.get('y', volume.shape[1] // 2)
    x = data.get('x', volume.shape[2] // 2)
    ww = data.get('ww', 80)
    wl = data.get('wl', 40)
    axial, coronal, sagittal = view_planes(volume, z, y, x)
    return jsonify(make_response(success=True, data={
        "axial": array_to_b64(apply_window(axial, ww, wl)),
        "coronal": array_to_b64(apply_window(coronal, ww, wl)),
        "sagittal": array_to_b64(apply_window(sagittal, ww, wl)),
        "center": {"z": z, "y": y, "x": x}
    }, session_id=sid))


@ct_bp.route('/filter-compare', methods=['POST'])
def filter_compare():
    sid = _get_sid(request)
    data = request.get_json() or {}
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    volume = cache['volume']
    z = data.get('z', volume.shape[0] // 2)
    ww = data.get('ww', 80)
    wl = data.get('wl', 40)
    slice_2d = np.rot90(volume[z, :, :])
    original = apply_window(slice_2d, ww, wl)
    results = {"original": array_to_b64(original)}
    for name, var in [("gaussian_1", 0.5), ("gaussian_2", 1.0), ("gaussian_3", 2.0),
                       ("median_3", 0.3), ("median_5", 0.5)]:
        mode = 'gaussian' if 'gaussian' in name else 'median'
        filtered = filter_slice(slice_2d.astype(np.float32), mode, var)
        results[name] = array_to_b64(apply_window(filtered, ww, wl).astype(np.uint8))
    return jsonify(make_response(success=True, data=results, session_id=sid))


@ct_bp.route('/histogram', methods=['POST'])
def get_histogram():
    sid = _get_sid(request)
    data = request.get_json() or {}
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    volume = cache['volume']
    z = data.get('z', volume.shape[0] // 2)
    slice_2d = np.rot90(volume[z, :, :])
    return jsonify(make_response(success=True, data=compute_histogram_data(slice_2d), session_id=sid))


@ct_bp.route('/statistics', methods=['POST'])
def get_statistics():
    sid = _get_sid(request)
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    return jsonify(make_response(success=True, data=compute_ct_statistics(cache['volume']), session_id=sid))


@ct_bp.route('/segment-3d', methods=['POST'])
def segment_3d():
    sid = _get_sid(request)
    data = request.get_json() or {}
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    volume = cache['volume']

    # 尝试加载深度学习模型，失败则回退到阈值分割
    if not hasattr(segment_3d, '_model'):
        segment_3d._model = load_seg_model()

    if segment_3d._model is not None:
        try:
            model = segment_3d._model
            mask = predict_segmentation(model, volume)
            is_dl = True
        except Exception as e:
            log.warning("三维分割模型推理失败，回退阈值: %s", e)
            lower = data.get('lower', 100)
            upper = data.get('upper', 300)
            mask = build_3d_mask(volume, lower, upper)
            is_dl = False
    else:
        lower = data.get('lower', 100)
        upper = data.get('upper', 300)
        mask = build_3d_mask(volume, lower, upper)
        is_dl = False

    masks = {}
    for i in range(0, min(mask.shape[0], volume.shape[0]), max(1, mask.shape[0] // 6)):
        z = min(i, mask.shape[0] - 1)
        gray_plane = apply_window(np.rot90(volume[z, :, :]), 80, 40)
        mask_plane = np.rot90(mask[z, :, :])
        masks[f"z_{z:03d}"] = overlay_to_b64(gray_plane.astype(np.float32), mask_plane)
    return jsonify(make_response(success=True, data={
        "maskShape": list(mask.shape), "voxelCount": int(np.sum(mask)),
        "totalVoxels": int(mask.size), "masks": masks,
        "boneRatio": float(np.sum(mask) / mask.size) if mask.size > 0 else 0,
        "is_deep_learning": is_dl,
    }, session_id=sid))


@ct_bp.route('/metal-detect', methods=['POST'])
def metal_detect():
    sid = _get_sid(request)
    data = request.get_json() or {}
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    volume = cache['volume']

    # 尝试加载深度学习模型，失败则回退到HU阈值
    if not hasattr(metal_detect, '_model'):
        metal_detect._model = load_metal_model()

    if metal_detect._model is not None:
        try:
            model = metal_detect._model
            mask = detect_metal_artifact(model, volume)
            is_dl = True
        except Exception as e:
            log.warning("金属伪影模型推理失败，回退阈值: %s", e)
            threshold = data.get('threshold', 2000)
            mask = build_metal_artifact_mask(volume, threshold)
            is_dl = False
    else:
        threshold = data.get('threshold', 2000)
        mask = build_metal_artifact_mask(volume, threshold)
        is_dl = False

    z = data.get('z', volume.shape[0] // 2)
    gray_plane = apply_window(np.rot90(volume[z, :, :]), 80, 40)
    mask_plane = np.rot90(mask[z, :, :])
    return jsonify(make_response(success=True, data={
        "overlay": overlay_to_b64(gray_plane.astype(np.float32), mask_plane, mask_color=(1, 0, 0)),
        "metalVoxels": int(np.sum(mask)), "totalVoxels": int(mask.size),
        "metalRatio": float(np.sum(mask) / mask.size) if mask.size > 0 else 0,
        "is_deep_learning": is_dl,
    }, session_id=sid))


@ct_bp.route('/montage', methods=['POST'])
def generate_montage():
    sid = _get_sid(request)
    data = request.get_json() or {}
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    volume = cache['volume']
    cols = data.get('cols', 6)
    ww = data.get('ww', 80)
    wl = data.get('wl', 40)
    n = min(volume.shape[0], cols * 4)
    step = max(1, volume.shape[0] // n)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 2, rows * 2))
    axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]
    for i in range(n):
        z = i * step
        if z >= volume.shape[0]:
            break
        axes[i].imshow(apply_window(np.rot90(volume[z, :, :]), ww, wl), cmap='gray')
        axes[i].axis('off')
        axes[i].set_title(f'Slice {z}', fontsize=8)
    for j in range(n, len(axes)):
        axes[j].axis('off')
    plt.tight_layout()
    return jsonify(make_response(success=True, data={"montage": fig_to_b64(fig)}, session_id=sid))


@ct_bp.route('/report', methods=['POST'])
def generate_report():
    sid = _get_sid(request)
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    volume = cache['volume']

    # 尝试使用深度学习分类器生成报告
    if not hasattr(generate_report, '_model'):
        generate_report._model = load_report_classifier()

    if generate_report._model is not None:
        try:
            model = generate_report._model
            clf_result = predict_report(model, volume)
            is_dl = True
        except Exception as e:
            log.warning("报告分类器推理失败，回退统计报告: %s", e)
            clf_result = None
            is_dl = False
    else:
        clf_result = None
        is_dl = False

    stats = compute_ct_statistics(volume)

    if clf_result and clf_result.get("findings"):
        findings = [f"CT扫描显示{volume.shape[0]}层头部影像", f"平均HU值: {float(volume.mean()):.1f}"]
        findings.extend(clf_result["findings"])
        impression = clf_result["impression"]
        recommendations = ["Clinical correlation recommended."]
        if clf_result.get("positive_labels"):
            recommendations.append("建议进一步影像学检查或临床评估。")
        else:
            recommendations.append("Follow-up if symptoms persist.")
    else:
        findings = [
            f"CT扫描显示{volume.shape[0]}层头部影像",
            f"平均HU值: {float(volume.mean()):.1f}",
            "未检测到明显急性颅内异常"
        ]
        impression = "No acute intracranial abnormality detected."
        recommendations = ["Clinical correlation recommended.", "Follow-up if symptoms persist."]

    report = {
        "patient_id": f"CT-{sid[:8].upper()}",
        "modality": "CT", "body_part": "Head",
        "total_slices": volume.shape[0],
        "volume_dimensions": list(volume.shape),
        "mean_hu": round(float(volume.mean()), 1),
        "std_hu": round(float(volume.std()), 1),
        "scan_info": {"slices": volume.shape[0], "voxel_count": volume.size},
        "hu_statistics": stats,
        "tissue_analysis": stats,
        "findings": findings,
        "impression": impression,
        "recommendations": recommendations,
        "is_deep_learning": is_dl,
        "report_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if clf_result and clf_result.get("probabilities"):
        report["ai_probabilities"] = clf_result["probabilities"]
        report["ai_positive_labels"] = clf_result["positive_labels"]

    cache['report'] = report
    _set_cache(sid, cache)
    return jsonify(make_response(success=True, data=report, session_id=sid))


@ct_bp.route('/export-mask', methods=['POST'])
def export_mask():
    sid = _get_sid(request)
    data = request.get_json() or {}
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400
    volume = cache['volume']
    try:
        lower = int(data.get('lower', 100))
        upper = int(data.get('upper', 300))
    except (TypeError, ValueError):
        return jsonify(make_response(success=False, error="lower/upper 必须是整数")), 400
    if not (-2000 <= lower < upper <= 4000):
        return jsonify(make_response(success=False, error="lower/upper 超出合法HU范围")), 400
    mask = build_3d_mask(volume, lower, upper)
    # 仅保留字母数字/下划线/连字符，杜绝文件名路径穿越
    safe_sid = ''.join(ch for ch in sid if ch.isalnum() or ch in '_-')[:8] or 'sid'
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mask_path = OUTPUT_DIR / f"mask_{safe_sid}_{lower}_{upper}.npy"
    np.save(str(mask_path), mask)
    return jsonify(make_response(success=True, data={
        "path": str(mask_path), "shape": list(mask.shape),
        "voxelCount": int(np.sum(mask))
    }, session_id=sid))


@ct_bp.route('/window-presets', methods=['GET'])
def get_window_presets():
    presets = {
        "软组织窗": {"ww": 350, "wl": 50},
        "脑组织窗": {"ww": 80, "wl": 40},
        "骨窗": {"ww": 2000, "wl": 500},
        "肺窗": {"ww": 1500, "wl": -500},
        "自定义": {"ww": 80, "wl": 40}
    }
    return jsonify(make_response(success=True, data={"presets": presets}, session_id=_get_sid(request)))


@ct_bp.route('/data-files', methods=['GET'])
def list_data_files():
    result = {"dicoms": [], "mhd": [], "single": [], "root": []}
    for subdir in DATA_DIR.glob('**/dicom/*'):
        if subdir.is_dir():
            dcm_files = sorted(subdir.glob('*.dcm'))
            if dcm_files:
                result["dicoms"].append({
                    "name": f"{subdir.name} ({len(dcm_files)}张)",
                    "path": str(subdir.relative_to(DATA_DIR.parent)),
                    "description": f"DICOM序列, {len(dcm_files)}张切片", "count": len(dcm_files)
                })
    for f in sorted(DATA_DIR.rglob('*.dcm')):
        if f.stat().st_size > 1000 and not any(p.name == 'dicom' for p in f.parents if p != DATA_DIR):
            result["single"].append({
                "name": f.name, "path": str(f.relative_to(DATA_DIR.parent)),
                "size": f.stat().st_size, "ext": ".dcm",
                "description": f"单张DICOM ({f.stat().st_size//1024}KB)"
            })
    for f in sorted(DATA_DIR.glob('*.mhd')):
        raw_f = f.with_suffix('.raw')
        raw_size = raw_f.stat().st_size if raw_f.exists() else 0
        result["mhd"].append({
            "name": f.name, "path": str(f.relative_to(DATA_DIR.parent)),
            "size": f.stat().st_size, "ext": ".mhd",
            "description": f"MHD+RAW ({raw_size//1024//1024}MB)"
        })
    for ext in ['*.nii', '*.nii.gz', '*.nrrd']:
        for f in sorted(DATA_DIR.glob(ext)):
            size_mb = f.stat().st_size // (1024 * 1024)
            result["root"].append({
                "name": f.name, "path": str(f.relative_to(DATA_DIR.parent)),
                "size": f.stat().st_size, "ext": f.suffix,
                "description": f"{f.suffix} 体数据 ({size_mb}MB)"
            })
    single_dir = DATA_DIR / 'single'
    if single_dir.exists():
        for f in sorted(single_dir.glob('*.*')):
            if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp', '.dcm']:
                result["single"].append({
                    "name": f.name, "path": str(f.relative_to(DATA_DIR.parent)),
                    "size": f.stat().st_size, "ext": f.suffix,
                    "description": f"单张图像 ({f.stat().st_size//1024}KB)"
                })
    return jsonify(make_response(success=True, data=result))


@ct_bp.route('/cq500/stats', methods=['GET'])
def cq500_stats():
    try:
        stats = get_dataset_stats()
        return jsonify(make_response(success=True, data=stats))
    except Exception as e:
        log.error(f"CQ500 stats error: {e}")
        return jsonify(make_response(success=False, error=str(e))), 500


@ct_bp.route('/cq500/cases', methods=['GET', 'POST'])
def cq500_list_cases():
    if request.method == 'POST':
        filters = request.get_json() or {}
    else:
        filters = request.args.to_dict()
    try:
        for key in ['page', 'page_size']:
            if key in filters:
                filters[key] = int(filters[key])
        for key in ['is_positive', 'has_ich', 'has_sdh', 'only_with_volume']:
            if key in filters:
                if isinstance(filters[key], str):
                    filters[key] = filters[key].lower() in ('true', '1', 'yes')
        result = get_case_list(filters)
        return jsonify(make_response(success=True, data=result))
    except Exception as e:
        log.error(f"CQ500 case list error: {e}")
        return jsonify(make_response(success=False, error=str(e))), 500


@ct_bp.route('/cq500/load', methods=['POST'])
def cq500_load_case():
    sid = _get_sid(request)
    data = request.get_json() or {}
    case_key = data.get('case_key', '')
    if not case_key:
        return jsonify(make_response(success=False, error="case_key required")), 400
    volume = load_cq500_volume(case_key)
    if volume is None:
        return jsonify(make_response(success=False, error=f"Cannot load {case_key}")), 404
    cache = _get_cache(sid) or {}
    cache['created'] = time.time()
    cache['volume'] = volume
    cache['source'] = f"CQ500/{case_key}"
    cache['case_key'] = case_key
    _set_cache(sid, cache)
    return jsonify(make_response(success=True, data={
        "loaded": True, "shape": list(volume.shape),
        "z_slices": volume.shape[0], "width": volume.shape[2],
        "height": volume.shape[1], "dtype": str(volume.dtype),
        "source": f"CQ500-{case_key}", "case_key": case_key,
        "sessionId": sid, "min": float(volume.min()),
        "max": float(volume.max()), "mean": float(volume.mean())
    }, session_id=sid))


@ct_bp.route('/ai-analyze', methods=['POST'])
def ct_ai_analyze():
    """使用CQ500训练的大脑CT异常检测模型分析当前会话的CT数据"""
    sid = _get_sid(request)
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400

    volume = cache['volume']

    try:
        import sys
        _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if _base_dir not in sys.path:
            sys.path.insert(0, _base_dir)
        from server.model_loader import get_model
        model = get_model('brain_ct_v3')
        if model is None:
            return jsonify(make_response(success=False, error="Model not loaded")), 503

        from collections import OrderedDict
        from scipy.spatial.distance import mahalanobis
        from scipy import ndimage
        import torch
        import torchvision.transforms as transforms
        
        import torch.nn as nn
        import torchvision.models as models_tv

        DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        WINDOWS = model.get('windows', OrderedDict())
        IMG_SIZE = 224

        class ResNetFeatureExtractor(nn.Module):
            def __init__(self):
                super().__init__()
                backbone = models_tv.resnet18(weights=models_tv.ResNet18_Weights.IMAGENET1K_V1)
                self.features = nn.Sequential(*list(backbone.children())[:-2])
                self.pool = nn.AdaptiveAvgPool2d((1, 1))

            def forward(self, x):
                x = self.features(x)
                x = self.pool(x)
                return x.view(x.size(0), -1)

        extractor = ResNetFeatureExtractor().to(DEVICE).eval()

        def preprocess_slice(slice_2d, img_size=IMG_SIZE):
            zoom = img_size / slice_2d.shape[0]
            resized = ndimage.zoom(slice_2d, zoom, order=1)
            mn, mx = resized.min(), resized.max()
            if mx - mn > 1e-6:
                normed = (resized - mn) / (mx - mn)
            else:
                normed = np.zeros_like(resized)
            tensor = torch.from_numpy(normed).float().unsqueeze(0).repeat(3,1,1).unsqueeze(0)
            tensor = transforms.Normalize(mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225])(tensor)
            return tensor.to(DEVICE)

        def apply_ct_window(vol, center, width):
            half = width / 2.0
            low = center - half
            high = center + half
            return np.clip(vol.astype(np.float32), low, high)

        num_slices = volume.shape[0]
        per_slice_anomaly = {}

        for wname in WINDOWS:
            w = WINDOWS[wname]
            windowed = apply_ct_window(volume, w['center'], w['width'])
            features = []
            with torch.no_grad():
                for z in range(min(windowed.shape[0], 60)):
                    sl = windowed[z]
                    tensor = preprocess_slice(sl)
                    feat = extractor(tensor).cpu().numpy().flatten()
                    features.append(feat)
            features = np.array(features)

            if f'{wname}_pca' in model:
                pca = model[f'{wname}_pca']
                features_pca = pca.transform(features)
                mean_vec = model[f'{wname}_mean']
                inv_cov = model[f'{wname}_inv_cov']
                scores = np.array([mahalanobis(f, mean_vec, inv_cov) for f in features_pca])
                ref_mean = model[f'{wname}_dist_mean']
                ref_std = model[f'{wname}_dist_std']
                zscores = (scores - ref_mean) / max(ref_std, 1e-8)
                per_slice_anomaly[wname] = zscores.tolist()

        # 综合评估
        all_scores = []
        for wname in per_slice_anomaly:
            all_scores.append(np.mean(per_slice_anomaly[wname]))
        avg_anomaly = float(np.mean(all_scores))

        if avg_anomaly > 3.0:
            assessment = "abnormal"
        elif avg_anomaly > 1.5:
            assessment = "suspicious"
        else:
            assessment = "normal"

        prob = 1.0 / (1.0 + np.exp(-avg_anomaly)) if avg_anomaly else 0.5

        return jsonify(make_response(success=True, data={
            "assessment": assessment,
            "abnormality_score": round(prob, 4),
            "abnormality_zscore": round(avg_anomaly, 4),
            "windows_analyzed": list(per_slice_anomaly.keys()),
            "num_slices_analyzed": min(num_slices, 60),
            "total_slices": num_slices,
            "model": "brain_ct_v3 (CQ500)",
        }, session_id=sid))

    except Exception as e:
        log.error(f"CT AI analyze error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(make_response(success=False, error=str(e))), 500


@ct_bp.route('/ai-artifact-segment', methods=['POST'])
def ct_artifact_segment():
    """
    使用 CQ500 训练好的 UNet3D 模型进行脑CT伪影分割。

    返回每个切片的伪影掩码叠加图 + 总体统计。
    """
    sid = _get_sid(request)
    cache = _get_cache(sid)
    if not cache or 'volume' not in cache:
        return jsonify(make_response(success=False, error="No data loaded")), 400

    volume = cache['volume']

    try:
        import sys
        _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if _base_dir not in sys.path:
            sys.path.insert(0, _base_dir)

        from server.ct.artifact_unet_model import load_artifact_unet, predict_artifact

        # 加载模型（只加载一次，会缓存到全局变量中）
        if not getattr(ct_artifact_segment, '_model', None):
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                'models', 'best_artifact_unet.pth'
            )
            ct_artifact_segment._model = load_artifact_unet(model_path)
            if ct_artifact_segment._model is None:
                return jsonify(make_response(success=False, error="伪影分割模型加载失败")), 503
            log.info("🔧 UNet3D 伪影分割模型已加载")

        model = ct_artifact_segment._model
        device = next(model.parameters()).device

        # 推理
        mask = predict_artifact(model, volume, device)
        # mask shape: (D, H, W) 二值

        # 统计
        total_voxels = int(mask.size)
        artifact_voxels = int(np.sum(mask))
        artifact_ratio = float(artifact_voxels / total_voxels) if total_voxels > 0 else 0.0

        # 生成切片叠加图（采样最多 9 层展示）
        data = request.get_json() or {}
        z_preview = data.get('z', volume.shape[0] // 2)

        # 预览切片：用当前 z 层生成叠加图
        gray_plane = apply_window(np.rot90(volume[z_preview, :, :]), 80, 40)
        mask_plane = np.rot90(mask[z_preview, :, :])
        overlay_b64 = overlay_to_b64(gray_plane.astype(np.float32), mask_plane, mask_color=(1, 0, 0))

        # 多切片缩略图
        thumbnails = {}
        n_slices = min(mask.shape[0], 9)
        step_slices = max(1, mask.shape[0] // n_slices)
        for i in range(0, mask.shape[0], step_slices):
            zz = min(i, mask.shape[0] - 1)
            g = apply_window(np.rot90(volume[zz, :, :]), 80, 40)
            m = np.rot90(mask[zz, :, :])
            thumbnails[f"z_{zz:03d}"] = overlay_to_b64(g.astype(np.float32), m, mask_color=(1, 0, 0))

        # 伪影最多的切片
        per_slice_artifact = [int(np.sum(mask[z, :, :])) for z in range(mask.shape[0])]
        worst_slice = int(np.argmax(per_slice_artifact)) if per_slice_artifact else 0

        return jsonify(make_response(success=True, data={
            "segmented": True,
            "artifact_voxels": artifact_voxels,
            "total_voxels": total_voxels,
            "artifact_ratio": round(artifact_ratio, 6),
            "mask_shape": list(mask.shape),
            "overlay": overlay_b64,
            "thumbnails": thumbnails,
            "worst_slice": worst_slice,
            "model": "artifact_unet (CQ500 UNet3D)",
            "model_epoch": getattr(model, 'epoch', '?'),
            "is_deep_learning": True,
        }, session_id=sid))

    except Exception as e:
        log.error(f"CT artifact segment error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(make_response(success=False, error=str(e))), 500


def init_ct_data():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log.info(f"CT data initialized (data_dir={DATA_DIR}, output={OUTPUT_DIR})")
