from __future__ import annotations

import argparse
from pathlib import Path

import SimpleITK as sitk
import vtk
from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html as html_widgets
from trame.widgets import vtk as vtk_widgets
from trame.widgets import vuetify3 as v3


def build_volume_property(preset: str) -> vtk.vtkVolumeProperty:
    color = vtk.vtkColorTransferFunction()
    opacity = vtk.vtkPiecewiseFunction()
    grad_opacity = vtk.vtkPiecewiseFunction()

    if preset == "bone":
        color.AddRGBPoint(-1000, 0.0, 0.0, 0.0)
        color.AddRGBPoint(-200, 0.25, 0.22, 0.22)
        color.AddRGBPoint(150, 0.75, 0.70, 0.68)
        color.AddRGBPoint(500, 0.95, 0.92, 0.90)
        color.AddRGBPoint(1500, 1.0, 1.0, 1.0)

        opacity.AddPoint(-1000, 0.00)
        opacity.AddPoint(-350, 0.00)
        opacity.AddPoint(-120, 0.01)
        opacity.AddPoint(120, 0.08)
        opacity.AddPoint(300, 0.20)
        opacity.AddPoint(700, 0.45)
        opacity.AddPoint(1600, 0.65)
    else:
        color.AddRGBPoint(-1000, 0.0, 0.0, 0.0)
        color.AddRGBPoint(-300, 0.20, 0.16, 0.16)
        color.AddRGBPoint(40, 0.65, 0.58, 0.56)
        color.AddRGBPoint(220, 0.88, 0.82, 0.80)
        color.AddRGBPoint(900, 1.0, 1.0, 1.0)

        opacity.AddPoint(-1000, 0.00)
        opacity.AddPoint(-450, 0.00)
        opacity.AddPoint(-120, 0.02)
        opacity.AddPoint(80, 0.12)
        opacity.AddPoint(260, 0.20)
        opacity.AddPoint(900, 0.32)

    grad_opacity.AddPoint(0, 0.00)
    grad_opacity.AddPoint(30, 0.05)
    grad_opacity.AddPoint(90, 0.20)
    grad_opacity.AddPoint(220, 0.60)

    prop = vtk.vtkVolumeProperty()
    prop.SetColor(color)
    prop.SetScalarOpacity(opacity)
    prop.SetGradientOpacity(grad_opacity)
    prop.ShadeOn()
    prop.SetInterpolationTypeToLinear()
    prop.SetAmbient(0.15)
    prop.SetDiffuse(0.9)
    prop.SetSpecular(0.25)
    prop.SetSpecularPower(12.0)
    return prop


def load_vtk_image(path: Path) -> vtk.vtkImageData:
    if path.is_dir():
        reader = sitk.ImageSeriesReader()
        files = reader.GetGDCMSeriesFileNames(str(path))
        if not files:
            raise FileNotFoundError(f"未在DICOM目录中找到可读取序列: {path}")
        reader.SetFileNames(files)
        sitk_img = reader.Execute()
    elif path.suffix.lower() in {".nrrd", ".nhdr"}:
        reader = vtk.vtkNrrdReader()
        reader.SetFileName(str(path))
        reader.Update()
        return reader.GetOutput()
    else:
        sitk_img = sitk.ReadImage(str(path))

    arr = sitk.GetArrayFromImage(sitk_img)  # z,y,x
    z, y, x = arr.shape
    importer = vtk.vtkImageImport()
    data = arr.astype("float32").tobytes(order="C")
    importer.CopyImportVoidPointer(data, len(data))
    importer.SetDataScalarTypeToFloat()
    importer.SetNumberOfScalarComponents(1)
    importer.SetDataExtent(0, x - 1, 0, y - 1, 0, z - 1)
    importer.SetWholeExtent(0, x - 1, 0, y - 1, 0, z - 1)
    sx, sy, sz = sitk_img.GetSpacing()
    importer.SetDataSpacing(sx, sy, sz)
    importer.Update()
    return importer.GetOutput()


def main() -> None:
    parser = argparse.ArgumentParser(description="Standalone Trame VTK CT service")
    parser.add_argument("--input", required=True, help="CT input path (.mhd/.nii.gz/.nrrd)")
    parser.add_argument("--mask", default="", help="Optional artifact mask path (.nii.gz)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9527)
    args = parser.parse_args()
    print("[trame] args parsed", flush=True)

    img = load_vtk_image(Path(args.input))
    print("[trame] image loaded", flush=True)

    mapper = vtk.vtkSmartVolumeMapper()
    mapper.SetInputData(img)
    mapper.SetBlendModeToComposite()
    print("[trame] mapper ready", flush=True)

    volume = vtk.vtkVolume()
    volume.SetMapper(mapper)
    volume.SetProperty(build_volume_property("bone"))

    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.06, 0.06, 0.07)
    renderer.AddVolume(volume)
    print("[trame] renderer+volume ready", flush=True)

    # Optional red mask overlay
    if args.mask:
        mask_path = Path(args.mask)
        if mask_path.exists():
            mask_img = load_vtk_image(mask_path)
            mc = vtk.vtkMarchingCubes()
            mc.SetInputData(mask_img)
            mc.SetValue(0, 0.5)
            mc.Update()
            mask_mapper = vtk.vtkPolyDataMapper()
            mask_mapper.SetInputConnection(mc.GetOutputPort())
            mask_actor = vtk.vtkActor()
            mask_actor.SetMapper(mask_mapper)
            mask_actor.GetProperty().SetColor(1.0, 0.1, 0.1)
            mask_actor.GetProperty().SetOpacity(0.95)
            renderer.AddActor(mask_actor)

    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.SetSize(1280, 900)
    render_window.SetOffScreenRendering(1)
    renderer.ResetCamera()
    print("[trame] render window ready", flush=True)

    server = get_server(client_type="vue3")
    print("[trame] server created", flush=True)
    state, ctrl = server.state, server.controller
    state.trame__title = "CT 3D VTK Viewer"
    state.preset = "bone"

    view_ref = {}

    def safe_update(push_camera: bool = False) -> None:
        try:
            if "view" in view_ref:
                view_ref["view"].update(push_camera=push_camera)
        except Exception:
            pass

    def safe_reset_camera() -> None:
        try:
            if "view" in view_ref:
                view_ref["view"].reset_camera()
        except Exception:
            pass

    def set_preset(preset: str) -> None:
        volume.SetProperty(build_volume_property(preset))
        safe_update(push_camera=True)

    @state.change("preset")
    def _on_preset(preset, **_):
        set_preset(preset)

    with SinglePageLayout(server) as layout:
        layout.title.set_text("CT 3D VTK Viewer")
        with layout.toolbar:
            v3.VSelect(
                label="Preset",
                v_model=("preset", "bone"),
                items=(["bone", "soft"],),
                hide_details=True,
                density="compact",
                style="max-width: 180px;",
            )
            v3.VBtn("Reset Camera", click=ctrl.view_reset_camera, density="compact", variant="tonal")
        with layout.content:
            with v3.VContainer(fluid=True, classes="pa-0 fill-height"):
                view = vtk_widgets.VtkRemoteView(render_window, interactive_ratio=1, interactive_quality=90)
                view_ref["view"] = view
                ctrl.view_update = safe_update
                ctrl.view_reset_camera = safe_reset_camera
    print("[trame] ui built", flush=True)

    print("[trame] starting server", flush=True)
    server.start(
        exec_mode="main",
        backend="tornado",
        host=args.host,
        port=args.port,
        open_browser=False,
        show_connection_info=False,
    )
    print("[trame] server stopped", flush=True)


if __name__ == "__main__":
    main()
