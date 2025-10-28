# -*- mode: python ; coding: utf-8 -*-
import os
import shutil

folders_to_copy = {
    "demo_assets": "dist/assets",
    "shaders": "dist/shaders",
    "engineAssets": "dist/engineAssets"
}

for src, dst in folders_to_copy.items():
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

# move imgui.ini
imgui_ini_src = os.path.join("dist", "assets", "imgui.ini")
imgui_ini_dst = os.path.join("dist", "imgui.ini")
if os.path.exists(imgui_ini_src):
    shutil.move(imgui_ini_src, imgui_ini_dst)

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
