import io
import os
import threading
import subprocess
import sys
import logging
import PyInstaller.__main__

import subprocess
import urllib.request
import zipfile
import shutil

from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, TypedDict
import json

from modules.console import Console
from modules.settings import Settings

if TYPE_CHECKING:
    from main import EmberEngine

import traceback

class ProjectManager:
    class Project(TypedDict):
        """Typedef for a scene file"""
        name            : str
        default_scene   : str

    def __init__( self, context ) -> None:
        """Project manager

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        self.context    : 'EmberEngine' = context
        self.settings   : Settings = context.settings
        self.console    : Console = context.console

        self.project_cfg = f"{self.settings.assets}\\project.cfg"

        self.meta : ProjectManager.Project = ProjectManager.Project()
        self.load()

    def setDefaultScene( self, scene_uid : str ):
        """Set default/startup scene of the project
        
        :param scene_uid: The scene UID of the to be default scene
        :type scene_uid: str
        """
        self.meta["default_scene"] = scene_uid

    def save( self ):
        """Save the project settings"""
        meta : ProjectManager.Project = ProjectManager.Project()
        meta["name"]           = "New project"
        meta["default_scene"]  = self.meta["default_scene"]

        with open(self.project_cfg, 'w') as buffer:
            json.dump(meta, buffer, indent=4)


        self.console.addEntry( self.console.ENTRY_TYPE_NOTE, [], f"Saved project" )

    def load( self ):
        """Load and decode JSON from the project config file"""
        try:
            with open(self.project_cfg, 'r') as buffer:
                meta : ProjectManager.Project = json.load(buffer)
                self.meta["name"] = meta["name"]
                self.meta["default_scene"] = meta.get("default_scene", "engine_default")
                print(self.meta)

        except Exception as e:
            print( e )
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e )




    #
    # Exporting project
    #
    def ensure_embedded_python( self ):
        EMBED_PYTHON_VERSION = "3.12.7"
        EMBED_PYTHON_ZIP_URL = f"https://www.python.org/ftp/python/{EMBED_PYTHON_VERSION}/python-{EMBED_PYTHON_VERSION}-embed-amd64.zip"

        EMBED_DIR       = "python"
        EMBED_EXE       = os.path.join(EMBED_DIR, "python.exe")
        EMBED_PTH       = os.path.join(EMBED_DIR, f"python{EMBED_PYTHON_VERSION[:4].replace('.', '')}._pth")
        EMBED_DLL       = f"python{EMBED_PYTHON_VERSION[:4].replace('.', '')}.dll"
        EMBED_ZIP       = f"python{EMBED_PYTHON_VERSION[:4].replace('.', '')}.zip"

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

    def run_pyinstaller( self, console : Console ):
        if getattr(sys, "frozen", False):
            self.ensure_embedded_python() # setup embedded python

            python_exe = os.path.join(os.getcwd(), "python", "python.exe")
            os.environ["EE_CORE_DIR"] = os.path.join(sys._MEIPASS, "core")
        else:
            python_exe = sys.executable
            os.environ["EE_CORE_DIR"] = os.getcwd()


        cmd = [
            python_exe, "-m", "PyInstaller",
            "export.spec",
            "--noconfirm",
            "--clean",
            "--distpath", "export",
        ]
        #            "--log-level=DEBUG"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )

        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            if "ERROR" in line:
                console.addEntry(console.ENTRY_TYPE_ERROR, [], line)
            elif "WARNING" in line or "WARN" in line:
                console.addEntry(console.ENTRY_TYPE_WARNING, [], line)
            else:
                console.addEntry(console.ENTRY_TYPE_NOTE, [], line)

        process.wait()

        console.addEntry(console.ENTRY_TYPE_NOTE, [], "Cleanup temporary file")
        for src in ["temp", "build"]:
            if os.path.exists(src):
                shutil.rmtree(src)
                

        if process.returncode == 0:
            console.addEntry(console.ENTRY_TYPE_NOTE, [], "Export complete.")
        else:
            console.addEntry(console.ENTRY_TYPE_ERROR, [], f"PyInstaller failed with code {process.returncode}")


    def export( self ):
        self.console.addEntry(self.console.ENTRY_TYPE_NOTE, [], "Exporting project...")

        try:
            thread = threading.Thread(target=self.run_pyinstaller, args=(self.console,), daemon=True)
            thread.start()
        except Exception as e:
            print( e )
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e )

