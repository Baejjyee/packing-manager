# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir build for Packing Manager."""

import os
import sys
from pathlib import Path


# This Mac has a broken Xcode.app toolchain selection, while the standalone
# Command Line Tools are healthy. Windows builds do not enter this branch.
if sys.platform == "darwin":
    command_line_tools = Path("/Library/Developer/CommandLineTools/usr/bin")
    if command_line_tools.is_dir():
        os.environ["PATH"] = f"{command_line_tools}{os.pathsep}{os.environ['PATH']}"


analysis = Analysis(
    ["main.py"],
    pathex=["src"],
    binaries=[],
    datas=[("assets/fonts", "assets/fonts")],
    hiddenimports=[
        "PySide6.QtPdf",
        "PySide6.QtPrintSupport",
        "packing_manager.printing.windows_printer",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

executable = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="PackingManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PackingManager",
)
