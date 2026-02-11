# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Store Inventory Manager desktop application

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('store_inventory.db', '.'),
        ('images', 'images'),
    ],
    hiddenimports=[
        'flask',
        'flask_cors',
        'webview',
        'sqlite3',
        'csv',
        'uuid',
        'shutil',
        'hashlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StoreInventoryManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for desktop app
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if desired
)
