# -*- mode: python ; coding: utf-8 -*-

import sys, os, shutil, subprocess

temp_dir = "temp"
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
os.makedirs(temp_dir)


git_repo_url = "https://github.com/mhoek2/EmberEngine"  
branch_name = "beta"
clone_dest = os.path.join(temp_dir, "")

subprocess.run([
    "git", "clone", "-b", branch_name, "--single-branch", git_repo_url, clone_dest
], check=True)

# ------------------------------------------------------
# Copy asset folders
# ------------------------------------------------------
folders_to_copy = {
    "assets": "temp/assets",
}
#    "shaders": "temp/shaders",
#    "engineAssets": "temp/engineAssets",

for src, dst in folders_to_copy.items():
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

#datas=[('engineAssets', 'engineAssets')],

a = Analysis(
    ['temp/main.py'],
    pathex=[],
    binaries=[('temp/assimp/assimp.dll', 'pygame.')],
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
