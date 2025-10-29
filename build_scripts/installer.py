import os
import sys
import shutil
import subprocess
import urllib.request
import zipfile

EMBED_PYTHON_VERSION = "3.12.7"
EMBED_PYTHON_ZIP_URL = f"https://www.python.org/ftp/python/{EMBED_PYTHON_VERSION}/python-{EMBED_PYTHON_VERSION}-embed-amd64.zip"

EMBED_DIR       = os.path.join("dist", "python")
EMBED_EXE       = os.path.join(EMBED_DIR, "python.exe")
EMBED_PTH       = os.path.join(EMBED_DIR, f"python{EMBED_PYTHON_VERSION[:4].replace('.', '')}._pth")
EMBED_DLL       = f"python{EMBED_PYTHON_VERSION[:4].replace('.', '')}.dll"
EMBED_ZIP       = f"python{EMBED_PYTHON_VERSION[:4].replace('.', '')}.zip"

#def get_embedded_python_exe():
#    """Return path to Python executable, either embedded or system."""
#    return EMBED_EXE
#    #if getattr(sys, "frozen", False):
#    #    return EMBED_EXE
#    #
#    #return sys.executable

def ensure_embedded_python():
    """Download embedded Python and install PyInstaller if not already present."""
    if os.path.exists(EMBED_EXE):
        return  # already exists

    print("[installer] Downloading embedded Python...")
    os.makedirs(EMBED_DIR, exist_ok=True)
    zip_path = os.path.join(EMBED_DIR, "python_embed.zip")
    urllib.request.urlretrieve(EMBED_PYTHON_ZIP_URL, zip_path)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(EMBED_DIR)
    os.remove(zip_path)

    print("[installer] Configuring embedded Python...")
    # update _pth file
    with open(EMBED_PTH, "w", encoding="utf-8") as f:
        f.write(
            f"{EMBED_ZIP}\n"
            ".\n"
            "Lib\n"
            "Lib\\site-packages\n"
            "import site"
        )

    # Install PyInstaller
    print("[installer] Installing pip in embedded Python...")
    url = "https://bootstrap.pypa.io/get-pip.py"
    save_path = os.path.join(EMBED_DIR, "get-pip.py")
    urllib.request.urlretrieve(url, save_path)
    subprocess.run([EMBED_EXE, save_path], check=True)

    print("[installer] Upgrade pip in embedded Python...")
    subprocess.run([EMBED_EXE, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    print("[installer] Installing PyInstaller in embedded Python...")
    subprocess.run([EMBED_EXE, "-m", "pip", "install", "pyinstaller"], check=True)

def copy_data_folders():
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

    # copy export.spec
    shutil.copy("build_scripts/export.spec", "dist/export.spec")