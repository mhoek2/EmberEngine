import os, sys
from pathlib import Path
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np
from pyrr import Matrix44, Vector3
from typing import TYPE_CHECKING, TypedDict, List

from modules.context import Context

from modules.cubemap import Cubemap
from modules.material import Materials
from modules.images import Images
from modules.models import Models

import importlib
import traceback

class GameObject( Context ):
    class Script(TypedDict):
        file: Path
        obj: None

    def addScript( self, file : Path ):
        """Add script to a gameObject
        :param file: The path to a .py script file
        :type file: Path
        """
        self.scripts.append( { "file": file, "obj": "" } )

    def removeScript( self, file : Path ):
        """Remove script from a gameObject
        :param file: The path to a .py script file
        :type file: Path
        """
        #self.scripts = [script for script in self.scripts if script['file'] != file]
        for script in self.scripts:
            if script['file'] == file:
                self.scripts.remove(script)
                break

    def _get_class_name_from_script(self, script: Path) -> str:
        """Scan the content of the script to find the first class name.
        :param script: The path to a .py script file
        :type script: Path
        :return: A class name if its found, return None otherwise
        :rtype: str | None
        """
        if os.path.isfile(script):
            code = script.read_text()

        for line in code.splitlines():
            if line.strip().startswith("class "):
                class_name = line.strip().split()[1].split('(')[0]

                if class_name.endswith(":"):
                    return class_name[:-1]

                return class_name

        return None

    def _init_external_script( self, script : Script ):
        """Initialize script attached to this gameObject,
        Try to load and parse the script, then convert to module in sys.
        :param script: The Script object containing a file path
        :type script: GameObject.Script
        """
        script["obj"] = False

        # module name needs subfolder prefixes with . delimter
        _module_name = str(script['file'].relative_to(self.settings.rootdir))
        _module_name = _module_name.replace("\\", ".").replace(".py", "")

        _class_name = self._get_class_name_from_script( script["file"] )

        _script_behaivior = importlib.import_module("gameObjects.scriptBehaivior")
        ScriptBehaivior = getattr(_script_behaivior, "ScriptBehaivior")

        # remove from sys modules cache
        if _module_name in sys.modules:
            importlib.reload(sys.modules[_module_name])

        module = importlib.import_module( _module_name )
        setattr(module, "ScriptBehaivior", ScriptBehaivior)
        ScriptClass = getattr(module, _class_name)

        class ClassPlaceholder( ScriptClass, ScriptBehaivior ):
            pass

        script["obj"] = ClassPlaceholder( self.context, self )

    def onStartScripts( self ):
        """Call onStart() function in all dynamic scripts attached to this gameObject"""
        for script in self.scripts:
            try:
                self._init_external_script( script )
                script["obj"].onStart()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e )

    def onUpdateScripts( self ):
        """Call onUpdate() function in all dynamic scripts attached to this gameObject"""
        for script in filter(lambda x: x["obj"] is not False, self.scripts):
            try:
                script["obj"].onUpdate()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e )

    def __init__( self, context, 
                 name = "GameObject",
                 visible = True,
                 model_file = False,
                 material = -1,
                 translate = [ 0.0, 0.0, 0.0 ], 
                 rotation = [ 0.0, 0.0, 0.0 ], 
                 scale = [ 1.0, 1.0, 1.0 ],
                 scripts : List[Path] = []
                 ) -> None:
        """Base class for gameObjects 
        :param context: This is the main context of the application
        :type context: EmberEngine
        :param name: The name that is stored with the gameObject
        :type name: str
        :param visible: If the gameObject is drawn
        :type visible: bool
        :param model_file: The file path to a model file
        :type model_file: Path | bool
        :param material: The index in the material buffer as override, -1 is default
        :type material: int
        :param translate: The position of the object
        :type translate: Vector3
        :param rotation: The rotation of the object
        :type rotation: Vector3
        :param scale: The scale of the object
        :type scale: Vector3
        :param scripts: A list containing Paths to dynamic scripts
        :type scripts: List[scripts]
        """
        super().__init__( context )

        self.materials      : Materials = context.materials
        self.images         : Images = context.images
        self.cubemaps       : Cubemap = context.cubemaps
        self.models         : Models = context.models

        self.scripts        : list[GameObject.Script] = []

        self.name           : str = name
        self.material       : int = material
        self.visible        : bool = visible

        self._removed        : bool = False
        
        # https://github.com/adamlwgriffiths/Pyrr
        self.translate = translate
        self.rotation = rotation
        self.scale = scale

        # model
        self.model          : int = -1
        self.model_file = Path(model_file) if model_file else False

        self.onStart()

        # external scripts
        for file in scripts:
            self.addScript( file )

    def _createModelMatrix( self ) -> Matrix44:
        """Create model matrix with translation, rotation and scale vectors"""
        model = Matrix44.identity()
        model = model * Matrix44.from_translation( Vector3( [self.translate[0], self.translate[1], self.translate[2]] ) )
        model = model * Matrix44.from_eulers( Vector3([self.rotation[0], self.rotation[1], self.rotation[2]] ) )
        return model * Matrix44.from_scale( Vector3( [self.scale[0], self.scale[1], self.scale[2]] ) )

    def onStart( self ) -> None:
        """Implemented by inherited class"""
        pass

    def onUpdate( self ) -> None:
        """Implemented by inherited class"""
        pass
    