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

import inspect
import importlib
import traceback

import copy
import pybullet as p

class GameObject( Context ):
    """Base class for gameObjects """

    class Script(TypedDict):
        file: Path
        obj: None

    def addScript( self, file : Path ):
        """Add script to a gameObject

        :param file: The path to a .py script file
        :type file: Path
        """
        relative_path = file.relative_to(self.settings.rootdir)

        self.console.log( self.console.Type_.note, [], f"Load script: {relative_path}" )

        self.scripts.append( { "file": relative_path, "obj": "" } )

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

    def get_class_name_from_script(self, script: Path) -> str:
        """Scan the content of the script to find the first class name.

        :param script: The path to a .py script file
        :type script: Path
        :return: A class name if its found, return None otherwise
        :rtype: str | None
        """
        file = (self.settings.rootdir / script).resolve()

        if os.path.isfile(file):
            code = file.read_text()

        for line in code.splitlines():
            if line.strip().startswith("class "):
                class_name = line.strip().split()[1].split('(')[0]

                if class_name.endswith(":"):
                    return class_name[:-1]

                return class_name

        return None

    def init_external_script( self, script : Script ):
        """Initialize script attached to this gameObject,
        Try to load and parse the script, then convert to module in sys.

        :param script: The Script object containing a file path
        :type script: GameObject.Script
        """
        __func_name__ = inspect.currentframe().f_code.co_name

        script["obj"] = False

        # Get full file path
        file_path = script['file']

        # Resolve relative paths (important when running from .exe)
        if not os.path.isabs(file_path):
            # Assuming your engine has a context.project_root or similar path
            base_path = getattr(self.context, "project_root", os.getcwd())
            file_path = os.path.join(base_path, file_path)

        if not os.path.isfile(file_path):
            self.console.log( self.console.Type_.note, [], 
                f"[{__func_name__}] Script file not found: {file_path}")
            return

        # Derive a simple module name from the file name
        module_name = os.path.splitext(os.path.basename(file_path))[0]

        # Remove from sys.modules if already loaded (hot reload)
        if module_name in sys.modules:
            del sys.modules[module_name]

        # Load the module from the file path
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            self.console.log( self.console.Type_.note, [], 
                f"[{__func_name__}] Failed to load spec for {file_path}")
            return

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Load ScriptBehaivior
        _script_behavior = importlib.import_module("gameObjects.scriptBehaivior")
        ScriptBehaivior = getattr(_script_behavior, "ScriptBehaivior")


        _class_name = self.get_class_name_from_script(script["file"])

        if not hasattr(module, _class_name):
            self.console.log( self.console.Type_.note, [], 
                f"[{__func_name__}] No class named '{_class_name}' found in {file_path}")
            return

        ScriptClass = getattr(module, _class_name)

        class ClassPlaceholder(ScriptBehaivior, ScriptClass):
            def __init__(self, context, gameObject):
                ScriptBehaivior.__init__(self, context, gameObject)
                if hasattr(ScriptClass, "__init__"):
                    try:
                        ScriptClass.__init__(self)
                    except TypeError:
                        pass

        script["obj"] = ClassPlaceholder(self.context, self)

        self.console.log( self.console.Type_.note, [], 
            f"[{__func_name__}] Loaded script '{_class_name}' from {file_path}")

    def onStartScripts( self ):
        """Call onStart() function in all dynamic scripts attached to this gameObject"""
        for script in self.scripts:
            try:
                self.init_external_script( script )
                script["obj"].onStart()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.log( self.console.Type_.error, traceback.format_tb(exc_tb), e )

    def onUpdateScripts( self ):
        """Call onUpdate() function in all dynamic scripts attached to this gameObject"""
        for script in filter(lambda x: x["obj"] is not False, self.scripts):
            try:
                script["obj"].onUpdate()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.log( self.console.Type_.error, traceback.format_tb(exc_tb), e )

        self._runPhysics()

    def __init__( self, context, 
                 name = "GameObject",
                 visible = True,
                 model_file = False,
                 material = -1,
                 translate = [ 0.0, 0.0, 0.0 ], 
                 rotation = [ 0.0, 0.0, 0.0 ], 
                 scale = [ 1.0, 1.0, 1.0 ],
                 mass = -1.0,
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
        :param translate: The position of the object, using getter and setter
        :type translate: List
        :param rotation: The rotation of the object, using getter and setter
        :type rotation: List
        :param scale: The scale of the object
        :type scale: Vector3
        :param mass: The mass of the object, -1.0 is noy physics?
        :type mass: float
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

        self._removed       : bool = False
        
        # https://github.com/adamlwgriffiths/Pyrr

        self._translate = self.vectorInterface( translate, self._update_physics_body )
        self._rotation  = self.vectorInterface( rotation, self._update_physics_body )

        self.scale      = scale
        self.mass       = mass

        # model
        self.model          : int = -1
        self.model_file = Path(model_file) if model_file else False

        # physics
        self.physics_id = None

        self.onStart()

        # external scripts
        for file in scripts:
            self.addScript( file )

    class vectorInterface(list):
        def __init__(self, data, callback):
            super().__init__(data)
            self._callback = callback

        def _trigger(self):
            if self._callback:
                self._callback()

        def __setitem__(self, key, value):
            """
            !important
            only update physics when value changed (gui or script)
            this is detected by the data type specifier,
            physics engine : tuple
            gui or scripts : list, int, float
            """
            update_physics : bool = isinstance(value, (list, int, float));

            if isinstance(key, slice):
                if not isinstance(value, type(self)):
                    value = type(self)( value, self._callback )
                    #print("(physics engine)");

            super().__setitem__(key, value)

            if update_physics:
                self._trigger()
                #print("(gui-script)");

        def __iadd__(self, other):
            result = super().__iadd__(other)
            self._trigger()
            return result

        def __isub__(self, other):
            result = super().__isub__(other)
            self._trigger()
            return result

    @property
    def translate(self):
        return self._translate
    
    @translate.setter
    def translate(self, data):
        self._translate.__setitem__(slice(None), data)

    @property
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    def rotation(self, data):
        self._rotation.__setitem__(slice(None), data)

    def _update_physics_body(self):
        """
        Physics engine requires are update call 
        whenever translation or rotation has changed externally (gui or script)
        """
        print("update")
        if self.physics_id is None or self.mass < 0.0:
            return
        
        p.resetBasePositionAndOrientation( 
            self.physics_id, 
            self.translate, 
            p.getQuaternionFromEuler( self.rotation ) 
        )
   
    def _save_state(self):
        """Save a snapshot of the full GameObject state."""

        self._state_snapshot = {
            "translate" : list(self.translate),
            "rotation"  : list(self.rotation),
            "scale"     : copy.deepcopy(self.scale),
            "visible"   : self.visible,
            "material"  : self.material,
            "scripts"   : copy.deepcopy(self.scripts),
        }
        print("here")

    def _restore_state(self):
        """Restore the object to the saved initial state."""
        if not hasattr(self, "_state_snapshot"):
            return

        state = self._state_snapshot
        self.translate  = state["translate"]
        self.rotation   = state["rotation"]
        self.scale      = copy.deepcopy(state["scale"])
        self.visible    = state["visible"]
        self.material   = state["material"]
        self.scripts    = copy.deepcopy(state["scripts"])

    def _createModelMatrix( self ) -> Matrix44:
        """Create model matrix with translation, rotation and scale vectors"""
        model = Matrix44.identity()
        model = model * Matrix44.from_translation( Vector3( [self.translate[0], self.translate[1], self.translate[2]] ) )
        model = model * Matrix44.from_eulers( Vector3([self.rotation[0], self.rotation[1], self.rotation[2]] ) )
        return model * Matrix44.from_scale( Vector3( [self.scale[0], self.scale[1], self.scale[2]] ) )

    def _initPhysics( self ) -> None:
        """Initialize physics for this gameObject, sets position, orientation and mass"""
        if self.mass < 0.0:
            return

        collision_shape = p.createCollisionShape(
            p.GEOM_BOX, 
            halfExtents = self.scale
        )

        self.physics_id = p.createMultiBody(
            baseMass                = self.mass, 
            baseCollisionShapeIndex = collision_shape, 
            basePosition            = self.translate,
            baseOrientation         = p.getQuaternionFromEuler(self.rotation)
        )

    def _deInitPhysics( self) -> None:
        if self.physics_id is None or self.mass < 0.0:
            return

        p.removeBody( self.physics_id )
        self.physics_id = None

    def _runPhysics( self ):
        """Run phyisics engine on this gameObject updating position and orientation"""
        if self.physics_id is None or self.mass < 0.0:
            return

        pos, rot = p.getBasePositionAndOrientation( self.physics_id )
        rotation_quat = p.getEulerFromQuaternion( rot )

        #if list(pos) != list(self._translate):
        self.translate = pos

        #if list(rotation_quat) != list(self.rotation):
        self.rotation = rotation_quat

    def onStart( self ) -> None:
        """Implemented by inherited class"""
        pass

    def onUpdate( self ) -> None:
        """Implemented by inherited class"""
        pass
    