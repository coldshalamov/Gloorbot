# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Gloorbot Worker
# Bundles PARALLEL folder and Playwright dependencies

import os
import sys
from pathlib import Path

block_cipher = None

# Paths relative to this spec file
spec_dir = Path(SPECPATH)
repo_root = spec_dir.parent.parent  # apps/worker -> repo root
parallel_dir = repo_root / 'PARALLEL'

a = Analysis(
    ['src/gloorbot_worker/__main__.py'],
    pathex=[str(spec_dir / 'src')],
    binaries=[],
    datas=[
        # Bundle PARALLEL folder with scraper.py
        (str(parallel_dir), 'PARALLEL'),
    ],
    hiddenimports=[
        'playwright',
        'playwright.async_api',
        'playwright.sync_api',
        'httpx',
        'tkinter',
    ],
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
    name='GloorbotWorker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed app (no console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GloorbotWorker',
)
