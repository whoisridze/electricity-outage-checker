# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for electricity-outage-checker."""

import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Build universal2 binary on macOS (Intel + Apple Silicon)
target_arch = 'universal2' if sys.platform == 'darwin' else None

# Collect data files from dependencies
datas = []
datas += collect_data_files('rich')

a = Analysis(
    ['run.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'rich',
        'typer',
        'httpx',
        'httpx._client',
        'httpx._config',
        'httpx._exceptions',
        'httpx._models',
        'httpx._transports',
        'httpx._utils',
        # Unicode/encoding support
        'encodings.utf_8',
        'encodings.idna',
        'encodings.ascii',
        'encodings.latin_1',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='outage-checker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_arch,
    codesign_identity=None,
    entitlements_file=None,
)
