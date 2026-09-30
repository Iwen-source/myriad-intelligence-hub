"""
AI Empowerment Platform - Python ML API Server
===============================================
Entry point: app.py
Routes: medical_routes, finance_routes, environment_routes, traffic_routes
Models: model_loader (lazy loading + retry)
CT Workstation: ct/ package (routes + image_processing + session)
Scripts: ../scripts/ (training scripts, moved from models/)
"""

# ---------------------------------------------------------------------------
# VC++ runtime bootstrap (app-local, no admin / no C: drive writes)
# ---------------------------------------------------------------------------
# 背景：本机 System32 的 VC++ 运行库曾被降级（vcruntime140/msvcp140 出现
# 14.00.24215 与 14.5x 混装），导致 PyTorch 加载 c10.dll 时抛
#   OSError [WinError 1114] 动态链接库(DLL)初始化例程失败。
# 解决：随项目携带 14.44 CRT，并在任何 torch 导入之前将其目录加入 DLL 搜索
# 路径（AddDllDirectory 的 user dirs 优先于 System32），从而无需管理员权限、
# 也不占用 C 盘空间即可修复。
#
# 说明：本块必须位于所有 `import torch` 之前。server 包在被 import 时（先于
# server.model_loader）执行，可保证 torch 之前完成注册。
import os as _os


def _bootstrap_vc_runtime() -> None:
    if not hasattr(_os, "add_dll_directory"):
        return  # 非 Windows 平台，无需处理
    _here = _os.path.dirname(_os.path.abspath(__file__))
    _crt_dirs = [
        _os.path.join(_os.path.dirname(_here), "runtime", "crt-x64"),
        # 兜底：OBS 的 app-local CRT（若项目内副本缺失）
        r"D:\software\OBS\obs-studio\bin\64bit",
    ]
    for _d in _crt_dirs:
        if _os.path.isdir(_d):
            try:
                _os.add_dll_directory(_d)
            except OSError:
                pass


_bootstrap_vc_runtime()
