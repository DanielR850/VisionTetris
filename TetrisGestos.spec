# -*- mode: python ; coding: utf-8 -*-

ONEFILE = True      # True: un solo .exe ; False: carpeta
CONSOLE = True      # True: con consola; False: sin consola
APP_NAME = "TetrisGestos"
ENTRY_SCRIPT = "main.py"

import os
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
)

# Recolección de recursos de terceros
mp_datas = collect_data_files("mediapipe", include_py_files=False)
mp_hidden = collect_submodules("mediapipe")

cv2_datas = collect_data_files("cv2", include_py_files=False)
cv2_bins  = collect_dynamic_libs("cv2")

pg_datas = collect_data_files("pygame", include_py_files=False)

# Carpeta de recursos del proyecto (usa tu ruta local -> destino dentro del bundle)
proj_datas = [(os.path.join(os.getcwd(), "Recursos"), "Recursos")]

a = Analysis(
    [ENTRY_SCRIPT],
    pathex=[os.getcwd()],
    binaries=cv2_bins,  # DLLs de OpenCV
    datas=mp_datas + cv2_datas + pg_datas + proj_datas,
    hiddenimports=mp_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["cairosvg", "cairocffi", "cairo", "pycairo"],
    noarchive=False,
)

pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=CONSOLE,
        disable_windowed_traceback=False,
        # icon='icon.ico',
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=CONSOLE,
        disable_windowed_traceback=False,
        # icon='icon.ico',
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )
