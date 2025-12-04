#from __future__ import annotations # used for "GameObject" forward reference in same scope

import os, sys, enum
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
from modules.script import Script

from gameObjects.scriptBehaivior import ScriptBehaivior

import inspect
import importlib
import traceback

import copy
import pybullet as p
import uuid as uid

class GameObject( Context, Transform ):
    """Base class for gameObjects """
    # IntFlag is bitwise  (1 << index)
    # IntEnum is seqential
    class DirtyFlag_(enum.IntFlag):
        none           = 0
        visible_state  = enum.auto() # (= 1 << 0) = 1
        active_state   = enum.auto() # (= 1 << 1) = 2
        transform      = enum.auto() # (= 1 << 2) = 4 
        all            = visible_state | active_state | transform

    def __init__( self, context, 
                 uuid           : uid.UUID = None,
                 name           : str = "GameObject",
                 model_file     : bool = False,
                 material       : int = -1,
                 translate      : list = [ 0.0, 0.0, 0.0 ], 
                 rotation       : list = [ 0.0, 0.0, 0.0 ], 
                 scale          : list = [ 1.0, 1.0, 1.0 ],
                 mass           : int = -1.0,
                 scripts        : list[Script] = []
                 ) -> None:
        """Base class for gameObjects 

        :param context: This is the main context of the application
        :type context: EmberEngine
        :param uuid: The uuid of the object, if None a new uuid is assigned
        :type uuid: str
        :param name: The name that is stored with the gameObject
        :type name: str
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
        self.scripts        : list[Script] = []
        self.material       : int = material
        
        self.parent         : GameObject = None
        self.children       : List[GameObject] = []

        self._active            : bool = True
        self._hierarchy_active  : bool = True

        self._visible           : bool = True
        self._hierarchy_visible : bool = True

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

        self._dirty         : GameObject.DirtyFlag_ = GameObject.DirtyFlag_.all
        self._removed       : bool = False

        self.onStart()

        # dynamic scripts
        for script in scripts:
            self.addScript( script )

    def __create_uuid( self ) -> uid.UUID:
        return uid.uuid4()

    def _mark_dirty(self, flag : DirtyFlag_ = DirtyFlag_.all ):
        """Mark this object and its children as dirty for the given state(s).

        When a GameObject is dirty, engine knows parts need updating.
        Which parts are determined by which flag(s) are set

        :param flag: The dirty flag(s) to set. Can be a single DirtyFlag_ or a combination.
                     Defaults to DirtyFlag_.all.
        :type flag: DirtyFlag_
        """
        if not self._dirty:
            self._dirty = flag

            for c in self.children:
                c._mark_dirty( flag )

    def get_component( self, component: str = "" ):
        """Retrieve a reference to a component of this GameObject.

        :param component: Name of the engine type (component) to retrieve.
        :type component: str
        :return: The requested component reference, or None if the name is not recognized.
        :rtype: Any or None
        """
        _ref = None

        match component:
            case "Transform"    : _ref = self.transform
            case "GameObject"   : _ref = self

        return _ref

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
        self._mark_dirty( GameObject.DirtyFlag_.active_state )

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
        self._mark_dirty( GameObject.DirtyFlag_.visible_state  )

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

        self._mark_dirty( GameObject.DirtyFlag_.all  )

    #
    # scripting
    #
    def onStartScripts(self):
        self.dispatch_script_base_method("onStart")

    def onUpdateScripts(self):
        self.dispatch_script_base_method("onUpdate")

    def onEnableScripts(self):
        self.dispatch_script_base_method("onEnable")

    def onDisableScripts(self):
        self.dispatch_script_base_method("onDisable")

    def addScript( self, script : Script ):
        """Attach a script to a gameObject

        :param script: Reference to the script
        :type script: Script
        """
        __func_name__ = inspect.currentframe().f_code.co_name

        if script.path.suffix != ".py":
            self.console.error( f"Extension: {script.path.suffix} is invalid!" )
            return

        script.init_instance( self )

        # append the script to the GameObject, even if it contains errors
        self.scripts.append( script )

    def removeScript( self, script : Script ):
        """Remove script from a gameObject

        :param script: Reference to the script
        :type script: Script
        """
        #self.scripts = [script for script in self.scripts if script["path"] != file]
        for x in self.scripts:
            if x.path == script.path:
                self.scripts.remove( script )
                return

    def dispatch_script_base_method( self, method_name : str ):
        """Dispatch and invoke a base method for each attached script
        
        Base methods are cached on the script instance.
            - onStart
            - onUpdate
            - onEnable
            - onDisable

        :param method_name: The name of method to invoke
        :type method_name: str
        """
        if not self.hierachyActive():
            return

        for script in filter( lambda x: x.instance is not None, self.scripts ):
            _base_method = script.base_methods.get( method_name )

            if _base_method:
                try:
                    _base_method()

                except Exception as e:
                    _, _, exc_tb = sys.exc_info()
                    self.console.error( e, traceback.format_tb( exc_tb ) )

    def _init_scripts( self ):
        """Call initilization function for each attached script"""
        if not self.hierachyActive():
            return

        for script in filter(lambda x: x.instance is not None, self.scripts):
            script.init_instance( self )

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
        #self.scripts                    = copy.deepcopy(state["scripts")

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
            self._init_scripts()
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
        # happens during Transform __init__ now?
        #self.transform._createWorldModelMatrix()

    def onUpdate( self ) -> None:
        """Implemented by inherited class"""
        if self._dirty & GameObject.DirtyFlag_.visible_state:
            self.__updateVisibleState()

        if self._dirty & GameObject.DirtyFlag_.active_state:
            self.__updateActiveState()

        if self.settings.game_running:
            self.onUpdateScripts();

        if self._dirty & GameObject.DirtyFlag_.transform:
            #if self.hierachyActive(): # not required
            self.transform._local_rotation_quat = self.transform.euler_to_quat( self.transform.local_rotation )
            self.transform._createWorldModelMatrix()

            if self.settings.game_running:
                self._updatePhysicsBody()

        if self._dirty:
            self._dirty = GameObject.DirtyFlag_.none

        else:
            # nothing to do
            if not self.hierachyActive():
                return 

            # Run physics and update non-kinematic local transforms
            self._runPhysics()

