import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import SimpleITK as sitk
from matplotlib import font_manager, rcParams


sitk.ProcessObject_SetGlobalWarningDisplay(False)


def setup_chinese_font() -> None:
    candidates = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "WenQuanYi Zen Hei",
        "PingFang SC",
        "Arial Unicode MS",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    selected = next((name for name in candidates if name in available), None)

    if selected:
        rcParams["font.sans-serif"] = [selected]
    else:
        rcParams["font.sans-serif"] = ["DejaVu Sans"]
        print("警告: 未检测到常见中文字体，标题可能出现中文显示异常。")
    rcParams["axes.unicode_minus"] = False


def read_dicom_series(dicom_folder: Path) -> sitk.Image:
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(str(dicom_folder))
    if not dicom_names:
        raise ValueError(f"未在目录中找到 DICOM 文件: {dicom_folder}")
    reader.SetFileNames(dicom_names)
    return reader.Execute()


def read_dataset(base_dir: Path) -> tuple[sitk.Image, str]:
    mhd_path = base_dir / "1.mhd"
    nii_path = base_dir / "result.nii.gz"
    dicom_dir = base_dir / "CT Plain"

    if mhd_path.exists():
        return sitk.ReadImage(str(mhd_path)), f"MHD: {mhd_path.name}"
    if nii_path.exists():
        return sitk.ReadImage(str(nii_path)), f"NIfTI: {nii_path.name}"
    if dicom_dir.exists() and dicom_dir.is_dir():
        return read_dicom_series(dicom_dir), f"DICOM目录: {dicom_dir.name}"

    raise FileNotFoundError(
        "未找到可读取的数据。请确保 CT_Junior 下至少有 1.mhd、result.nii.gz 或解压后的 CT Plain DICOM 目录。"
    )


def print_image_info(img: sitk.Image, source_desc: str) -> None:
    print(f"数据来源: {source_desc}")
    print("图像大小 (x,y,z):", img.GetSize())
    print("体素间距 (mm):", img.GetSpacing())
    print("原点:", img.GetOrigin())
    print("方向矩阵:", img.GetDirection())
    print("像素类型:", img.GetPixelIDTypeAsString())


def numpy_process(img: sitk.Image) -> sitk.Image:
    arr = sitk.GetArrayFromImage(img)  # (z, y, x)
    print("NumPy 数组形状 (z,y,x):", arr.shape)
    print("NumPy 数据类型:", arr.dtype)
    print("数值范围: min =", np.min(arr), ", max =", np.max(arr))

    processed = arr.copy()
    processed[processed > 100] = 0

    out = sitk.GetImageFromArray(processed)
    out.SetOrigin(img.GetOrigin())
    out.SetSpacing(img.GetSpacing())
    out.SetDirection(img.GetDirection())
    return out


def save_outputs(img_original: sitk.Image, img_processed: sitk.Image, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img_original, str(out_dir / "ct_original.nii.gz"))
    sitk.WriteImage(img_processed, str(out_dir / "ct_processed.nii.gz"))
    sitk.WriteImage(img_processed, str(out_dir / "ct_processed.nrrd"))

    z_center = img_original.GetSize()[2] // 2
    slice_2d = img_original[:, :, z_center]
    png_img = sitk.IntensityWindowing(slice_2d, -125, 225, 0, 255)
    png_img = sitk.Cast(png_img, sitk.sitkUInt8)
    sitk.WriteImage(png_img, str(out_dir / f"slice_z{z_center}.png"))


def save_matplotlib_preview(img: sitk.Image, out_dir: Path) -> None:
    arr = sitk.GetArrayFromImage(img)  # (z, y, x)
    z_center = arr.shape[0] // 2
    slice_2d = arr[z_center]

    ww, wl = 350, 50
    v_min = wl - ww / 2
    v_max = wl + ww / 2
    slice_2d = np.clip(slice_2d, v_min, v_max)

    plt.figure(figsize=(8, 8))
    plt.imshow(slice_2d, cmap="gray")
    plt.title(f"CT 第 {z_center} 层 | 软组织窗")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_dir / f"preview_z{z_center}.png", dpi=150)
    plt.close()


def save_axial_report(img: sitk.Image, out_dir: Path, rows: int = 3, cols: int = 3) -> None:
    arr = sitk.GetArrayFromImage(img)  # (z, y, x)
    z_count = arr.shape[0]
    total = rows * cols
    if z_count < total:
        indices = np.linspace(0, z_count - 1, total, dtype=int)
    else:
        # 避开头尾，选取更稳定的中间区间切片
        start = max(0, int(z_count * 0.1))
        end = min(z_count - 1, int(z_count * 0.9))
        indices = np.linspace(start, end, total, dtype=int)

    ww, wl = 350, 50
    v_min = wl - ww / 2
    v_max = wl + ww / 2

    fig, axes = plt.subplots(rows, cols, figsize=(12, 12), facecolor="#efefef")
    axes = axes.flatten()

    for ax, z in zip(axes, indices):
        slice_2d = np.clip(arr[z], v_min, v_max)
        ax.imshow(slice_2d, cmap="gray", vmin=v_min, vmax=v_max)
        ax.set_title(f"第 {int(z)} 层", fontsize=12)
        ax.axis("off")

    fig.suptitle("CT横断面报告", fontsize=18, y=0.995)
    plt.tight_layout()
    plt.savefig(out_dir / "ct_axial_report.png", dpi=180)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="按 SimpleITK 教程步骤读取并处理 CT_Junior 数据集")
    parser.add_argument(
        "--base-dir",
        default=str(Path(__file__).resolve().parent),
        help="数据集目录，默认是脚本所在目录",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="输出目录，默认 <base-dir>/out",
    )
    args = parser.parse_args()
    setup_chinese_font()

    base_dir = Path(args.base_dir).resolve()
    out_dir = Path(args.out_dir).resolve() if args.out_dir else base_dir / "out"

    image, source_desc = read_dataset(base_dir)
    print_image_info(image, source_desc)
    processed = numpy_process(image)
    save_outputs(image, processed, out_dir)
    save_matplotlib_preview(image, out_dir)
    save_axial_report(image, out_dir)

    print(f"\n处理完成，输出目录: {out_dir}")
    print("已生成: ct_original.nii.gz, ct_processed.nii.gz, ct_processed.nrrd, slice_*.png, preview_*.png, ct_axial_report.png")


if __name__ == "__main__":
    main()
