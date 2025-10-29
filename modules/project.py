import io
import os
import threading
import subprocess
import sys
import logging
import PyInstaller.__main__

import subprocess
from build_scripts import installer

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

    def run_pyinstaller( self, console : Console ):
        if getattr(sys, "frozen", False):
            #python_exe = sys._MEIPASS + "/python/python.exe"
            python_exe = os.path.join(os.getcwd(), "python", "python.exe")
        else:
            python_exe = sys.executable



        #python_exe = installer.get_embedded_python_exe()

        #installer.ensure_embedded_python()

        cmd = [
            python_exe, "-m", "PyInstaller",
            "export.spec",
            "--noconfirm",
            "--clean",
            "--distpath", "output",
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

