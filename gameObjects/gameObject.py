#from __future__ import annotations # used for "GameObject" forward reference in same scope

import os, sys
from pathlib import Path
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np
from pyrr import Matrix44, Vector3, Quaternion, euler
from typing import TYPE_CHECKING, TypedDict, List

from pyrr.objects import quaternion

from modules.context import Context

from modules.cubemap import Cubemap
from modules.material import Materials
from modules.images import Images
from modules.models import Models
from modules.transform import Transform

import inspect
import importlib
import traceback

import copy, math
import pybullet as p

class GameObject( Context, Transform ):
    """Base class for gameObjects """
    def __init__( self, context, 
                 name           = "GameObject",
                 visible        = True,
                 model_file     = False,
                 material       = -1,
                 translate      = [ 0.0, 0.0, 0.0 ], 
                 rotation       = [ 0.0, 0.0, 0.0 ], 
                 scale          = [ 1.0, 1.0, 1.0 ],
                 mass           = -1.0,
                 scripts        : List[Path] = []
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

        self.children       : List[GameObject] = []
        self.parent         : GameObject = None

        self.transform      : Transform = Transform(
            context=self.context,
            gameObject=self,
            translate=translate,
            rotation=rotation,
            scale=scale,
            name=name
        )

        # model
        self.model          : int = -1
        self.model_file     = Path(model_file) if model_file else False

        # physics
        self.physics_id     : int = None
        self.mass           : float = mass

        self._dirty         : bool = True
        self._removed       : bool = False

        self.onStart()

        # external scripts
        for file in scripts:
            self.addScript( file )

    def setParent( self, parent : "GameObject" ) -> None:
        """Set relation between child and parent object"""
        parent.children.append(self)
        self.parent = parent

        # needs additional logic for model matrix transforms to keep the current world position
        # bascily, need to update local transform in relation to the new parent world position
        pass

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True

            for c in self.children:
                c._mark_dirty()

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
            self.init_external_script( script )
            script["obj"].onStart()
        #    try:
        #        self.init_external_script( script )
        #        script["obj"].onStart()
        #    except Exception as e:
        #        exc_type, exc_value, exc_tb = sys.exc_info()
        #        self.console.log( self.console.Type_.error, traceback.format_tb(exc_tb), e )

    def onUpdateScripts( self ):
        """Call onUpdate() function in all dynamic scripts attached to this gameObject"""
        for script in filter(lambda x: x["obj"] is not False, self.scripts):
            try:
                script["obj"].onUpdate()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.log( self.console.Type_.error, traceback.format_tb(exc_tb), e )

    def _save_state(self):
        """Save a snapshot of the full GameObject state."""

        self._state_snapshot = {
            "translate" : list(self.transform.local_position),
            "rotation"  : list(self.transform.local_rotation),
            "scale"     : list(self.transform.local_scale),
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
        self.transform.local_position   = state["translate"]
        self.transform.local_rotation   = state["rotation"]
        self.transform.local_scale      = state["scale"]
        self.visible                    = state["visible"]
        self.material                   = state["material"]
        self.scripts                    = copy.deepcopy(state["scripts"])

    #
    # physics
    #
    def _initPhysics( self ) -> None:
        """
        Initialize physics for this gameObject, sets position, orientation and mass
        https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstartguide.pdf
        """
 
        self.transform._createWorldModelMatrix()

        if self.mass < 0.0:
            return

        _, world_rotation_quat, world_position = self.transform.world_model_matrix.decompose()

        collision_shape = p.createCollisionShape(
            p.GEOM_BOX, 
            halfExtents = self.transform.local_scale
        )

        self.physics_id = p.createMultiBody(
            baseMass                = self.mass, 
            baseCollisionShapeIndex = collision_shape, 
            basePosition            = world_position,
            baseOrientation         = [
                world_rotation_quat[0], 
                world_rotation_quat[1], 
                world_rotation_quat[2], 
                -world_rotation_quat[3] # handedness
            ] 
        )

    def _deInitPhysics( self) -> None:
        if self.physics_id is None or self.mass < 0.0:
            return

        p.removeBody( self.physics_id )
        self.physics_id = None

    def _runPhysics( self ) -> bool:
        """Run phyisics engine on this gameObject updating position and orientation"""
        if not self.settings.game_running or self.physics_id is None or self.mass < 0.0:
            return False

        world_position, world_rotation_quat = p.getBasePositionAndOrientation(self.physics_id)

        self.transform.world_model_matrix = self.compose_matrix(
            world_position,
            Quaternion([
                world_rotation_quat[0], 
                world_rotation_quat[1], 
                world_rotation_quat[2], 
                -world_rotation_quat[3] # ~handedness
            ]),
            self.transform.local_scale
        )

        if self.mass > 0.0:
            self.transform._update_local_from_world()

        return True

    def _updatePhysicsBody(self):
        """
        Physics engine requires are update call 
        whenever translation or rotation has changed externally (gui or script)
        """
        if self.physics_id is None or self.mass < 0.0:
            return
        
        pos = self.transform.extract_position(self.transform.world_model_matrix)
        rot = self.transform.extract_quat(self.transform.world_model_matrix)

        p.resetBasePositionAndOrientation( 
            self.physics_id, 
            pos, 
            #rot.xyzw
            [
                rot[0],
                rot[1], 
                rot[2], 
                -rot[3] # ~handedness
            ] 
        )

    #
    # start and update
    #
    def onStart( self ) -> None:
        """Implemented by inherited class"""
        self.transform._createWorldModelMatrix()

    def onUpdate( self ) -> None:
        """Implemented by inherited class"""
        if self._dirty:
            self.transform._local_rotation_quat = self.transform.euler_to_quat( self.transform.local_rotation )
            self.transform._createWorldModelMatrix()

            if self.settings.game_running:
                self._updatePhysicsBody()

            self._dirty = False

        else:
            # Run physics and update non-kinematic local transforms
            self._runPhysics()
            pass

