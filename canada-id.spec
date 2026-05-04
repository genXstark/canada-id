# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Canada ID desktop app."""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all Gradio data files (templates, static assets)
# include_py_files=True: Gradio reads its own .py files at runtime
# for pyi stub generation (component_meta.create_or_modify_pyi)
gradio_datas = collect_data_files("gradio", include_py_files=True)
gradio_client_datas = collect_data_files(
    "gradio_client", include_py_files=True,
)
safehttpx_datas = collect_data_files("safehttpx")
groovy_datas = collect_data_files("groovy", include_py_files=False)

# Collect hidden imports
hidden_imports = (
    collect_submodules("gradio")
    + collect_submodules("gradio_client")
    + collect_submodules("webview")
    + collect_submodules("canada_id")
    + collect_submodules("safehttpx")
    + [
        "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
        "cv2", "numpy", "click",
        "clr_loader", "pythonnet",
        "engineio", "socketio",
        "multipart",
        "safehttpx",
    ]
)

a = Analysis(
    ["desktop.py"],
    pathex=["src"],
    binaries=[],
    datas=gradio_datas + gradio_client_datas + safehttpx_datas + groovy_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="moviepropIDgen",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="moviepropIDgen",
)
