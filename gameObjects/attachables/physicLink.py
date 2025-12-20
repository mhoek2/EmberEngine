from stat import FILE_ATTRIBUTE_NOT_CONTENT_INDEXED
import os, sys, enum

from pyrr import Quaternion

from modules.settings import Settings
from modules.engineTypes import EngineTypes
from modules.transform import Transform

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject
    
    from gameObjects.attachables.physic import Physic

import inspect
import traceback
import uuid as uid

import pybullet as p

class PhysicLink:
    class GeometryType_(enum.IntEnum):
        sphere      = 0              # (= 0)
        box         = enum.auto()    # (= 1)
        mesh        = enum.auto()    # (= 2)
        cilinder    = enum.auto()    # (= 3)

    @staticmethod
    def pybullet_geom_type( _t : int = 0 ) :
        if _t == PhysicLink.GeometryType_.sphere:
            return p.GEOM_SPHERE

        if _t == PhysicLink.GeometryType_.box:
            return p.GEOM_BOX

        if _t == PhysicLink.GeometryType_.mesh:
            return p.GEOM_MESH

        if _t == PhysicLink.GeometryType_.cilinder:
            return p.GEOM_CYLINDER

        #p.GEOM_PLANE
        #p.GEOM_CAPSULE
        #p.GEOM_HEIGHTFIELD
        raise NotImplementedError(
            "Not yet supported"
        )

    @staticmethod
    def create_collision_shape( link : "PhysicLink" ):

        world_scale = (
            link.gameObject.transform.local_scale *
            link.collision.transform.local_scale
        )

        geom_type = PhysicLink.pybullet_geom_type(link.collision.geom_type)

        # p.createCollisionShape(...)
        # shapeType (int) REQUIRED:
        #   p.GEOM_SPHERE | BOX | CAPSULE | CYLINDER | PLANE | MESH | HEIGHTFIELD
        #
        # radius (float, default=0.5)        : SPHERE, CAPSULE, CYLINDER
        # halfExtents (vec3, default=[1,1,1]): BOX (half-size per axis)
        # height (float, default=1.0)        : CAPSULE, CYLINDER
        #
        # fileName (str)                     : MESH (.obj, convex hull per 'o')
        # meshScale (vec3, default=[1,1,1])  : MESH
        # flags (int)                        : MESH (p.GEOM_FORCE_CONCAVE_TRIMESH -> static only)
        #
        # planeNormal (vec3, default=[0,0,1]): PLANE
        #
        # collisionFramePosition (vec3)      : local offset of shape
        # collisionFrameOrientation (quat)   : local rotation (x,y,z,w)
        #
        # HEIGHTFIELD only:
        #   vertices (list[vec3]), indices (list[int])
        #   numHeightfieldRows (int), numHeightfieldColumns (int)
        #   heightfieldTextureScaling (float)
        #   replaceHeightfieldIndex (int)
        #
        # physicsClientId (int)              : multi-client support

        pos         = link.collision.transform.local_position
        rot_quat    = [
            link.collision.transform._local_rotation_quat[0], 
            link.collision.transform._local_rotation_quat[1], 
            link.collision.transform._local_rotation_quat[2], 
            -link.collision.transform._local_rotation_quat[3] # handedness
        ]

        if geom_type == p.GEOM_BOX:
            return p.createCollisionShape(
                geom_type,
                halfExtents=[
                    world_scale[0],
                    world_scale[1],
                    world_scale[2],
                ],
                collisionFramePosition      = pos,
                collisionFrameOrientation   = rot_quat,
            )

        elif geom_type == p.GEOM_SPHERE:
            # assume uniform scale, take X
            return p.createCollisionShape(
                geom_type,
                radius=world_scale[0],
                collisionFramePosition      = pos,
                collisionFrameOrientation   = rot_quat,
            )

        elif geom_type == p.GEOM_CYLINDER:
            # Bullet cylinder axis = Z
            return p.createCollisionShape(
                geom_type,
                radius=world_scale[0] * 0.5,
                height=world_scale[2],
                collisionFramePosition      = pos,
                collisionFrameOrientation   = rot_quat,
            )

        elif geom_type == p.GEOM_MESH:
            return p.createCollisionShape(
                geom_type,
                fileName=link.collision.mesh_path,
                meshScale=list(world_scale),
                collisionFramePosition      = pos,
                collisionFrameOrientation   = rot_quat,
            )

        else:
            raise NotImplementedError("Unsupported geometry type")

    @staticmethod
    def pybullet_joint_type( _t : int = 0 ):
        if _t == PhysicLink.Joint.Type_.fixed:
            return p.JOINT_FIXED

        if _t in (
            PhysicLink.Joint.Type_.revolute,
            PhysicLink.Joint.Type_.continuous,
        ):
            return p.JOINT_REVOLUTE

        if _t == PhysicLink.Joint.Type_.prismatic:
            return p.JOINT_PRISMATIC

        if _t in (
            PhysicLink.Joint.Type_.planar,
            PhysicLink.Joint.Type_.floating,
        ):
            raise NotImplementedError(
                "PyBullet does not support planar or floating joints in createMultiBody"
            )

        raise ValueError(f"Unknown joint type {_t}")

    class Inertia:
        def __init__( self, context : "EmberEngine" ):
            self.context = context

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

        def __init__( self, context         : "EmberEngine",
                            gameObject      : "GameObject"):
            self.context    = context
            self.gameObject = gameObject

            # joint transform uses the self.gameObject.transform

            self.geom_type   : PhysicLink.Joint.Type_ = PhysicLink.Joint.Type_.fixed

    class Visual:
        def __init__( self, context         : "EmberEngine", 
                            gameObject      : "GameObject"
                    ) -> None:
            self.context    = context
            self.gameObject = gameObject

            self.transform : Transform = Transform(
                context         = self.context,
                gameObject      = gameObject,
                translate       = ( 0.0, 0.0, 0.0 ),
                rotation        = ( 0.0, 0.0, 0.0 ),
                scale           = ( 1.0, 1.0, 1.0 ),
                name            = f"{gameObject.name}_physic_visual",
                local_callback  = lambda : self.transform._createWorldModelMatrix()
            )
            self.transform.is_physic_shape = True
            self.transform._createWorldModelMatrix()

    class Collision:
        def __init__( self, context         : "EmberEngine", 
                            gameObject      : "GameObject"
                    ) -> None:
            self.context    = context
            self.gameObject = gameObject

            self.transform : Transform = Transform(
                context         = self.context,
                gameObject      = gameObject,
                translate       = ( 0.0, 0.0, 0.0 ),
                rotation        = ( 0.0, 0.0, 0.0 ),
                scale           = ( 1.0, 1.0, 1.0 ),
                name            = f"{gameObject.name}_physic_collision",
                local_callback  = lambda : self.transform._createWorldModelMatrix()
            )
            self.transform.is_physic_shape = True
            self.transform._createWorldModelMatrix()

            self._type   : PhysicLink.GeometryType_ = PhysicLink.GeometryType_.box
            self.model = None

        @property
        def geom_type( self ):
            return self._type

        @geom_type.setter
        def geom_type( self, data ) -> None:
            self._type = data

            match self._type:
                case PhysicLink.GeometryType_.sphere:
                    self.model = self.context.models.default_sphere
                case PhysicLink.GeometryType_.box:
                    self.model = self.context.models.default_cube
                case PhysicLink.GeometryType_.mesh:
                    self.model = self.gameObject.model

    def __init__( self, context         : "EmberEngine",
                        gameObject      : "GameObject",
                        uuid            : uid.UUID      = None,
                        active          : bool          = False,
                 ) -> None :
        self.context    = context
        self.settings   = context.settings
        self.renderer   = context.renderer

        self.gameObject = gameObject

        if uuid is None:
            uuid = self.__create_uuid()

        self.uuid           : uid.UUID = uuid
        self.active         : bool     = active

        self.inertia        : PhysicLink.Inertia    = PhysicLink.Inertia( context )
        self.joint          : PhysicLink.Joint      = PhysicLink.Joint( context, self.gameObject )
        self.collision      : PhysicLink.Collision  = PhysicLink.Collision( context, self.gameObject )
        self.visual         : PhysicLink.Visual     = PhysicLink.Visual( context, self.gameObject )

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

        # linkWorldPosition (COM)	    state[0]
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

        world_position = state[4]
        world_rotation_quat = state[5]

        # Update world transform (ignore scale for physics)
        _model_matrix = (
            self.gameObject.transform.compose_matrix(
                world_position,
                Quaternion([
                    world_rotation_quat[0],
                    world_rotation_quat[1],
                    world_rotation_quat[2],
                    -world_rotation_quat[3]
                ]),
                self.gameObject.transform.local_scale
            )
        )

        # Always recompute local transform when parented (PhysicLink)
        self.gameObject.transform.world_model_matrix = _model_matrix
        self.gameObject.transform._update_local_from_world()

        # debug to visualize collisions in runtime:
        if self.context.settings.drawColliders:
            _collision = self.gameObject.physic_link.collision
            local_matrix = _collision.transform.compose_matrix(
                _collision.transform.local_position,
                _collision.transform._local_rotation_quat,
                _collision.transform.local_scale
            )
            _collision.transform.world_model_matrix = _model_matrix * local_matrix
            #self.gameObject.physic_link.collision.transform._update_local_from_world()

        return True

