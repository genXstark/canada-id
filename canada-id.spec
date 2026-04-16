# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Canada ID desktop app."""
import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all Gradio data files (templates, static assets)
gradio_datas = collect_data_files("gradio")
gradio_client_datas = collect_data_files("gradio_client")

# Collect hidden imports
hidden_imports = (
    collect_submodules("gradio")
    + collect_submodules("gradio_client")
    + collect_submodules("webview")
    + collect_submodules("canada_id")
    + [
        "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
        "cv2", "numpy", "click",
        "clr_loader", "pythonnet",
        "engineio", "socketio",
        "multipart",
    ]
)

a = Analysis(
    ["desktop.py"],
    pathex=["src"],
    binaries=[],
    datas=gradio_datas + gradio_client_datas,
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
    name="Canada ID",
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
    name="Canada ID",
)
