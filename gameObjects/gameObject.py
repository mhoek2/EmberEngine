#from __future__ import annotations # used for "GameObject" forward reference in same scope

import os, sys, enum
from pathlib import Path
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

from typing import TYPE_CHECKING, TypedDict

from modules.context import Context

from modules.cubemap import Cubemap
from modules.material import Materials
from modules.images import Images
from modules.models import Models
from modules.transform import Transform
from modules.script import Script

from gameObjects.scriptBehaivior import ScriptBehaivior

from gameObjects.attachables.physic import Physic
from gameObjects.attachables.physicLink import PhysicLink

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
        :type translate: list
        :param rotation: The rotation of the object, using getter and setter
        :type rotation: list
        :param scale: The scale of the object
        :type scale: Vector3
        :param scripts: A list containing Paths to dynamic scripts
        :type scripts: list[scripts]
        """
        super().__init__( context )

        if uuid is None:
            uuid = self.__create_uuid()
        
        self.uuid           : uid.UUID = uuid
        self._uuid_gui      : int = int(str(self.uuid.int)[0:8])

        self.name           : str = name

        # list of references to attachables eg: Transform
        self.attachables      : dict = {}

        self.materials      : Materials = context.materials
        self.images         : Images = context.images
        self.cubemaps       : Cubemap = context.cubemaps
        self.models         : Models = context.models
        self.scripts        : list[Script] = []
        self.material       : int = material

        self.parent         : GameObject = None
        self.children       : list[GameObject] = []

        self._active            : bool = True
        self._hierarchy_active  : bool = True

        self._visible           : bool = True
        self._hierarchy_visible : bool = True

        self.transform = self.addAttachable( Transform, Transform(
            context     = self.context,
            gameObject  = self,
            translate   = translate,
            rotation    = rotation,
            scale       = scale,
            name        = name
        ) )

        self.physic : Physic = None  # reserved for physic attachment
        self.physic_link : PhysicLink = None  # reserved for physic attachment

        # model
        self.model          : int = -1
        self.model_file     = Path(model_file) if model_file else False

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

    def addAttachable( self, t : type, object ):
        """Add a attachable object to this gameObject
        
        :param t: The type of the attachable
        :type t: type
        :param object: The instance of the attachable
        :type object: Any or None
        :return: A reference to the added attachable
        :rtype: Any or None
        """
        if t in self.attachables:
            self.console.warn( f"{self.name} already has attachable: {t.__name__}")

        self.attachables[t] = object

        # special case for physics (for now)
        # use reserved self.physic_link attribute as reference, dont want to do per frame lookups.
        if t is PhysicLink:
            self.physic_link = self.attachables[t] 

        if t is Physic:
            self.physic = self.attachables[t] 

        return self.attachables[t] 

    def getAttachable( self, attachable: str = "" ):
        """Retrieve a reference to a attachable of this GameObject.

        :param attachable: Name of the engine type (attachable) to retrieve.
        :type attachable: str
        :return: The requested attachable reference, or None if the name is not recognized.
        :rtype: Any or None
        """
        _ref = None

        if isinstance(attachable, type):
            attachable = attachable.__name__

        match attachable:
            case "Transform"    : _ref = self.attachables.get( Transform )
            case "PhysicLink"   : _ref = self.attachables.get( PhysicLink )
            case "Physic"       : _ref = self.attachables.get( Physic )
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
        if not self.renderer.game_running:
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

    def getParent( self, filter_physic_base : bool = False ) -> "GameObject":
        if self.parent and filter_physic_base:
            if not self.parent.getAttachable( Physic ):
                return self.parent.getParent( filter_physic_base )
        
        return self.parent

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

        if script.path.suffix != self.settings.SCRIPT_EXTENSION:
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

        if self.physic:
            self._state_snapshot["Physic"] = {
                "translate" : list(self.physic.collision.transform.local_position),
                "rotation"  : list(self.physic.collision.transform.local_rotation),
                "scale"     : list(self.physic.collision.transform.local_scale),
            }

        if self.physic_link:
            self._state_snapshot["PhysicLink"] = {
                "translate" : list(self.physic_link.collision.transform.local_position),
                "rotation"  : list(self.physic_link.collision.transform.local_rotation),
                "scale"     : list(self.physic_link.collision.transform.local_scale),
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

        if "Physic" in state: 
            _physic = state["Physic"]
            self.physic.collision.transform.local_position   = _physic["translate"]
            self.physic.collision.transform.local_rotation   = _physic["rotation"]
            self.physic.collision.transform.local_scale      = _physic["scale"]

        if "PhysicLink" in state: 
            _physic_link = state["PhysicLink"]
            self.physic_link.collision.transform.local_position   = _physic_link["translate"]
            self.physic_link.collision.transform.local_rotation   = _physic_link["rotation"]
            self.physic_link.collision.transform.local_scale      = _physic_link["scale"]
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

        if self.physic:
            self.physic._initPhysics()

    def onDisable( self, _on_stop=False ) -> None:
        self.onDisableScripts();

        # only when runtime stops
        if _on_stop:
            self._restore_state()
            #deinit scripts?

        if self.physic:
            self.physic._deInitPhysics()

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

        if self.renderer.game_running:
            self.onUpdateScripts();

        if self._dirty & GameObject.DirtyFlag_.transform:
            #if self.hierachyActive(): # not required
            self.transform._local_rotation_quat = self.transform.euler_to_quat( self.transform.local_rotation )
            self.transform._createWorldModelMatrix()

            if self.renderer.game_running and self.physic:
                self.physic._updatePhysicsBody()

        if self._dirty:
            self._dirty = GameObject.DirtyFlag_.none

        else:
            # nothing to do
            if not self.hierachyActive():
                return 

            # Run physics and update non-kinematic local transforms
            if self.physic:
                self.physic._runPhysics()

            elif self.physic_link:
                self.physic_link._runPhysics()

    def onRender( self ) -> None:
        is_visible : bool = True if self.renderer.game_runtime else self.hierachyVisible()
        
        if not is_visible:
            return

        if self.context.settings.DEBUG_COLLIDER:
            # debug draw collision geometry
            #if not self.renderer.game_runtime and self.physic_link is not None:
            _physic = self.physic_link or self.physic

            # dont visualize
            if self.physic and self.children:
                _physic = None

            if _physic is not None:
                _current_shader = self.renderer.shader

                self.renderer.use_shader( self.renderer.color )

                _color = ( 0.83, 0.34, 0.0, 1.0 )
                glUniform4f( self.renderer.shader.uniforms['uColor'],  _color[0],  _color[1], _color[2], 0.7 )

                glEnable(GL_DEPTH_TEST)
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

                glLineWidth(5)
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

                _collision_model = _physic.collision.model or self.context.models.default_cube

                glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection )
                glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view )

                self.models.draw(
                    _collision_model,
                    _physic.collision.transform._getModelMatrix()
                )

                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                glLineWidth(1)

                if _current_shader:
                    self.renderer.use_shader( _current_shader )

                    glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection )
                    glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view )

        # render the model geometry
        if self.model != -1 and is_visible:
            self.models.draw( self.model, self.transform._getModelMatrix() ) 
