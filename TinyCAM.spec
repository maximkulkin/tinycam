# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['tinycam/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tinycam.icons_rc',
        'tinycam.textures_rc',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'moderngl',
        'moderngl_window',
        'qasync',
        'shapely',
        'shapely.geometry',
        'shapely.affinity',
        'shapely.ops',
        'pyrr',
        'blinker',
        'serial',
        'serial_asyncio',
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
    name='TinyCAM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TinyCAM',
)

app = BUNDLE(
    coll,
    name='TinyCAM.app',
    icon='build/TinyCAM.icns',
    bundle_identifier='com.tinycam.app',
    info_plist={
        'CFBundleName': 'TinyCAM',
        'CFBundleDisplayName': 'TinyCAM',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'SVG File',
                'CFBundleTypeExtensions': ['svg'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Alternate',
            },
            {
                'CFBundleTypeName': 'Gerber File',
                'CFBundleTypeExtensions': ['gbr'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
            {
                'CFBundleTypeName': 'Excellon Drill File',
                'CFBundleTypeExtensions': ['drl'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            },
        ],
    },
)
