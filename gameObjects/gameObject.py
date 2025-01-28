import os, sys
from pathlib import Path
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np
from pyrr import Matrix44, Vector3
from typing import TYPE_CHECKING, TypedDict

from modules.context import Context

from modules.cubemap import Cubemap
from modules.material import Material
from modules.images import Images
from modules.models import Models

import importlib
import traceback

class GameObject( Context ):
    class Script(TypedDict):
        file: Path
        obj: None

    def addScript( self, file : Path ):
        self.scripts.append( { "file": file, "obj": "" } )

    def removeScript( self, file : Path ):
        #self.scripts = [script for script in self.scripts if script['file'] != file]
        for script in self.scripts:
            if script['file'] == file:
                self.scripts.remove(script)
                break

    def _get_class_name_from_script(self, script: Path) -> str:
        """Scan the content of the script to find the first class name."""
        if os.path.isfile(script):
            code = script.read_text()

        for line in code.splitlines():
            if line.strip().startswith("class "):
                class_name = line.strip().split()[1].split('(')[0]

                if class_name.endswith(":"):
                    return class_name[:-1]

                return class_name
        return None

    def _init_external_script( self, script ):
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
        for script in self.scripts:
            try:
                self._init_external_script( script )
                script["obj"].onStart()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e )

    def onUpdateScripts( self ):
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
                 scripts : Path = []
                 ) -> None:

        super().__init__( context )

        self.materials      : Material = context.materials
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
        self.model_file = model_file if model_file else False

        self.onStart()

        # external scripts
        for file in scripts:
            self.addScript( file )

        return

    def _createModelMatrix( self ):
        """Create model matrix with translation, rotation and scale vectors"""
        model = Matrix44.identity()
        model = model * Matrix44.from_translation( Vector3( [self.translate[0], self.translate[1], self.translate[2]] ) )
        model = model * Matrix44.from_eulers( Vector3([self.rotation[0], self.rotation[1], self.rotation[2]] ) )
        return model * Matrix44.from_scale( Vector3( [self.scale[0], self.scale[1], self.scale[2]] ) )

    def onStart( self ) -> None:
        """Implemented by inherited class"""
        return

    def onUpdate( self ) -> None:
        """Implemented by inherited class"""
        return
    