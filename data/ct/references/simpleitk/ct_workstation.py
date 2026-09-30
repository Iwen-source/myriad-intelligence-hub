from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, Tuple
import socket
import subprocess
import time
import shlex

import matplotlib.pyplot as plt
import numpy as np
import SimpleITK as sitk
import streamlit as st
import streamlit.components.v1 as components
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False
try:
    import pyvista as pv
    HAS_VTK_WEB = True
except Exception:
    HAS_VTK_WEB = False


CQ500_LABEL_FIELDS = [
    "ICH",
    "IPH",
    "IVH",
    "SDH",
    "EDH",
    "SAH",
    "CalvarialFracture",
    "MassEffect",
    "MidlineShift",
]

CQ500_READ_FIELDS = [
    "ICH",
    "IPH",
    "IVH",
    "SDH",
    "EDH",
    "SAH",
    "BleedLocation-Left",
    "BleedLocation-Right",
    "ChronicBleed",
    "Fracture",
    "CalvarialFracture",
    "OtherFracture",
    "MassEffect",
    "MidlineShift",
]

CQ500_LABEL_CN = {
    "ICH": "颅内出血",
    "IPH": "脑实质出血",
    "IVH": "脑室内出血",
    "SDH": "硬膜下血肿",
    "EDH": "硬膜外血肿",
    "SAH": "蛛网膜下腔出血",
    "BleedLocation-Left": "左侧出血",
    "BleedLocation-Right": "右侧出血",
    "ChronicBleed": "慢性出血",
    "Fracture": "颅骨骨折",
    "CalvarialFracture": "颅盖骨骨折",
    "OtherFracture": "其他骨折",
    "MassEffect": "占位效应",
    "MidlineShift": "中线移位",
}


def setup_page() -> None:
    st.set_page_config(page_title="CT影像分析工作台", layout="wide")
    st.title("CT影像分析工作台")
    st.caption("支持读取、窗宽窗位、滤波、边缘检测、阈值分割与多切片浏览")


@st.cache_data(show_spinner=False)
def load_ct(base_dir: str) -> Tuple[sitk.Image, np.ndarray]:
    root = Path(base_dir)
    if root.is_file():
        img = sitk.ReadImage(str(root))
    elif any(root.glob("*.dcm")):
        reader = sitk.ImageSeriesReader()
        files = reader.GetGDCMSeriesFileNames(str(root))
        if not files:
            raise FileNotFoundError(f"未在 DICOM 目录中找到可读取序列: {root}")
        reader.SetFileNames(files)
        img = reader.Execute()
    else:
        mhd = root / "1.mhd"
        nii = root / "result.nii.gz"
        dcm = root / "CT Plain"
        if mhd.exists():
            img = sitk.ReadImage(str(mhd))
        elif nii.exists():
            img = sitk.ReadImage(str(nii))
        elif dcm.exists():
            reader = sitk.ImageSeriesReader()
            files = reader.GetGDCMSeriesFileNames(str(dcm))
            if not files:
                raise FileNotFoundError(f"未在 DICOM 目录中找到可读取序列: {dcm}")
            reader.SetFileNames(files)
            img = reader.Execute()
        else:
            raise FileNotFoundError("未找到 1.mhd / result.nii.gz / CT Plain / DICOM序列目录")
    return img, sitk.GetArrayFromImage(img)  # (z,y,x)


@st.cache_data(show_spinner=False)
def load_cq500_table(csv_path: str) -> Dict[str, dict[str, str]]:
    path = Path(csv_path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["name"]: row for row in csv.DictReader(f)}


@st.cache_data(show_spinner=False)
def discover_cq500_cases(cq500_dir: str) -> list[dict[str, str]]:
    root = Path(cq500_dir)
    cases: list[dict[str, str]] = []
    if not root.exists():
        return cases
    for path in root.iterdir():
        if not path.is_dir():
            continue
        match = re.search(r"CQ500CT(\d+)", path.name)
        if not match:
            continue
        number = int(match.group(1))
        cases.append(
            {
                "id": f"CQ500-CT-{number}",
                "number": str(number),
                "path": str(path),
                "folder": path.name,
            }
        )
    return sorted(cases, key=lambda item: int(item["number"]))


def cq500_sequences(case_path: Path) -> list[str]:
    study_dir = case_path / "Unknown Study"
    if not study_dir.exists():
        return []
    sequences = [p.name for p in study_dir.iterdir() if p.is_dir()]
    preferred = ["CT Plain", "CT PLAIN THIN", "CT 4cc sec 150cc D3D on", "CT 4cc sec 150cc D3D on-2", "CT 4cc sec 150cc D3D on-3"]
    return sorted(sequences, key=lambda name: (preferred.index(name) if name in preferred else 99, name))


def cq500_consensus(read_row: dict[str, str] | None, field: str) -> tuple[int, int]:
    if not read_row:
        return 0, 0
    votes = 0
    total = 0
    for reader in ("R1", "R2", "R3"):
        value = read_row.get(f"{reader}:{field}", "")
        if value in {"0", "1"}:
            total += 1
            votes += int(value)
    return votes, total


def cq500_case_summary(case_id: str, read_row: dict[str, str] | None, prob_row: dict[str, str] | None) -> str:
    category = (read_row or prob_row or {}).get("Category") or (read_row or prob_row or {}).get("Category_New") or "-"
    positives = []
    if read_row:
        for field in CQ500_LABEL_FIELDS:
            votes, total = cq500_consensus(read_row, field)
            if total and votes >= 2:
                positives.append(field)
    if not positives and prob_row:
        for field in CQ500_LABEL_FIELDS:
            try:
                if float(prob_row.get(field, "0") or 0) >= 0.5:
                    positives.append(field)
            except ValueError:
                pass
    label = "阴性/低风险" if not positives else "阳性: " + ", ".join(positives[:4])
    if len(positives) > 4:
        label += "..."
    return f"{case_id} | {category} | {label}"


def render_cq500_metadata(case_id: str, read_row: dict[str, str] | None, prob_row: dict[str, str] | None) -> None:
    st.subheader("CQ500结构化标注")
    category = (read_row or {}).get("Category") or (prob_row or {}).get("Category_New") or "-"
    st.caption(f"{case_id} | 分级: {category} | 标注基于 CT Plain 平扫序列")

    if prob_row:
        prob_cols = st.columns(3)
        for idx, field in enumerate(CQ500_LABEL_FIELDS):
            try:
                value = float(prob_row.get(field, "0") or 0)
            except ValueError:
                value = 0.0
            with prob_cols[idx % 3]:
                st.metric(CQ500_LABEL_CN.get(field, field), f"{value:.2f}")
    else:
        st.info("未在 prediction_probabilities.csv 中找到该病例。")

    if read_row:
        rows = []
        for field in CQ500_READ_FIELDS:
            votes, total = cq500_consensus(read_row, field)
            if total == 0:
                continue
            rows.append(
                {
                    "征象": CQ500_LABEL_CN.get(field, field),
                    "字段": field,
                    "三阅片阳性数": f"{votes}/{total}",
                    "共识": "阳性" if votes >= 2 else "阴性",
                }
            )
        st.table(rows)
    else:
        st.info("未在 reads.csv 中找到该病例。")


@st.cache_data(show_spinner=False)
def load_nrrd_volume(nrrd_path: str) -> Tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(nrrd_path)
    return img, sitk.GetArrayFromImage(img)


def apply_window(slice_2d: np.ndarray, ww: float, wl: float) -> np.ndarray:
    vmin = wl - ww / 2
    vmax = wl + ww / 2
    out = np.clip(slice_2d, vmin, vmax)
    out = (out - vmin) / (vmax - vmin + 1e-8)
    return out


def filter_slice(slice_2d: np.ndarray, mode: str, variance: float) -> np.ndarray:
    itk_2d = sitk.GetImageFromArray(slice_2d.astype(np.float32))
    if mode == "高斯滤波 (DiscreteGaussian)":
        out = sitk.DiscreteGaussian(itk_2d, variance=variance)
    elif mode == "中值滤波 (Median)":
        k = max(1, int(round(variance * 2)))
        out = sitk.Median(itk_2d, [k, k])
    else:
        out = itk_2d
    return sitk.GetArrayFromImage(out)


def edge_slice(slice_2d: np.ndarray) -> np.ndarray:
    itk_2d = sitk.GetImageFromArray(slice_2d.astype(np.float32))
    edge = sitk.SobelEdgeDetection(itk_2d)
    return sitk.GetArrayFromImage(edge)


def edge_slice_advanced(slice_2d: np.ndarray, method: str, threshold: float) -> np.ndarray:
    itk_2d = sitk.GetImageFromArray(slice_2d.astype(np.float32))
    if method == "Canny":
        edge = sitk.CannyEdgeDetection(
            itk_2d,
            lowerThreshold=max(0.0, threshold * 0.5),
            upperThreshold=max(0.0, threshold),
            variance=1.0,
        )
    elif method == "Laplacian":
        edge = sitk.Laplacian(itk_2d)
    else:
        edge = sitk.SobelEdgeDetection(itk_2d)
    return sitk.GetArrayFromImage(edge)


def threshold_slice(slice_2d: np.ndarray, low: float, high: float) -> np.ndarray:
    mask = ((slice_2d >= low) & (slice_2d <= high)).astype(np.float32)
    return mask


def save_figure(img: np.ndarray, title: str, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 6), facecolor="#001830")
    ax.imshow(img, cmap="gray")
    ax.set_title(title, color="white")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def save_histogram(slice_2d: np.ndarray, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(slice_2d.ravel(), bins=120, color="#2f80ed")
    ax.set_title("灰度直方图")
    ax.set_xlabel("HU")
    ax.set_ylabel("频数")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def save_montage(volume: np.ndarray, out_path: Path) -> None:
    z = volume.shape[0]
    idx = np.linspace(max(0, int(z * 0.1)), min(z - 1, int(z * 0.9)), 9, dtype=int)
    fig, axes = plt.subplots(3, 3, figsize=(12, 12), facecolor="#efefef")
    for ax, i in zip(axes.flatten(), idx):
        ax.imshow(apply_window(volume[i], 350, 50), cmap="gray")
        ax.set_title(f"第 {int(i)} 层")
        ax.axis("off")
    fig.suptitle("CT横断面报告", fontsize=18)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def build_3d_mask(
    volume: np.ndarray,
    low: float,
    high: float,
    opening_radius: int,
    closing_radius: int,
    min_size: int,
) -> np.ndarray:
    bin_mask = ((volume >= low) & (volume <= high)).astype(np.uint8)
    itk_mask = sitk.GetImageFromArray(bin_mask)
    if opening_radius > 0:
        itk_mask = sitk.BinaryMorphologicalOpening(itk_mask, [opening_radius] * 3)
    if closing_radius > 0:
        itk_mask = sitk.BinaryMorphologicalClosing(itk_mask, [closing_radius] * 3)
    if min_size > 0:
        cc = sitk.ConnectedComponent(itk_mask)
        cc = sitk.RelabelComponent(cc, minimumObjectSize=min_size)
        itk_mask = sitk.BinaryThreshold(cc, 1, 10_000_000, 1, 0)
    return sitk.GetArrayFromImage(itk_mask).astype(np.uint8)


def build_metal_artifact_mask(
    volume: np.ndarray,
    hu_low: int,
    hu_high: int,
    grad_th: float,
    opening_radius: int,
    closing_radius: int,
    min_size: int,
) -> np.ndarray:
    img = sitk.GetImageFromArray(volume.astype(np.float32))
    binary = sitk.BinaryThreshold(img, lowerThreshold=hu_low, upperThreshold=hu_high, insideValue=1, outsideValue=0)

    grad = sitk.GradientMagnitude(img)
    grad_mask = sitk.BinaryThreshold(grad, lowerThreshold=grad_th, upperThreshold=1e9, insideValue=1, outsideValue=0)

    mask = sitk.And(binary, grad_mask)

    if opening_radius > 0:
        mask = sitk.BinaryMorphologicalOpening(mask, [opening_radius] * 3)
    if closing_radius > 0:
        mask = sitk.BinaryMorphologicalClosing(mask, [closing_radius] * 3)
    if min_size > 0:
        cc = sitk.ConnectedComponent(mask)
        cc = sitk.RelabelComponent(cc, minimumObjectSize=min_size)
        mask = sitk.BinaryThreshold(cc, 1, 10_000_000, 1, 0)

    return sitk.GetArrayFromImage(mask).astype(np.uint8)


def overlay_mask(gray: np.ndarray, mask: np.ndarray) -> np.ndarray:
    rgb = np.stack([gray, gray, gray], axis=-1)
    m = mask > 0
    rgb[m, 0] = 1.0
    rgb[m, 1] = 0.0
    rgb[m, 2] = 0.0
    return rgb


def show_image(img: np.ndarray, caption: str, width: int) -> None:
    st.image(img, caption=caption, width=width, clamp=True)


def view_planes(volume: np.ndarray, z: int, y: int, x: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    axial = volume[z, :, :]
    coronal = volume[:, y, :]
    sagittal = volume[:, :, x]
    return axial, coronal, sagittal


def clamp_index(value: int, upper: int) -> int:
    return max(0, min(int(value), int(upper)))


def build_filter_strength_images(
    slice_2d: np.ndarray, filter_mode: str, strengths: list[float], ww: float, wl: float
) -> list[tuple[float, np.ndarray]]:
    items: list[tuple[float, np.ndarray]] = []
    for s in strengths:
        filt = filter_slice(slice_2d, filter_mode, s)
        items.append((s, apply_window(filt, ww, wl)))
    return items


def save_filter_strength_montage(
    items: list[tuple[float, np.ndarray]], out_path: Path, filter_mode: str, z_idx: int
) -> None:
    n = len(items)
    fig, axes = plt.subplots(1, n, figsize=(4 * n, 4), facecolor="#efefef")
    if n == 1:
        axes = [axes]
    for ax, (s, img) in zip(axes, items):
        ax.imshow(img, cmap="gray")
        ax.set_title(f"强度 {s:.1f}")
        ax.axis("off")
    fig.suptitle(f"{filter_mode} | 第 {z_idx} 层", fontsize=14)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def build_pyvista_grid(volume: np.ndarray, spacing: tuple[float, float, float]) -> "pv.ImageData":
    # volume shape: (z, y, x), VTK expects dimensions in (x, y, z)
    z, y, x = volume.shape
    grid = pv.ImageData(dimensions=(x, y, z))
    grid.spacing = spacing
    # Fortran order keeps x-fastest layout for VTK
    grid["HU"] = volume.transpose(2, 1, 0).ravel(order="F")
    return grid


def render_plotly_viewer(
    volume: np.ndarray,
    metal_mask: np.ndarray | None,
    spacing: tuple[float, float, float],
    bone_iso: float,
    soft_iso: float,
    soft_opacity: float,
    bg_hex: str,
    z_idx: int,
    y_idx: int,
    x_idx: int,
    show_linked_planes: bool,
    plane_opacity: float,
    color_preset: str,
    show_plane_colorbar: bool,
) -> None:
    if not HAS_PLOTLY or not HAS_VTK_WEB:
        st.warning("缺少 Plotly 或 PyVista 依赖，无法显示 Plotly 3D。")
        st.code("pip install plotly pyvista", language="bash")
        return

    # 先做体数据降采样，显著降低前端消息体积，避免 Streamlit 200MB 限制
    max_dim = int(max(volume.shape))
    step = 1 if max_dim <= 220 else (2 if max_dim <= 420 else 3)
    vol_ds = volume[::step, ::step, ::step].astype(np.float32)
    spacing_ds = (spacing[0] * step, spacing[1] * step, spacing[2] * step)
    grid = build_pyvista_grid(vol_ds, spacing_ds)
    traces = []
    max_faces = 120_000

    def _extract_faces(mesh: "pv.PolyData") -> np.ndarray | None:
        if mesh.n_cells <= 0 or mesh.n_points <= 0:
            return None
        try:
            tri = mesh.triangulate()
            if tri.n_cells <= 0:
                return None
            # 二次约简：限制三角面数量，防止 Plotly 消息过大
            if tri.n_cells > max_faces:
                ratio = max(0.02, min(1.0, max_faces / float(tri.n_cells)))
                tri = tri.decimate_pro(target_reduction=1.0 - ratio, preserve_topology=True)
            faces = tri.faces.reshape(-1, 4)
            if faces.shape[0] > max_faces:
                stride = int(np.ceil(faces.shape[0] / max_faces))
                faces = faces[::stride]
            return tri, faces
        except Exception:
            return None

    if color_preset == "高对比":
        bone_color = "rgb(255,245,220)"
        soft_color = "rgb(255,150,120)"
        plane_colorscale = "Turbo"
        scene_light = dict(ambient=0.33, diffuse=0.78, specular=0.35, roughness=0.42)
    else:
        bone_color = "rgb(235,235,235)"
        soft_color = "rgb(216,183,168)"
        plane_colorscale = "Gray"
        scene_light = dict(ambient=0.25, diffuse=0.70, specular=0.25, roughness=0.50)

    try:
        bone_mesh = grid.contour([bone_iso], scalars="HU")
        bone_data = _extract_faces(bone_mesh)
        if bone_data is not None:
            bone_mesh, bfaces = bone_data
            traces.append(
                go.Mesh3d(
                    x=bone_mesh.points[:, 0],
                    y=bone_mesh.points[:, 1],
                    z=bone_mesh.points[:, 2],
                    i=bfaces[:, 1],
                    j=bfaces[:, 2],
                    k=bfaces[:, 3],
                    color=bone_color,
                    opacity=0.70,
                    name="骨组织",
                    flatshading=False,
                    lighting=scene_light,
                    lightposition=dict(x=120, y=120, z=240),
                )
            )
    except Exception:
        pass

    try:
        soft_mesh = grid.contour([soft_iso], scalars="HU")
        soft_data = _extract_faces(soft_mesh)
        if soft_data is not None:
            soft_mesh, sfaces = soft_data
            traces.append(
                go.Mesh3d(
                    x=soft_mesh.points[:, 0],
                    y=soft_mesh.points[:, 1],
                    z=soft_mesh.points[:, 2],
                    i=sfaces[:, 1],
                    j=sfaces[:, 2],
                    k=sfaces[:, 3],
                    color=soft_color,
                    opacity=float(soft_opacity),
                    name="软组织",
                    flatshading=False,
                    lighting=dict(ambient=0.32, diffuse=0.70, specular=0.12, roughness=0.68),
                )
            )
    except Exception:
        pass

    if metal_mask is not None and metal_mask.sum() > 0:
        try:
            mgrid = build_pyvista_grid(metal_mask[::step, ::step, ::step].astype(np.float32), spacing_ds)
            mm = mgrid.contour([0.5], scalars="HU")
            mm_data = _extract_faces(mm)
            if mm_data is not None:
                mm, mfaces = mm_data
                traces.append(
                    go.Mesh3d(
                        x=mm.points[:, 0],
                        y=mm.points[:, 1],
                        z=mm.points[:, 2],
                        i=mfaces[:, 1],
                        j=mfaces[:, 2],
                        k=mfaces[:, 3],
                        color="red",
                        opacity=0.95,
                        name="金属伪影掩码",
                        flatshading=True,
                    )
                )
        except Exception:
            pass

    if show_linked_planes:
        zmax, ymax, xmax = volume.shape
        sx, sy, sz = spacing
        pstep = 1 if max(ymax, xmax) <= 320 else 2
        ys = np.arange(0, ymax, pstep)
        xs = np.arange(0, xmax, pstep)
        zs = np.arange(0, zmax, pstep)

        try:
            # Axial plane (z fixed)
            zf = int(np.clip(z_idx, 0, zmax - 1))
            axial = apply_window(volume[zf].astype(np.float32), ww=350.0, wl=50.0)
            axial_ds = axial[::pstep, ::pstep]
            xx, yy = np.meshgrid(xs * sx, ys * sy)
            zz = np.full_like(xx, zf * sz, dtype=np.float32)
            traces.append(
                go.Surface(
                    x=xx,
                    y=yy,
                    z=zz,
                    surfacecolor=axial_ds,
                    cmin=0.0,
                    cmax=1.0,
                    colorscale=plane_colorscale,
                    opacity=float(plane_opacity),
                    showscale=show_plane_colorbar,
                    name=f"Axial z={zf}",
                )
            )
        except Exception:
            pass

        try:
            # Coronal plane (y fixed)
            yf = int(np.clip(y_idx, 0, ymax - 1))
            coronal = apply_window(volume[:, yf, :].astype(np.float32), ww=350.0, wl=50.0)
            coronal_ds = coronal[::pstep, ::pstep]
            xx, zz = np.meshgrid(xs * sx, zs * sz)
            yy = np.full_like(xx, yf * sy, dtype=np.float32)
            traces.append(
                go.Surface(
                    x=xx,
                    y=yy,
                    z=zz,
                    surfacecolor=coronal_ds,
                    cmin=0.0,
                    cmax=1.0,
                    colorscale=plane_colorscale,
                    opacity=float(plane_opacity),
                    showscale=False,
                    name=f"Coronal y={yf}",
                )
            )
        except Exception:
            pass

        try:
            # Sagittal plane (x fixed)
            xf = int(np.clip(x_idx, 0, xmax - 1))
            sagittal = apply_window(volume[:, :, xf].astype(np.float32), ww=350.0, wl=50.0)
            sagittal_ds = sagittal[::pstep, ::pstep]
            yy, zz = np.meshgrid(ys * sy, zs * sz)
            xx = np.full_like(yy, xf * sx, dtype=np.float32)
            traces.append(
                go.Surface(
                    x=xx,
                    y=yy,
                    z=zz,
                    surfacecolor=sagittal_ds,
                    cmin=0.0,
                    cmax=1.0,
                    colorscale=plane_colorscale,
                    opacity=float(plane_opacity),
                    showscale=False,
                    name=f"Sagittal x={xf}",
                )
            )
        except Exception:
            pass

        # Cross point marker
        traces.append(
            go.Scatter3d(
                x=[x_idx * sx],
                y=[y_idx * sy],
                z=[z_idx * sz],
                mode="markers",
                marker=dict(size=4, color="cyan" if color_preset == "真实感" else "yellow"),
                name="联动点",
            )
        )

    if not traces:
        st.warning("当前参数未提取到可显示的三维表面，请调整等值面阈值。")
        return

    st.caption(f"3D渲染已启用降采样: {step}x（防止浏览器与Streamlit消息过大）")

    fig = go.Figure(data=traces)
    fig.update_layout(
        height=760,
        margin=dict(l=0, r=0, t=0, b=0),
        scene=dict(
            bgcolor=bg_hex,
            xaxis=dict(visible=True, title="X"),
            yaxis=dict(visible=True, title="Y"),
            zaxis=dict(visible=True, title="Z"),
            aspectmode="data",
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.2)),
        ),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(0,0,0,0.25)", font=dict(color="white")),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})


def render_vtk_viewer(
    volume: np.ndarray,
    metal_mask: np.ndarray | None,
    spacing: tuple[float, float, float],
    bone_iso: float,
    soft_iso: float,
    soft_opacity: float,
    bg_hex: str,
    interactive: bool,
) -> None:
    if not HAS_VTK_WEB:
        st.warning("未安装 PyVista/stpyvista，无法显示内嵌三维查看器。")
        st.code("pip install pyvista stpyvista", language="bash")
        return

    grid = build_pyvista_grid(volume.astype(np.float32), spacing)
    # Streamlit 运行在脚本线程；trame 在该线程注册信号会触发 set_wakeup_fd 错误。
    # 因此默认使用离屏渲染的稳定模式，交互模式仅作为可选尝试。
    plotter = pv.Plotter(window_size=(1200, 720), off_screen=not interactive)
    plotter.set_background(bg_hex)

    try:
        bone_mesh = grid.contour([bone_iso], scalars="HU")
        if bone_mesh.n_points > 0:
            plotter.add_mesh(
                bone_mesh,
                color="#f2f2f2",
                opacity=0.65,
                smooth_shading=True,
                specular=0.25,
                ambient=0.20,
            )
    except Exception:
        pass

    try:
        soft_mesh = grid.contour([soft_iso], scalars="HU")
        if soft_mesh.n_points > 0:
            plotter.add_mesh(
                soft_mesh,
                color="#d8b7a8",
                opacity=soft_opacity,
                smooth_shading=True,
                specular=0.12,
                ambient=0.25,
            )
    except Exception:
        pass

    if metal_mask is not None and metal_mask.sum() > 0:
        mgrid = build_pyvista_grid(metal_mask.astype(np.float32), spacing)
        try:
            mm = mgrid.contour([0.5], scalars="HU")
            if mm.n_points > 0:
                plotter.add_mesh(mm, color="red", opacity=0.95, smooth_shading=False)
        except Exception:
            pass

    plotter.add_axes(line_width=2)
    plotter.camera_position = "iso"
    plotter.show_grid(color="gray")
    try:
        if interactive:
            html = plotter.export_html(filename=None)
            components.html(html, height=720, scrolling=False)
        else:
            img = plotter.screenshot(filename=None, return_img=True, window_size=[1200, 720])
            st.image(img, caption="VTK三维预览（静态）", use_container_width=True)
    except Exception as e:
        msg = str(e)
        if interactive and "set_wakeup_fd only works in main thread" in msg:
            st.warning("交互模式受 Streamlit 线程限制，已切换为静态3D预览。")
        else:
            st.warning(f"3D渲染异常，已切换为静态预览。原因: {e}")
        # 重新创建一个明确的离屏 Plotter，避免“Nothing to screenshot”
        fallback = pv.Plotter(window_size=(1200, 720), off_screen=True)
        fallback.set_background(bg_hex)
        try:
            bone_mesh = grid.contour([bone_iso], scalars="HU")
            if bone_mesh.n_points > 0:
                fallback.add_mesh(bone_mesh, color="#f2f2f2", opacity=0.65, smooth_shading=True, specular=0.25, ambient=0.20)
        except Exception:
            pass
        try:
            soft_mesh = grid.contour([soft_iso], scalars="HU")
            if soft_mesh.n_points > 0:
                fallback.add_mesh(soft_mesh, color="#d8b7a8", opacity=soft_opacity, smooth_shading=True, specular=0.12, ambient=0.25)
        except Exception:
            pass
        if metal_mask is not None and metal_mask.sum() > 0:
            try:
                mgrid = build_pyvista_grid(metal_mask.astype(np.float32), spacing)
                mm = mgrid.contour([0.5], scalars="HU")
                if mm.n_points > 0:
                    fallback.add_mesh(mm, color="red", opacity=0.95, smooth_shading=False)
            except Exception:
                pass
        fallback.add_axes(line_width=2)
        fallback.camera_position = "iso"
        fallback.show_grid(color="gray")
        img = fallback.screenshot(filename=None, return_img=True, window_size=[1200, 720])
        st.image(img, caption="VTK三维预览（静态降级）", use_container_width=True)
        fallback.close()
    finally:
        plotter.close()


def is_port_open(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.25)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def start_trame_service(
    service_script: Path,
    venv_python: Path,
    input_path: Path,
    mask_path: Path | None,
    host: str,
    port: int,
    force_restart: bool = False,
) -> bool:
    cmd = [
        str(venv_python),
        str(service_script),
        "--input",
        str(input_path),
        "--host",
        host,
        "--port",
        str(port),
    ]
    if mask_path is not None and mask_path.exists():
        cmd.extend(["--mask", str(mask_path)])

    if not force_restart and is_port_open(host, port):
        return True

    # 仅在明确重启时清理旧服务，避免自动启动逻辑把新进程误杀
    if force_restart:
        try:
            subprocess.run(
                ["pkill", "-f", f"trame_ct_service.py .* --port {port}"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.3)
        except Exception:
            pass

    log_path = service_script.parent / "trame_service.log"
    if force_restart:
        log_path.write_text("", encoding="utf-8")
    quoted_cmd = " ".join(shlex.quote(part) for part in cmd)
    shell_cmd = f"PYTHONUNBUFFERED=1 {quoted_cmd} >> {shlex.quote(str(log_path))} 2>&1 < /dev/null"
    subprocess.Popen(
        ["setsid", "bash", "-lc", shell_cmd],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        if is_port_open(host, port):
            return True
        time.sleep(0.2)
    return False


def main() -> None:
    setup_page()
    base_dir = Path(__file__).resolve().parent
    project_dir = base_dir.parent
    cq500_dir = project_dir / "CQ500"
    cq500_reads = load_cq500_table(str(cq500_dir / "reads.csv"))
    cq500_probs = load_cq500_table(str(cq500_dir / "prediction_probabilities.csv"))
    cq500_cases = discover_cq500_cases(str(cq500_dir))

    selected_cq500_case: dict[str, str] | None = None
    selected_sequence = ""
    selected_case_id = ""
    current_input_path = base_dir

    with st.sidebar:
        st.header("控制面板")
        data_source = st.selectbox("数据源", ["CT_Junior示例数据", "CQ500急诊头颅CT"])
        if data_source == "CQ500急诊头颅CT":
            if not cq500_cases:
                st.error(f"未找到 CQ500 病例目录: {cq500_dir}")
                return
            selected_cq500_case = st.selectbox(
                "CQ500病例",
                cq500_cases,
                format_func=lambda item: cq500_case_summary(
                    item["id"],
                    cq500_reads.get(item["id"]),
                    cq500_probs.get(item["id"]),
                ),
            )
            selected_case_id = selected_cq500_case["id"]
            case_path = Path(selected_cq500_case["path"])
            sequences = cq500_sequences(case_path)
            if not sequences:
                st.error(f"该病例未找到 Unknown Study 下的DICOM序列: {case_path}")
                return
            default_seq_index = sequences.index("CT Plain") if "CT Plain" in sequences else 0
            selected_sequence = st.selectbox("扫描序列", sequences, index=default_seq_index)
            current_input_path = case_path / "Unknown Study" / selected_sequence
            if selected_sequence != "CT Plain":
                st.warning("CQ500官方急诊出血/骨折标注主要对应 CT Plain 平扫序列，其他序列仅建议作补充查看。")
        else:
            current_input_path = base_dir

    out_dir = base_dir / "out" / (selected_case_id if selected_case_id else "CT_Junior")
    out_dir.mkdir(parents=True, exist_ok=True)

    img, volume = load_ct(str(current_input_path))
    z_max = volume.shape[0] - 1
    volume_key = f"{current_input_path}|{volume.shape}|{img.GetSpacing()}"
    if st.session_state.get("loaded_volume_key") != volume_key:
        st.session_state.loaded_volume_key = volume_key
        st.session_state.z_mpr = z_max // 2
        st.session_state.y_mpr = volume.shape[1] // 2
        st.session_state.x_mpr = volume.shape[2] // 2
        st.session_state.seg_mask = None
        st.session_state.metal_mask = None

    with st.sidebar:
        if selected_case_id:
            st.write(f"当前加载 `{selected_case_id}` / `{selected_sequence}`")
        else:
            st.write(f"当前加载 `{(base_dir / '1.mhd').name}`")
        filter_mode = st.selectbox("滤波器", ["高斯滤波 (DiscreteGaussian)", "中值滤波 (Median)", "不滤波"])
        window_preset = st.selectbox("窗宽窗位", ["脑窗", "肺窗", "软组织窗", "骨窗", "自定义"])
        variance = st.slider("滤波参数(方差)", 0.1, 3.0, 0.3, 0.1)
        z_idx = st.slider("切片控制", 0, z_max, z_max // 2, 1)
        show_zoom = st.checkbox("显示中心ROI放大图", value=True)
        edge_method = st.selectbox("边缘算法", ["Sobel", "Canny", "Laplacian"])
        edge_threshold = st.slider("边缘阈值(Canny有效)", 10.0, 300.0, 80.0, 5.0)
        st.markdown("---")
        st.subheader("三维分割参数")
        seg_low = st.slider("阈值下限", -1200, 2000, 200, 10)
        seg_high = st.slider("阈值上限", -1200, 3000, 2800, 10)
        opening_radius = st.slider("开运算半径", 0, 5, 1, 1)
        closing_radius = st.slider("闭运算半径", 0, 5, 2, 1)
        min_obj_size = st.slider("连通域最小体素", 0, 20000, 500, 100)
        show_seg_overlay = st.checkbox("显示分割叠加(红色)", value=True)
        compact_layout = st.checkbox("紧凑排布(推荐)", value=True)
        st.markdown("---")
        st.subheader("金属伪影检测")
        metal_low = st.slider("伪影阈值下限(HU)", 300, 1500, 600, 10)
        metal_high = st.slider("伪影阈值上限(HU)", 2000, 4000, 3500, 10)
        metal_grad = st.slider("梯度阈值", 50.0, 500.0, 80.0, 5.0)
        metal_open = st.slider("伪影开运算半径", 0, 5, 1, 1)
        metal_close = st.slider("伪影闭运算半径", 0, 10, 2, 1)
        metal_min_size = st.slider("伪影最小面积(体素)", 10, 5000, 30, 10)
        show_metal_overlay = st.checkbox("显示伪影红色标注", value=True)
        show_metal_white_mask = st.checkbox("显示白色伪影掩码图", value=True)
        st.markdown("---")
        st.subheader("三维VTK查看器")
        show_vtk = st.checkbox("显示内嵌3D查看器", value=True)
        viewer_engine = st.selectbox("3D引擎", ["Plotly(稳定推荐)", "Trame(服务模式)"])
        show_linked_planes = st.checkbox("3D中显示对应切片平面", value=True)
        color_preset = st.selectbox("3D配色风格", ["真实感", "高对比"])
        show_plane_colorbar = st.checkbox("显示切片伪彩色条", value=False)
        plane_opacity = st.slider("切片平面不透明度", 0.10, 0.85, 0.45, 0.05)
        trame_host = st.text_input("Trame主机", value="127.0.0.1")
        trame_port = st.number_input("Trame端口", min_value=9000, max_value=9900, value=9590, step=1)
        auto_start_trame = st.checkbox("自动启动3D服务", value=True)
        start_trame_btn = st.button("重启独立3D服务", use_container_width=True)
        vtk_source = st.selectbox("3D数据源", ["VTK脑部数据(brain_ct.nrrd)", "当前CT数据"])
        bone_iso = st.slider("骨组织等值面(HU)", 150, 1500, 450, 10)
        soft_iso = st.slider("软组织等值面(HU)", -200, 500, 80, 10)
        soft_opacity = st.slider("软组织不透明度", 0.05, 0.60, 0.22, 0.01)
        vtk_bg = st.color_picker("3D背景色", "#0a0e14")

        if window_preset == "脑窗":
            ww, wl = 80.0, 40.0
        elif window_preset == "肺窗":
            ww, wl = 1500.0, -600.0
        elif window_preset == "骨窗":
            ww, wl = 2000.0, 400.0
        elif window_preset == "软组织窗":
            ww, wl = 350.0, 50.0
        else:
            ww = st.number_input("自定义窗宽", value=350.0, step=10.0)
            wl = st.number_input("自定义窗位", value=50.0, step=10.0)

        st.markdown("---")
        st.subheader("功能快捷键")
        save_view = st.button("保存当前视图", use_container_width=True)
        save_hist = st.button("保存灰度直方图", use_container_width=True)
        edge_btn = st.button("边缘检测", use_container_width=True)
        th_btn = st.button("阈值分割", use_container_width=True)
        compare_btn = st.button("滤波强度对比", use_container_width=True)
        seg_btn = st.button("执行三维分割", use_container_width=True)
        metal_btn = st.button("执行金属伪影检测", use_container_width=True)
        montage_btn = st.button("保存多切片拼图", use_container_width=True)
        save_compare_btn = st.button("保存滤波强度拼图", use_container_width=True)
        save_mask_btn = st.button("导出分割结果(NIfTI)", use_container_width=True)
        save_metal_btn = st.button("导出伪影掩码(NIfTI)", use_container_width=True)
        save_metal_png_btn = st.button("导出当前层伪影掩码PNG", use_container_width=True)

        st.markdown("---")
        st.text(
            f"图像大小(x,y,z): {img.GetSize()}\n"
            f"Spacing: {img.GetSpacing()}\n"
            f"Origin: {img.GetOrigin()}\n"
            f"Direction: {img.GetDirection()}\n"
            f"NumPy形状(z,y,x): {volume.shape}"
        )

    if selected_case_id:
        render_cq500_metadata(
            selected_case_id,
            cq500_reads.get(selected_case_id),
            cq500_probs.get(selected_case_id),
        )

    base_slice = volume[z_idx].astype(np.float32)
    filtered = filter_slice(base_slice, filter_mode, variance)
    shown = apply_window(filtered, ww, wl)

    if "panel_mode" not in st.session_state:
        st.session_state.panel_mode = "normal"
    if edge_btn:
        st.session_state.panel_mode = "edge"
    if th_btn:
        st.session_state.panel_mode = "threshold"
    if st.button("恢复原图显示"):
        st.session_state.panel_mode = "normal"

    if st.session_state.panel_mode == "edge":
        edge_img = edge_slice_advanced(filtered, edge_method, edge_threshold)
        right_img = apply_window(edge_img, ww=1.0, wl=0.2)
        right_title = f"边缘检测 ({edge_method})"
    elif st.session_state.panel_mode == "threshold":
        low = wl - ww / 4
        high = wl + ww / 4
        right_img = threshold_slice(filtered, low, high)
        right_title = f"阈值分割 [{low:.0f}, {high:.0f}]"
    else:
        right_img = shown
        right_title = "处理结果"

    if "seg_mask" not in st.session_state:
        st.session_state.seg_mask = None
    if "metal_mask" not in st.session_state:
        st.session_state.metal_mask = None
    if seg_btn:
        st.session_state.seg_mask = build_3d_mask(
            volume, seg_low, seg_high, opening_radius, closing_radius, min_obj_size
        )
        st.success("三维分割完成。")
    if metal_btn:
        st.session_state.metal_mask = build_metal_artifact_mask(
            volume,
            metal_low,
            metal_high,
            metal_grad,
            metal_open,
            metal_close,
            metal_min_size,
        )
        metal_vox = int(st.session_state.metal_mask.sum())
        if metal_vox == 0:
            st.warning("检测结果为空：请降低梯度阈值或伪影最小面积，并适当降低阈值下限。")
        else:
            per_slice = st.session_state.metal_mask.sum(axis=(1, 2))
            top_idx = np.argsort(per_slice)[-5:][::-1]
            top_text = ", ".join([f"{int(i)}({int(per_slice[i])})" for i in top_idx if per_slice[i] > 0])
            st.success(f"金属伪影检测完成。掩码体素数: {metal_vox}")
            st.info(f"伪影最明显层(层号/体素): {top_text}")

    seg_mask = st.session_state.seg_mask
    metal_mask = st.session_state.metal_mask

    shown_main = shown
    right_main = right_img
    if show_metal_overlay and metal_mask is not None:
        m2d = metal_mask[z_idx, :, :]
        shown_main = overlay_mask(shown, m2d)
        right_main = overlay_mask(right_img, m2d)

    col1, col2 = st.columns(2)
    main_width = 680 if compact_layout else 900
    with col1:
        show_image(shown_main, f"原始/滤波视图 | 第 {z_idx} 层", main_width)
    with col2:
        show_image(right_main, right_title, main_width)

    st.subheader("MPR多平面视图")
    z0 = z_idx
    y0 = volume.shape[1] // 2
    x0 = volume.shape[2] // 2
    if "z_mpr" not in st.session_state:
        st.session_state.z_mpr = z0
    if "y_mpr" not in st.session_state:
        st.session_state.y_mpr = y0
    if "x_mpr" not in st.session_state:
        st.session_state.x_mpr = x0

    z_mpr = clamp_index(st.session_state.z_mpr, volume.shape[0] - 1)
    y_mpr = clamp_index(st.session_state.y_mpr, volume.shape[1] - 1)
    x_mpr = clamp_index(st.session_state.x_mpr, volume.shape[2] - 1)
    st.session_state.z_mpr = z_mpr
    st.session_state.y_mpr = y_mpr
    st.session_state.x_mpr = x_mpr

    axial, coronal, sagittal = view_planes(volume.astype(np.float32), z_mpr, y_mpr, x_mpr)
    axial_w = apply_window(axial, ww, wl)
    coronal_w = apply_window(coronal, ww, wl)
    sagittal_w = apply_window(sagittal, ww, wl)

    axial_show, coronal_show, sagittal_show = axial_w, coronal_w, sagittal_w
    if show_seg_overlay and seg_mask is not None:
        m_ax, m_co, m_sa = view_planes(seg_mask, z_mpr, y_mpr, x_mpr)
        axial_show = overlay_mask(axial_show, m_ax)
        coronal_show = overlay_mask(coronal_show, m_co)
        sagittal_show = overlay_mask(sagittal_show, m_sa)
    if show_metal_overlay and metal_mask is not None:
        mm_ax, mm_co, mm_sa = view_planes(metal_mask, z_mpr, y_mpr, x_mpr)
        axial_show = overlay_mask(axial_show, mm_ax)
        coronal_show = overlay_mask(coronal_show, mm_co)
        sagittal_show = overlay_mask(sagittal_show, mm_sa)

    # MPR 1+2+1 排布：上1（Axial）+ 中2（Coronal/Sagittal）+ 下1（Axial参考）
    axial_top_w_px = 760 if compact_layout else 980
    axial_bottom_w_px = 760 if compact_layout else 980
    mid_w_px = 440 if compact_layout else 560

    top_l, top_c, top_r = st.columns([1, 2, 1], gap="large")
    with top_c:
        show_image(axial_show, f"Axial | 切片:{z_mpr}/{volume.shape[0]-1}", axial_top_w_px)
        z_mpr = st.slider(
            "Axial 切片",
            0,
            volume.shape[0] - 1,
            z_mpr,
            1,
            key="z_mpr",
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    mid_l, mid_r = st.columns(2, gap="large")
    with mid_l:
        show_image(coronal_show, f"Coronal | 切片:{y_mpr}/{volume.shape[1]-1}", mid_w_px)
        y_mpr = st.slider(
            "Coronal 切片",
            0,
            volume.shape[1] - 1,
            y_mpr,
            1,
            key="y_mpr",
        )
    with mid_r:
        show_image(sagittal_show, f"Sagittal | 切片:{x_mpr}/{volume.shape[2]-1}", mid_w_px)
        x_mpr = st.slider(
            "Sagittal 切片",
            0,
            volume.shape[2] - 1,
            x_mpr,
            1,
            key="x_mpr",
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # 1+2+1 的最后一个 1：中心 ROI（来自当前 Axial 视图）
    bot_l, bot_c, bot_r = st.columns([1, 2, 1], gap="large")
    if show_zoom:
        h_mpr, w_mpr = axial_show.shape[:2]
        s_mpr = min(h_mpr, w_mpr) // 4
        cy_mpr, cx_mpr = h_mpr // 2, w_mpr // 2
        roi_mpr = axial_show[cy_mpr - s_mpr : cy_mpr + s_mpr, cx_mpr - s_mpr : cx_mpr + s_mpr]
        with bot_c:
            show_image(roi_mpr, "中心ROI放大图", axial_bottom_w_px)

    compare_strengths = [0.3, 0.8, 1.5, 2.5]
    compare_items = build_filter_strength_images(base_slice, filter_mode, compare_strengths, ww, wl)
    if compare_btn:
        st.subheader("不同滤波强度对比")
        compare_cols = st.columns(len(compare_items))
        for c, (s, img_cmp) in zip(compare_cols, compare_items):
            with c:
                show_image(img_cmp, f"强度 {s:.1f}", 280 if compact_layout else 380)

    # ROI 已并入 MPR 1+2+1 布局最后一行，这里不再重复显示

    if show_metal_white_mask:
        st.subheader("伪影掩码（白色）")
        if metal_mask is None:
            st.info("请先点击“执行金属伪影检测”。")
        else:
            mask_2d = metal_mask[z_idx, :, :].astype(np.float32)
            w1, w2, w3 = st.columns([1, 1, 1])
            with w2:
                show_image(mask_2d, f"Mask | 第 {z_idx} 层", 420 if compact_layout else 560)

    if show_vtk:
        st.subheader("VTK三维查看器")
        st.caption("Plotly模式无需额外服务；Trame模式为独立服务+iframe。")
        vtk_dir = base_dir.parent / "VTK"
        brain_nrrd = vtk_dir / "brain_ct.nrrd"
        vtk_img = img
        vtk_vol = volume
        vtk_metal = metal_mask if show_metal_overlay else None
        input_path = current_input_path
        if vtk_source == "VTK脑部数据(brain_ct.nrrd)":
            if not brain_nrrd.exists():
                st.error(f"未找到脑部数据文件: {brain_nrrd}")
                st.info("请把 brain_ct.nrrd 放到 VTK 目录后再使用3D查看器。")
                return
            vtk_img, vtk_vol = load_nrrd_volume(str(brain_nrrd))
            input_path = brain_nrrd
            # 当前伪影掩码来自工作台CT，维度不匹配时不叠加
            if metal_mask is None or metal_mask.shape != vtk_vol.shape:
                vtk_metal = None

        if viewer_engine == "Plotly(稳定推荐)":
            render_plotly_viewer(
                volume=vtk_vol,
                metal_mask=vtk_metal,
                spacing=vtk_img.GetSpacing(),
                bone_iso=bone_iso,
                soft_iso=soft_iso,
                soft_opacity=soft_opacity,
                bg_hex=vtk_bg,
                z_idx=z_mpr,
                y_idx=y_mpr,
                x_idx=x_mpr,
                show_linked_planes=show_linked_planes,
                plane_opacity=plane_opacity,
                color_preset=color_preset,
                show_plane_colorbar=show_plane_colorbar,
            )
        else:
            service_script = vtk_dir / "trame_ct_service.py"
            venv_python = base_dir.parent / ".venv" / "bin" / "python"
            mask_path = out_dir / "metal_artifact_mask.nii.gz" if vtk_metal is not None else None
            trame_url = f"http://{trame_host}:{int(trame_port)}/index.html"
            if "trame_last_auto_try" not in st.session_state:
                st.session_state.trame_last_auto_try = 0.0

            if start_trame_btn:
                if not service_script.exists():
                    st.error(f"未找到服务脚本: {service_script}")
                elif not venv_python.exists():
                    st.error(f"未找到解释器: {venv_python}")
                else:
                    ok = start_trame_service(
                        service_script=service_script,
                        venv_python=venv_python,
                        input_path=input_path,
                        mask_path=mask_path,
                        host=trame_host,
                        port=int(trame_port),
                        force_restart=True,
                    )
                    if ok:
                        st.success("独立3D服务已启动。")
                    else:
                        st.error("独立3D服务启动失败，请查看日志。")

            service_ready = is_port_open(trame_host, int(trame_port))
            now_ts = time.time()
            if (
                not service_ready
                and auto_start_trame
                and (now_ts - st.session_state.trame_last_auto_try > 12.0)
            ):
                st.session_state.trame_last_auto_try = now_ts
                if service_script.exists() and venv_python.exists():
                    service_ready = start_trame_service(
                        service_script=service_script,
                        venv_python=venv_python,
                        input_path=input_path,
                        mask_path=mask_path,
                        host=trame_host,
                        port=int(trame_port),
                        force_restart=False,
                    )
                    if service_ready:
                        st.success("独立3D服务已自动启动。")

            if service_ready:
                components.iframe(trame_url, height=760, scrolling=False)
            else:
                st.info(f"3D服务未启动。点击“重启独立3D服务”后，访问: {trame_url}")
                st.caption(f"日志: {(vtk_dir / 'trame_service.log')}")

    if save_view:
        out = out_dir / f"view_z{z_idx}.png"
        save_figure(right_img, f"第 {z_idx} 层", out)
        st.success(f"已保存: {out}")
    if save_hist:
        out = out_dir / f"hist_z{z_idx}.png"
        save_histogram(filtered, out)
        st.success(f"已保存: {out}")
    if montage_btn:
        out = out_dir / "ct_axial_report.png"
        save_montage(volume, out)
        st.success(f"已保存: {out}")
    if save_compare_btn:
        out = out_dir / f"filter_strength_z{z_idx}.png"
        save_filter_strength_montage(compare_items, out, filter_mode, z_idx)
        st.success(f"已保存: {out}")
    if save_mask_btn:
        if seg_mask is None:
            st.warning("请先点击“执行三维分割”。")
        else:
            mask_img = sitk.GetImageFromArray(seg_mask.astype(np.uint8))
            mask_img.SetOrigin(img.GetOrigin())
            mask_img.SetSpacing(img.GetSpacing())
            mask_img.SetDirection(img.GetDirection())
            out = out_dir / "segmentation_mask.nii.gz"
            sitk.WriteImage(mask_img, str(out))
            st.success(f"已导出: {out}")
    if save_metal_btn:
        if metal_mask is None:
            st.warning("请先点击“执行金属伪影检测”。")
        else:
            metal_img = sitk.GetImageFromArray(metal_mask.astype(np.uint8))
            metal_img.SetOrigin(img.GetOrigin())
            metal_img.SetSpacing(img.GetSpacing())
            metal_img.SetDirection(img.GetDirection())
            out = out_dir / "metal_artifact_mask.nii.gz"
            sitk.WriteImage(metal_img, str(out))
            st.success(f"已导出: {out}")
    if save_metal_png_btn:
        if metal_mask is None:
            st.warning("请先点击“执行金属伪影检测”。")
        else:
            out = out_dir / f"metal_mask_z{z_idx}.png"
            mask_2d = (metal_mask[z_idx, :, :] > 0).astype(np.uint8) * 255
            sitk.WriteImage(sitk.GetImageFromArray(mask_2d), str(out))
            st.success(f"已导出: {out}")


if __name__ == "__main__":
    main()
