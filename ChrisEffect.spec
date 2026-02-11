# -*- mode: python ; coding: utf-8 -*-
"""
Chris Effect Inventory System - PyInstaller Spec File
Builds a standalone Windows executable (.exe)
"""

from PyInstaller.utils.hooks import collect_all
import sys
import os

block_cipher = None

# Collect all data files for ttkbootstrap (modern UI theme)
datas = [
    ('ceicon.ico', '.'),
    ('templates/', 'templates'),
    ('images/', 'images'),
]

binaries = []
hiddenimports = [
    'ttkbootstrap',
    'ttkbootstrap.constants',
    'PIL',
    'sqlite3',
    'csv',
    'uuid',
    'shutil',
    'hashlib',
]

# Collect all ttkbootstrap data
tmp_ret = collect_all('ttkbootstrap')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'django',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ChrisEffect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI only)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ceicon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ChrisEffect',
)
