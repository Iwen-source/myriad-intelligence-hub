import os
import locale
import vtk


def setup_utf8_locale() -> bool:
    # Make sure window title text is encoded/decoded under UTF-8 locale.
    candidates = ["", "C.UTF-8", "en_US.UTF-8", "zh_CN.UTF-8"]
    for loc in candidates:
        try:
            locale.setlocale(locale.LC_ALL, loc)
            current = locale.setlocale(locale.LC_CTYPE)
            if "UTF-8" in current.upper() or "UTF8" in current.upper():
                return True
        except locale.Error:
            continue
    return False


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
    else:  # soft tissue
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

    volume_property = vtk.vtkVolumeProperty()
    volume_property.SetColor(color)
    volume_property.SetScalarOpacity(opacity)
    volume_property.SetGradientOpacity(grad_opacity)
    volume_property.ShadeOn()
    volume_property.SetInterpolationTypeToLinear()
    volume_property.SetAmbient(0.15)
    volume_property.SetDiffuse(0.9)
    volume_property.SetSpecular(0.25)
    volume_property.SetSpecularPower(12.0)
    return volume_property


class KeyPressInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, volume_actor, mapper, render_window, renderer):
        super().__init__()
        self.volume_actor = volume_actor
        self.mapper = mapper
        self.render_window = render_window
        self.renderer = renderer
        self.preset = "bone"
        self.show_help = True
        self.help_actor = None
        self.AddObserver("KeyPressEvent", self.on_key_press)

    def set_help_actor(self, help_actor):
        self.help_actor = help_actor

    def on_key_press(self, obj, event):
        key = self.GetInteractor().GetKeySym().lower()
        if key == "1":
            self.preset = "bone"
            self.volume_actor.SetProperty(build_volume_property("bone"))
        elif key == "2":
            self.preset = "soft"
            self.volume_actor.SetProperty(build_volume_property("soft"))
        elif key == "h" and self.help_actor is not None:
            self.show_help = not self.show_help
            self.help_actor.SetVisibility(1 if self.show_help else 0)
        elif key == "r":
            self.renderer.ResetCamera()
        elif key == "m":
            mode = self.mapper.GetBlendMode()
            if mode == vtk.vtkVolumeMapper.COMPOSITE_BLEND:
                self.mapper.SetBlendModeToMaximumIntensity()
            else:
                self.mapper.SetBlendModeToComposite()
        self.render_window.Render()
        self.OnKeyPress()


def create_help_text_actor() -> vtk.vtkTextActor:
    txt = vtk.vtkTextActor()
    txt.SetInput(
        "Mouse: Rotate/Pan/Zoom | 1: Bone preset | 2: Soft preset | "
        "M: Blend mode | R: Reset camera | H: Toggle help"
    )
    txtprop = txt.GetTextProperty()
    txtprop.SetFontSize(18)
    txtprop.SetColor(0.88, 0.88, 0.90)
    txtprop.SetBackgroundColor(0.08, 0.08, 0.09)
    txtprop.SetBackgroundOpacity(0.45)
    txt.SetDisplayPosition(18, 18)
    return txt


def main():
    utf8_ok = setup_utf8_locale()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    nrrd_path = os.path.join(current_dir, "brain_ct.nrrd")
    if not os.path.exists(nrrd_path):
        raise FileNotFoundError(f"未找到 CT 数据: {nrrd_path}")

    reader = vtk.vtkNrrdReader()
    reader.SetFileName(nrrd_path)
    reader.Update()

    volume_mapper = vtk.vtkSmartVolumeMapper()
    volume_mapper.SetInputConnection(reader.GetOutputPort())
    volume_mapper.SetBlendModeToComposite()

    volume = vtk.vtkVolume()
    volume.SetMapper(volume_mapper)
    volume.SetProperty(build_volume_property("bone"))

    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.06, 0.06, 0.07)
    renderer.AddVolume(volume)

    help_actor = create_help_text_actor()
    renderer.AddActor2D(help_actor)

    ren_win = vtk.vtkRenderWindow()
    ren_win.AddRenderer(renderer)
    ren_win.SetSize(1280, 900)
    ren_win.SetWindowName("VTK 3D CT 查看器" if utf8_ok else "VTK 3D CT Viewer")

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(ren_win)

    style = KeyPressInteractorStyle(volume, volume_mapper, ren_win, renderer)
    style.set_help_actor(help_actor)
    interactor.SetInteractorStyle(style)

    renderer.ResetCamera()
    ren_win.Render()
    interactor.Initialize()
    interactor.Start()


if __name__ == "__main__":
    main()
