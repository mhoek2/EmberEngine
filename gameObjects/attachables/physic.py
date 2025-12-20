import os, sys, enum

from pyrr import Quaternion, Matrix44

from modules.settings import Settings
from modules.engineTypes import EngineTypes
from gameObjects.attachables.physicLink import PhysicLink

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject
    from modules.transform import Transform

import inspect
import traceback
import uuid as uid

import pybullet as p

from dataclasses import dataclass, field

Vec3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]

@dataclass(slots=True)
class MultiBodyLinks:
    base: "Physic | None" = None

    # map
    # 0 : base_footprint
    # 1 :     |_Base_link (0)
    # 2 :       |_ Link A (1)
    # 3 :           |_ Link B (2)
    link_to_index : dict = field( default_factory=dict )
    # flat list of nested children
    index_to_link : list[PhysicLink] = field( default_factory=list )

    masses                     : list[float] = field( default_factory=list )
    parents                    : list[int]   = field( default_factory=list )
    positions                  : list[Vec3]  = field( default_factory=list )
    orientations               : list[Quat]  = field( default_factory=list )
    jointTypes                 : list[int]   = field( default_factory=list )
    jointAxis                  : list[Vec3]  = field( default_factory=list )
    collisionShapes            : list[int]   = field( default_factory=list )
    visualShapes               : list[int]   = field( default_factory=list )
    inertialFramePositions     : list[Vec3]  = field( default_factory=list )
    inertialFrameOrientations  : list[Quat]  = field( default_factory=list )

    def destroy( self ) -> None:
        """
        Unlink all physics child objects from this runtime physics instance.

        This clears internal link/index mappings and removes the runtime physics
        references
        """
        for i, link in enumerate( self.index_to_link ):
            link.runtime_link_index     = None
            link.runtime_base_physic    = None
            link.physics_id             = None

        # reset/clear all lists
        for name in self.__slots__:
            value = getattr(self, name)
            if isinstance(value, list) or isinstance(value, dict):
                value.clear()

        print("sd")

    def find_physic_children( self, obj : "GameObject", _list : list[PhysicLink] ):
        """Build a flat list of valid nested pybullet child gameObjects"""
        for c in obj.children:
            link = c.getAttachable( PhysicLink )
            if link and c.hierachyActive():
                _list.append( link )

            self.find_physic_children( c, _list )

    def cache_on_children( self ) -> None:
        """
        Cache references on the child objects at runtime.
        
            Cache adds references to:
            - Child link mapping index
            - Base Physic (self.base)
            - Base Physic physics_id (multibody index from pybullet)

        This allows for easy and fast lookups
        """
        for i, link in enumerate( self.index_to_link ):
            link.runtime_link_index     = self.link_to_index[link]
            link.runtime_base_physic    = self.base
            link.physics_id             = self.base.physics_id

    def add_link(
        self,
        link            : PhysicLink = None,
        mass            : float = -1.0,
        parent          : int = 0,
        position        : Vec3 = (0.0, 0.0, 0.0),
        orientation     : Quat = (0.0, 0.0, 0.0, 1.0),
        joint_type      : int = 0,
        joint_axis      : Vec3 = (0.0, 0.0, 1.0),
        collision_shape : int = -1,
        visual_shape    : int = -1,
        inertial_pos    : Vec3 = (0.0, 0.0, 0.0),
        inertial_ori    : Quat = (0.0, 0.0, 0.0, 1.0),
    ) -> int:
        """Add a link and return its index."""

        index = len(self.masses)

        # properties
        self.masses.append(mass)
        self.parents.append(parent)
        self.positions.append(position)
        self.orientations.append(orientation)
        self.jointTypes.append(joint_type)
        self.jointAxis.append(joint_axis)
        self.collisionShapes.append(collision_shape)
        self.visualShapes.append(visual_shape)
        self.inertialFramePositions.append(inertial_pos)
        self.inertialFrameOrientations.append(inertial_ori)

        return index

    def runtime_init( self ):
        # first build a flat list of nested children with: PhysicList
        self.index_to_link.clear()
        self.find_physic_children( self.base.gameObject, self.index_to_link )

        # extract physic properties from each nested child and convert to a pybullet link
        for i, link in enumerate( self.index_to_link ):
            gameObject : GameObject = link.gameObject

            # parent/link indexing
            _parent = gameObject.getParent()
            if _parent is self.base.gameObject:
                parent_index = 0  # parent is base_footprint (self/this/PhysicBase)
            else:
                parent_link : PhysicLink = _parent.getAttachable(PhysicLink)
                parent_index = self.link_to_index[parent_link] + 1 # + 1 cus of pybullet hierarchy (base = 0)

            # position & orientation
            #parent_inv      = self.gameObject.transform.world_model_matrix.inverse
            ##parent_inv     = parent.transform.world_model_matrix.inverse
            #local_matrix    = parent_inv * Matrix44(gameObject.transform.world_model_matrix)
            ##scale, rot_quat, pos = local_matrix.decompose()
            #pos             = gameObject.transform.extract_position(local_matrix)
            #rot_quat        = gameObject.transform.extract_quat(local_matrix)

            # joint/link origin
            pos         = gameObject.transform.local_position
            rot_quat    = [
                gameObject.transform._local_rotation_quat[0], 
                gameObject.transform._local_rotation_quat[1], 
                gameObject.transform._local_rotation_quat[2], 
                -gameObject.transform._local_rotation_quat[3] # handedness
            ]

            self.link_to_index[link] = self.add_link(
                link = link,

                mass            = link.inertia.mass,
                parent          = parent_index,
                position        = pos,
                orientation     = Quat(rot_quat),
                joint_type      = PhysicLink.pybullet_joint_type( link.joint.geom_type ),
                joint_axis      = (0, 1, 0),
                collision_shape = PhysicLink.create_collision_shape( link ),
                visual_shape    = -1,
                inertial_pos    = (0.0, 0.0, 0.0),
                inertial_ori    = (0.0, 0.0, 0.0, 1.0)
            )

            # debug
            #print( f"{gameObject.name} links to {parent_index}: {_parent.name}" )

class Physic( PhysicLink ):
    def __init__( self, context : "EmberEngine",
                    gameObject      : "GameObject",
                    uuid            : uid.UUID      = None,
                    active          : bool          = False,
                 ) -> None :
        super().__init__( context, gameObject )

        self.physics_id             : int = None
        

        self.base_mass  : float = -1.0

        # linked children
        self.links      : MultiBodyLinks = MultiBodyLinks( base=self )

    def __create_uuid( self ) -> uid.UUID:
        return uid.uuid4()

    def _initPhysics( self ) -> None:
        """
        Initialize physics for this gameObject, sets position, orientation and mass
        https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstartguide.pdf
        """
        is_base_physic = bool(self.gameObject.children)

        if self.physics_id or (not is_base_physic and self.inertia.mass < 0.0):
            return

        # base physic properties
        _base_mass               = self.base_mass
        _base_collision_shape    = -1
        _base_position           = []
        _base_orientation        = []

        # base physic (Physic + nested children) 
        if is_base_physic:
            # construct the link list from nested children
            self.links.runtime_init()

            self.gameObject.transform._createWorldModelMatrix()
            _, world_rotation_quat, world_position = self.gameObject.transform.world_model_matrix.decompose()

        # no children, meaning its just a single world physic object
        else:
            self.gameObject.transform._createWorldModelMatrix()
            _, world_rotation_quat, world_position = self.gameObject.transform.world_model_matrix.decompose()

            _base_mass              = self.inertia.mass
            _base_collision_shape   = PhysicLink.create_collision_shape( self )

        _base_position      = world_position
        _base_orientation   = [
            world_rotation_quat[0], 
            world_rotation_quat[1], 
            world_rotation_quat[2], 
            -world_rotation_quat[3] # handedness
        ]

        # -------------------------------------------------------------------------------
        # createMultiBody                    Type                        Description
        # -------------------------------------------------------------------------------
        # baseMass                           float                       Mass of the base (kg, SI units)
        # baseCollisionShapeIndex            int                         Collision shape ID or -1
        # baseVisualShapeIndex               int                         Visual shape ID or -1
        # basePosition                       vec3 / [float, float, float] Base world position
        # baseOrientation                    vec4 / [x, y, z, w]         Base orientation (quaternion)
        # baseInertialFramePosition          vec3                        Local inertial frame position
        # baseInertialFrameOrientation       vec4                        Local inertial frame orientation
        #
        # linkMasses                         list[float]                 Mass of each link
        # linkCollisionShapeIndices          list[int]                   Collision shape IDs per link
        # linkVisualShapeIndices             list[int]                   Visual shape IDs per link
        # linkPositions                      list[vec3]                  Link positions relative to parent
        # linkOrientations                   list[vec4]                  Link orientations relative to parent
        # linkInertialFramePositions         list[vec3]                  Inertial frame positions per link
        # linkInertialFrameOrientations      list[vec4]                  Inertial frame orientations per link
        # linkParentIndices                  list[int]                   Parent link index (0 = base)
        # linkJointTypes                     list[int]                   JOINT_REVOLUTE / PRISMATIC / FIXED
        # linkJointAxis                      list[vec3]                  Joint axis in local frame
        #
        # useMaximalCoordinates              int                         Experimental (default: 0)
        # physicsClientId                    int                         Physics server ID
        # -------------------------------------------------------------------------------
        self.physics_id = p.createMultiBody(
            # base
            baseMass                = _base_mass, 
            baseCollisionShapeIndex = _base_collision_shape, 
            basePosition            = _base_position,
            baseOrientation         = _base_orientation,

            # links
            linkMasses                    = self.links.masses,
            linkCollisionShapeIndices     = self.links.collisionShapes,
            linkVisualShapeIndices        = self.links.visualShapes,
            linkPositions                 = self.links.positions,
            linkOrientations              = self.links.orientations,
            linkInertialFramePositions    = self.links.inertialFramePositions,
            linkInertialFrameOrientations = self.links.inertialFrameOrientations,
            linkParentIndices             = self.links.parents,
            linkJointTypes                = self.links.jointTypes,
            linkJointAxis                 = self.links.jointAxis,
        )

        # cache references to physic_id, base and index of the link on the child GameObject
        self.links.cache_on_children()


    def _deInitPhysics( self) -> None:
        if self.physics_id is None:
            return

        p.removeBody( self.physics_id )
        self.physics_id = None

        # cleanup links and joints
        self.links.destroy()

    def _runPhysics( self ) -> bool:
        """Run phyisics engine on this gameObject updating position and orientation"""
        if not self.renderer.game_running or self.physics_id is None:
            return False

        is_base_physic = bool(self.gameObject.children)

        world_position, world_rotation_quat = p.getBasePositionAndOrientation(self.physics_id)
        # getLinkState

        # Update world transform (ignore scale for physics)
        _model_matrix = (
            self.gameObject.transform.compose_matrix(
                world_position,
                Quaternion([
                    world_rotation_quat[0], 
                    world_rotation_quat[1], 
                    world_rotation_quat[2], 
                    -world_rotation_quat[3] # ~handedness
                ]),
                self.gameObject.transform.local_scale
            )
        )

        # Recompute local transform when base physic (Physic + nested children) 
        if is_base_physic:
            self.gameObject.transform.world_model_matrix = _model_matrix
            self.gameObject.transform._update_local_from_world()

        # or is a single world physic object with mass
        elif self.inertia.mass > 0.0:
            #self.gameObject.transform.world_model_matrix = _model_matrix * self.collision.transform.local_model_matrix.inverse
            self.gameObject.transform.world_model_matrix = _model_matrix
            self.gameObject.transform._update_local_from_world()

            # debug to visualize collisions in runtime:
            if self.context.settings.drawColliders:
                _collision = self.collision
                local_matrix = _collision.transform.compose_matrix(
                    _collision.transform.local_position,
                    _collision.transform._local_rotation_quat,
                    _collision.transform.local_scale
                )
                _collision.transform.world_model_matrix = _model_matrix * local_matrix

        return True

    def _updatePhysicsBody(self):
        """
        Physics engine requires are update call 
        whenever translation or rotation has changed externally (gui or script)
        """
        if self.physics_id is None:
            return
        
        pos = self.gameObject.transform.extract_position(self.gameObject.transform.world_model_matrix)
        rot = self.gameObject.transform.extract_quat(self.gameObject.transform.world_model_matrix)

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
