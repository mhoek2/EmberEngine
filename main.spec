# -*- mode: python ; coding: utf-8 -*-

import sys, os

try:
    base_dir = os.path.dirname(__file__)
except NameError:
    base_dir = os.getcwd()  # fallback if __file__ isn't defined

sys.path.append(os.path.join(base_dir, "build_scripts"))

import installer

# ------------------------------------------------------
# Setup environment (download + configure embedded Python)
# ------------------------------------------------------
installer.ensure_embedded_python()

# ------------------------------------------------------
# Copy asset folders
# ------------------------------------------------------
installer.copy_data_folders()

#datas=[('engineAssets', 'engineAssets')],

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('assimp/assimp.dll', 'pygame.')],
    datas=[],
    hiddenimports=['gameObjects.scriptBehaivior'],
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EmberEngine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
	icon='engineAssets/icon/icon.ico',
)
