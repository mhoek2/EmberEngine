import sys
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
