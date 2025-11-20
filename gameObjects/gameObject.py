#from __future__ import annotations # used for "GameObject" forward reference in same scope

import os, sys
from pathlib import Path
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

from pyrr import Quaternion
from typing import TYPE_CHECKING, TypedDict, List

from modules.context import Context

from modules.cubemap import Cubemap
from modules.material import Materials
from modules.images import Images
from modules.models import Models
from modules.transform import Transform

import inspect
import importlib
import traceback

import copy
import pybullet as p
import uuid as uid

class GameObject( Context, Transform ):
    """Base class for gameObjects """
    def __init__( self, context, 
                 uuid           : uid.UUID = None,
                 name           : str = "GameObject",
                 visible        : bool = True,
                 model_file     : bool = False,
                 material       : int = -1,
                 translate      : list = [ 0.0, 0.0, 0.0 ], 
                 rotation       : list = [ 0.0, 0.0, 0.0 ], 
                 scale          : list = [ 1.0, 1.0, 1.0 ],
                 mass           : int = -1.0,
                 scripts        : list[Path] = []
                 ) -> None:
        """Base class for gameObjects 

        :param context: This is the main context of the application
        :type context: EmberEngine
        :param uuid: The uuid of the object, if None a new uuid is assigned
        :type uuid: str
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

        if uuid is None:
            uuid = self.__create_uuid()
        
        self.uuid           : uid.UUID = uuid
        self._uuid_gui      : int = int(str(self.uuid.int)[0:8])

        self.name           : str = name
        self.materials      : Materials = context.materials
        self.images         : Images = context.images
        self.cubemaps       : Cubemap = context.cubemaps
        self.models         : Models = context.models
        self.scripts        : list[GameObject.Script] = []
        self.material       : int = material
        
        self.parent         : GameObject = None
        self.children       : List[GameObject] = []

        self._active            : bool = False
        self._hierarchy_active  : bool = False

        self._visible           : bool = visible
        self._hierarchy_visible : bool = False

        self.transform      : Transform = Transform(
            context     = self.context,
            gameObject  = self,
            translate   = translate,
            rotation    = rotation,
            scale       = scale,
            name        = name
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
        for path in scripts:
            self.addScript( path )

    def __create_uuid( self ) -> uid.UUID:
        return uid.uuid4()

    def _mark_dirty(self):
        if not self._dirty:
            self._dirty = True

            for c in self.children:
                c._mark_dirty()

    #
    # active state
    #
    def selfActive( self ) -> bool:
        """Get the current active sate of only the GameObject"""
        return self._active

    def hierachyActive( self ) -> bool:
        """Get the current hierarchical active state of the GameObject
        :return: True if GameObject AND its ancestors are active
        :rtype: bool
        """
        return self._hierarchy_active

    def __isHierarchyActive( self, gameObject : "GameObject" = None ) -> bool:
        """Check for ancestor active state recursivly

        :param gameObject: The current GameObject if None use self
        :type gameObject: GameObject
        :return: True if all of its ancestors are active, False if not
        :rtype: bool
        """
        gameObject = gameObject or self

        if gameObject.parent is None:
            return True

        # check parent then recursivly the ancestors
        return gameObject.parent.active and self.__isHierarchyActive( gameObject.parent )

    def __updateActiveState( self ) -> None:
        """
        Update hierarchical active state when GameObject is _dirty
        Calls onEnable() or onDisable() on state change in runtime
        """
        _latest_state = True if (self._active and self.__isHierarchyActive()) else False

        # no state change, stop
        if self._hierarchy_active == _latest_state:
            return

        self._hierarchy_active = _latest_state

        # runtime logic
        if not self.settings.game_running:
            return

        if self._hierarchy_active:
            self.onEnable()

        else:
            self.onDisable()

    @property
    def active( self ):
        """
        @property:  The active state of this gameObject (not including parents)
        @setter:    Changes state and marks itself and children _dirty
        """
        return self._active

    @active.setter
    def active( self, state : bool = True ):
        if self._active == state:
           return

        self._active = state
        self._mark_dirty()

    def setActive( self, state : bool ) -> None:
        """Sets active state for this GameObject, then marks itself and children dirty

        :param state: The new state
        :type state: bool
        """
        self.active = state

    #
    # visibility state
    #
    def selfVisible( self ) -> bool:
        """Get the current visible sate of only the GameObject"""
        return self.visible

    def hierachyVisible( self ) -> bool:
        """Get the current hierarchical active state of the GameObject
        :return: True if GameObject AND its ancestors are active
        :rtype: bool
        """
        return self._hierarchy_visible

    def __isHierarchyVisible( self, gameObject : "GameObject" = None ):
        """Check for ancestor visible state recursivly (editor-only)

        :param gameObject: The current GameObject if None use self
        :type gameObject: GameObject
        :return: True if all of its ancestors are visible, False if not
        :rtype: bool
        """
        gameObject = gameObject or self

        if gameObject.parent is None:
            return True

        # check parent then recursivly the ancestors
        return gameObject.parent.visible and self.__isHierarchyVisible( gameObject.parent )

    def __updateVisibleState( self ) -> None:
        """
        Update hierarchical active state when GameObject is _dirty
        Calls onEnable() or onDisable() on state change in runtime
        """
        _latest_state = True if (self.visible and self.__isHierarchyVisible()) else False

        # no state change, stop
        if self._hierarchy_visible != _latest_state:
            self._hierarchy_visible = _latest_state

    @property
    def visible( self ):
        """
        @property:  The active state of this gameObject (not including parents)
        @setter:    Changes state and marks itself and children _dirty
        """
        return self._visible

    @visible.setter
    def visible( self, state : bool = True ):
        if self._visible == state:
           return

        self._visible = state
        self._mark_dirty()

    def setVisible( self, state : bool ) -> None:
        """Sets visible state for this GameObject, then marks itself and children dirty

        :param state: The new state
        :type state: bool
        """
        self.visible = state

    #
    # parenting
    #
    def setParent( self, parent : "GameObject", update:bool=True ) -> None:
        """Set relation between child and parent object
        
        :param parent: The new parent of this object
        :type parent: GameObject
        :param update: Whether to update transform local from new parents world world coordinates
        :type update: bool
        """

        # remove from current parent
        if self.parent is not None:
            self.parent.children.remove(self)

        # add to new parent
        if parent is not None:
            parent.children.append(self)

        self.parent = parent

        # update local transform in relation to new parent
        if update:
            self.transform._update_local_from_world()

        self._mark_dirty()

    #
    # scripting
    #
    class Script(TypedDict):
        path            : Path
        class_name      : str
        class_name_f    : str
        obj             : None

    def addScript( self, path : Path ):
        """Add script to a gameObject

        :param path: The path to a .py script file
        :type path: Path
        """
        if path.suffix != ".py":
            self.console.log( self.console.Type_.note, [], f"Extension: {path.suffix} is invalid!" )
            return

        relative_path = path.relative_to(self.settings.rootdir)

        self.console.log( self.console.Type_.note, [], f"Load script: {relative_path}" )

        self.scripts.append({ 
            "path": relative_path, 
            "obj": "" 
         })

        # set class name
        self.__set_class_name( self.scripts[-1] )

    def removeScript( self, path : Path ):
        """Remove script from a gameObject

        :param path: The path to a .py script file
        :type path: Path
        """
        #self.scripts = [script for script in self.scripts if script["path"] != file]
        for script in self.scripts:
            if script["path"] == path:
                self.scripts.remove(script)
                break

    def __get_class_name_from_script( self, path: Path ) -> str:
        """Scan the content of the script to find the first class name.

        :param path: The path to a .py script file
        :type path: Path
        :return: A class name if its found, return None otherwise
        :rtype: str | None
        """
        filepath = (self.settings.rootdir / path).resolve()

        if os.path.isfile(filepath):
            code = filepath.read_text()

        for line in code.splitlines():
            if line.strip().startswith("class "):
                class_name = line.strip().split()[1].split('(')[0]

                if class_name.endswith(":"):
                    return class_name[:-1]

                return class_name

        return None

    def __format_class_name( self, name : str ) -> str:
        """Format the classname
        
        :return: Formatted string with space after any uppercased letter
        :rtype: str | None
        """
        formatted : str = ""

        for char in name:
            if char.isupper():
                formatted += f" {char}"
            else:
                formatted += char

        return formatted

    def __set_class_name( self, script : Script ):
        """Gets the class name for a given scripts, also formats it for GUI
        
        :param script: The Script object containing a file path
        :type script: GameObject.Script
        """
        script["class_name"] = self.__get_class_name_from_script(script["path"])
        script["class_name_f"] = self.__format_class_name( script["class_name"] )

    def init_external_script( self, script : Script ):
        """Initialize script attached to this gameObject,
        Try to load and parse the script, then convert to module in sys.

        :param script: The Script object containing a file path
        :type script: GameObject.Script
        """
        __func_name__ = inspect.currentframe().f_code.co_name

        script["obj"] = False

        # Get full file path
        file_path = script["path"]

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
        
        # auto import modules
        for auto_mod_name, auto_mod_as in self.settings.SCRIPT_AUTO_IMPORT_MODULES.items():
            imported = importlib.import_module(auto_mod_name)

            if auto_mod_as is not None:
                module.__dict__[auto_mod_as] = imported
            else:
                module.__dict__[auto_mod_name] = imported

        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Load ScriptBehaivior
        _script_behavior = importlib.import_module("gameObjects.scriptBehaivior")
        ScriptBehaivior = getattr(_script_behavior, "ScriptBehaivior")

        # set class name
        self.__set_class_name( script )
        _class_name = script["class_name"]

        if not hasattr(module, _class_name):
            self.console.log( self.console.Type_.note, [], 
                f"[{__func_name__}] No class named '{_class_name}' found in {file_path}")
            return

        ScriptClass = getattr(module, _class_name)

        class ClassPlaceholder(ScriptClass, ScriptBehaivior):
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
        if not self.hierachyActive():
            return

        for script in self.scripts:
            try:
                script["obj"].onStart()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.log( self.console.Type_.error, traceback.format_tb(exc_tb), e )

    def onUpdateScripts( self ):
        """Call onUpdate() function in all dynamic scripts attached to this gameObject"""
        if not self.hierachyActive():
            return

        for script in filter(lambda x: x["obj"] is not False, self.scripts):
            try:
                script["obj"].onUpdate()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.log( self.console.Type_.error, traceback.format_tb(exc_tb), e )

    def onEnableScripts( self ):
        """Call onEnable() function in all dynamic scripts attached to this gameObject"""
        if not self.hierachyActive():
            return

        for script in filter(lambda x: x["obj"] is not False, self.scripts):
            try:
                script["obj"].onEnable()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.log( self.console.Type_.error, traceback.format_tb(exc_tb), e )

    def onDisableScripts( self ):
        """Call onDisable() function in all dynamic scripts attached to this gameObject"""
        for script in filter(lambda x: x["obj"] is not False, self.scripts):
            try:
                script["obj"].onDisable()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.log( self.console.Type_.error, traceback.format_tb(exc_tb), e )

    def initScripts( self ):
        for script in filter(lambda x: x["obj"] is not False, self.scripts):
            try:
                self.init_external_script( script )

                script["obj"].onEnable()
            except Exception as e:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.log( self.console.Type_.error, traceback.format_tb(exc_tb), e )

    #
    # editor state
    #
    def _save_state(self):
        """Save a snapshot of the full GameObject state."""

        self._state_snapshot = {
            "translate" : list(self.transform.local_position),
            "rotation"  : list(self.transform.local_rotation),
            "scale"     : list(self.transform.local_scale),
            "active"    : self.active,
            "visible"   : self.visible,
            "material"  : self.material,
            "children"  : self.children,
            "parent"  : self.parent,
            #"scripts"   : copy.deepcopy(self.scripts),
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
        self.active                     = state["active"]
        self.visible                    = state["visible"]
        self.material                   = state["material"]
        self.children                   = state["children"]
        self.parent                     = state["parent"]
        #self.scripts                    = copy.deepcopy(state["scripts"])

    #
    # physics
    #
    def _initPhysics( self ) -> None:
        """
        Initialize physics for this gameObject, sets position, orientation and mass
        https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstartguide.pdf
        """
        self.transform._createWorldModelMatrix()

        if self.physics_id or self.mass < 0.0:
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
    # enable and disable
    #
    def onEnable( self, _on_start=False ) -> None:
        # only when runtime starts
        if _on_start:
            self._save_state()
            self.initScripts()
            self.__updateActiveState()

        # skip runtime, object is disabled
        if not self.hierachyActive():
            return

        self.onEnableScripts();

        # only when runtime starts
        if _on_start:
            self.onStartScripts();

        self._initPhysics()

    def onDisable( self, _on_stop=False ) -> None:
        self.onDisableScripts();

        # only when runtime stops
        if _on_stop:
            self._restore_state()
            #deinit scripts?

        self._deInitPhysics()

    #
    # start and update
    #
    def onStart( self ) -> None:
        """Implemented by inherited class"""
        self.transform._createWorldModelMatrix()

    def onUpdate( self ) -> None:
        """Implemented by inherited class"""
        if self._dirty:
            # want a dirty flag for this? DirtyFlag_.visible_state
            self.__updateVisibleState()

            # want a dirty flag for this? DirtyFlag_.active_state
            self.__updateActiveState()

        if self.settings.game_running:
            self.onUpdateScripts();

        if self._dirty:
            # want a dirty flag for this? DirtyFlag_.transform
            if self.hierachyActive():
                self.transform._local_rotation_quat = self.transform.euler_to_quat( self.transform.local_rotation )
                self.transform._createWorldModelMatrix()

                if self.settings.game_running:
                    self._updatePhysicsBody()

            self._dirty = False

        else:
            # nothing to do
            if not self.hierachyActive():
                return 

            # Run physics and update non-kinematic local transforms
            self._runPhysics()

