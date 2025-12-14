from stat import FILE_ATTRIBUTE_NOT_CONTENT_INDEXED
import os, sys, enum

from pyrr import Quaternion

from modules.settings import Settings
from modules.engineTypes import EngineTypes

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject
    from modules.transform import Transform
    from gameObjects.attachables.physic import Physic

import inspect
import traceback
import uuid as uid

import pybullet as p

class PhysicLink:
    class Inertia:
        def __init__( self, context : "EmberEngine" ):
            self.context = context

            self.active : bool = False
            self.mass   : float = -1.0
            pass

    class Joint:
        class Type_(enum.IntEnum):
            fixed       = 0              # (= 0)
            revolute    = enum.auto()    # (= 1)
            continuous  = enum.auto()    # (= 2)
            prismatic   = enum.auto()    # (= 3)
            planar      = enum.auto()    # (= 4)
            floating    = enum.auto()    # (= 5)

        def __init__( self, context : "EmberEngine" ):
            self.context = context

            self.active : bool = False
            self.name   : str = "-"
            self.type   : PhysicLink.Joint.Type_ = PhysicLink.Joint.Type_.fixed
            self.parent : "GameObject" = None

        def getParent( self ) -> "GameObject":
            return self.parent

        def setParent( self, uuid : uid.UUID ):
            self.parent = self.context.findGameObject( uuid )

    def __init__( self, context : "EmberEngine",
                    gameObject      : "GameObject",
                    uuid            : uid.UUID      = None,
                    active          : bool          = False,
                 ) -> None :
        self.context    = context
        self.settings   = context.settings
        self.renderer   = context.renderer

        self.gameObject = gameObject
        self.transform  = self.gameObject.transform

        if uuid is None:
            uuid = self.__create_uuid()

        self.uuid           : uid.UUID = uuid
        self.active         : bool     = active

        self.inertia        : PhysicLink.Inertia = PhysicLink.Inertia( context )
        self.joint          : PhysicLink.Joint = PhysicLink.Joint( context )

        self.runtime_link_index = 0
        self.runtime_base_physic : "Physic" = None
        self.physics_id = 0     # this is the physics id of the base link

    def __create_uuid( self ) -> uid.UUID:
        return uid.uuid4()


    def _runPhysics(self) -> bool:
        if not self.context.renderer.game_running:
            return False

        if not self.runtime_base_physic or self.runtime_base_physic.physics_id is None:
            return False


        num_joints = p.getNumJoints( self.runtime_base_physic.physics_id )
        print(f"joints: {num_joints} -- {self.gameObject.name} index: {self.runtime_link_index}")
        # inkWorldPosition (COM)	    state[0]
        # linkWorldOrientation (COM)	state[1]
        # localInertialFramePosition	state[2]
        # localInertialFrameOrientation	state[3]
        # worldLinkFramePosition	    state[4]
        # worldLinkFrameOrientation	    state[5]
        state = p.getLinkState(
            self.runtime_base_physic.physics_id,
            self.runtime_link_index,
            computeForwardKinematics=True
        )

        if not state:
            return False

        world_pos = state[4]
        world_orn = state[5]

        # Update world transform (ignore scale for physics)
        self.gameObject.transform.world_model_matrix = (
            self.gameObject.transform.compose_matrix(
                world_pos,
                Quaternion([
                    world_orn[0],
                    world_orn[1],
                    world_orn[2],
                    -world_orn[3]
                ]),
                self.gameObject.transform.local_scale
            )
        )

        # Recompute local transform if parented
        self.gameObject.transform._update_local_from_world()

        return True

