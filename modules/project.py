import io
import os
import threading
import subprocess
import sys
import logging
import PyInstaller.__main__

import subprocess
import ssl
import certifi
import urllib.request
import zipfile
import shutil

from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, TypedDict
import json
import re

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
        export_clean    : bool
        export_debug    : bool

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
        meta["name"]           = self.meta.get("name") or self.settings.project_default_name
        meta["default_scene"]  = self.meta.get("default_scene")
        meta["export_clean"]   = self.meta.get("export_clean")
        meta["export_debug"]   = self.meta.get("export_debug")

        with open(self.project_cfg, 'w') as buffer:
            json.dump(meta, buffer, indent=4)

        self.console.note( f"Saved project" )

    def load( self ):
        """Load and decode JSON from the project config file"""
        try:
            with open(self.project_cfg, 'r') as buffer:
                meta : ProjectManager.Project = json.load(buffer)
                self.meta["name"]           = meta.get("name", self.settings.project_default_name)
                self.meta["default_scene"]  = meta.get("default_scene", "engine_default")
                self.meta["export_clean"]   = meta.get("export_clean", self.settings.export_clean)
                self.meta["export_debug"]   = meta.get("export_debug", self.settings.export_debug)
                
                print("------------ loaded project configuration ------------")
                print( self.meta )

        except Exception as e:
            print( e )
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.error( e, traceback.format_tb(exc_tb) )

    #
    # Exporting project
    #
    EMBED_PYTHON_VERSION = "3.11.7"
    EMBED_PYTHON_ZIP_URL = f"https://www.python.org/ftp/python/{EMBED_PYTHON_VERSION}/python-{EMBED_PYTHON_VERSION}-embed-amd64.zip"

    EMBED_DIR       = "python"
    EMBED_EXE       = os.path.join(EMBED_DIR, "python.exe")
    EMBED_PTH       = os.path.join(EMBED_DIR, f"python{EMBED_PYTHON_VERSION[:4].replace('.', '')}._pth")
    EMBED_DLL       = f"python{EMBED_PYTHON_VERSION[:4].replace('.', '')}.dll"
    EMBED_ZIP       = f"python{EMBED_PYTHON_VERSION[:4].replace('.', '')}.zip"

    def sanitize_executable_filename( self, name: str ) -> str:

        name = re.sub(self.settings.executable_format, "", name) 
        name = name.strip()

        if not name:
            name = "export"

        # replace spaces with underscores
        name = name.replace(" ", "_")

        return name

    def run_process( self, console : Console, command, label ):
        """Helper to run a subprocess with live stdout streaming."""
        print(f"[installer] Running: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            console.log( line )

        process.wait()
                
        if process.returncode == 0:
            console.note( f"{label} complete." )
        else:
            console.error( f"{label} failed with code {process.returncode}" )

    def ensure_embedded_python( self, console : Console ):
        """Download embedded Python and install PyInstaller if not already present."""
        if os.path.exists(self.EMBED_EXE):
            return  # already exists

        ssl_context = ssl.create_default_context(cafile=certifi.where())

        print("[installer] Downloading embedded Python...")
        os.makedirs(self.EMBED_DIR, exist_ok=True)
        zip_path = os.path.join(self.EMBED_DIR, "python_embed.zip")
        #urllib.request.urlretrieve(self.EMBED_PYTHON_ZIP_URL, zip_path, context=ssl_context)
        with urllib.request.urlopen(self.EMBED_PYTHON_ZIP_URL, context=ssl_context) as response:
            with open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(self.EMBED_DIR)
        os.remove(zip_path)

        print("[installer] Configuring embedded Python...")
        # update _pth file
        with open(self.EMBED_PTH, "w", encoding="utf-8") as f:
            f.write(
                f"{self.EMBED_ZIP}\n"
                ".\n"
                "Lib\n"
                "Lib\\site-packages\n"
                "import site"
            )

        # Install PyInstaller
        print("[installer] Installing pip in embedded Python...")
        url = "https://bootstrap.pypa.io/get-pip.py"
        save_path = os.path.join(self.EMBED_DIR, "get-pip.py")
        #urllib.request.urlretrieve(url, save_path, context=ssl_context)
        with urllib.request.urlopen(url, context=ssl_context) as response:
            with open(save_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

        self.run_process( console, [self.EMBED_EXE, save_path], "pip install")
        self.run_process( console, [self.EMBED_EXE, "-m", "pip", "install", "--upgrade", "pip"], "pip upgrade")

        print("[installer] Embedded Python setup complete.")

    def ensure_embedded_python_requirements( self, console : Console ) -> None:
        """Installs python requirements needed to package the application"""
        self.run_process( console, [self.EMBED_EXE, "-m", "pip", "install", "-r", "requirements.txt"], "ensure dependencies")

    def run_pyinstaller( self, console : Console ):
        # project settings
        os.environ["EE_EXPORT_EXEC_NAME"] = self.sanitize_executable_filename( self.meta.get("name") );
        os.environ["EE_EXPORT_DEBUG_MODE"] = "1" if self.meta.get("export_debug") else "0"

        if getattr(sys, "frozen", False):
            # for packaged version, install embedded python.
            self.ensure_embedded_python( console )
            self.ensure_embedded_python_requirements( console)

            python_exe = os.path.join(os.getcwd(), "python", "python.exe")
            os.environ["EE_CORE_DIR"] = os.path.join(sys._MEIPASS, "core")
        else:
            python_exe = sys.executable
            os.environ["EE_CORE_DIR"] = os.getcwd()

        cmd = [
            python_exe, "-m", "PyInstaller",
            "export.spec",
            "--noconfirm",
            "--distpath", "export",
        ]
        #            "--log-level=DEBUG"

        if self.meta.get("export_clean"):
            cmd.append("--clean")

        self.run_process( console, cmd, "PyInstaller")

        console.note( "Cleanup temporary file" )
        for src in ["temp", "build"]:
            if os.path.exists(src):
                shutil.rmtree(src)

    def export( self ):
        self.console.note( "Exporting project..." )

        try:
            thread = threading.Thread(target=self.run_pyinstaller, args=(self.console,), daemon=True)
            thread.start()
        except Exception as e:
            print( e )
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.error( e, traceback.format_tb(exc_tb) )

