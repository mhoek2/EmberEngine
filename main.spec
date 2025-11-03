# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile

#try:
#    base_dir = os.path.dirname(__file__)
#except NameError:
#    base_dir = os.getcwd()  # fallback if __file__ isn't defined
#
#sys.path.append(os.path.join(base_dir, "build_scripts"))
#
#import installer

# ------------------------------------------------------
# Copy asset folders
# ------------------------------------------------------
files_to_copy = {
    os.path.join("imgui.ini"):         "dist/imgui.ini",
    os.path.join("export.spec"):       "dist/export.spec",
    os.path.join("requirements.txt"):  "dist/requirements.txt",
}

folders_to_copy = {
    "demo_assets": "dist/assets",
    "shaders": "dist/shaders",
    "engineAssets": "dist/engineAssets",
    "hooks": "dist/hooks"
}

for src, dst in folders_to_copy.items():
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

for src, dst in files_to_copy.items():
    if os.path.isfile(src):
        shutil.copy2(src, dst)

# ------------------------------------------------------
# Configuration
# ------------------------------------------------------
datas = [
    ('main.py',        'core'),
    ('modules',        'core/modules'),
    ('gameObjects',    'core/gameObjects'),
    ('assimp',         'core/assimp'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('assimp/assimp.dll', 'pygame.')],
    datas=datas,
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
