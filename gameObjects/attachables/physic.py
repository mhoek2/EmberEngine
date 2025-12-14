import os, sys, enum

from pyrr import Quaternion

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

class Physic:
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

        self.physics_id     : int = None
        self.physics_base   : bool = False
        self.physics_links  : list["PhysicLink"] = []

        self.root_link : PhysicLink = PhysicLink( self.context, self.gameObject )
        self.root_link.joint.setParent( self.uuid  )
        self.physics_links.append( self.root_link )

        self.base_mass : float = -1.0

    def __create_uuid( self ) -> uid.UUID:
        return uid.uuid4()

    def compute_physics_local_transform( self, child_tf : "Transform", parent_tf : "Transform" ):
        # Extract WORLD transforms (no scale)
        Pc = child_tf.extract_position()
        Qc = child_tf.extract_quat()

        Pp = parent_tf.extract_position()
        Qp = parent_tf.extract_quat()

        # Quaternion inverse
        invQp = Qp.inverse

        # Local position (parent space)
        delta = Pc - Pp
        local_pos = invQp * delta  # quaternion-vector rotate

        # Local orientation (parent space)
        local_rot = invQp * Qc

        return tuple(local_pos), tuple(local_rot)

    def pybullet_joint_type( self, joint_type : PhysicLink.Joint.Type_ = 0 ):
        if joint_type == PhysicLink.Joint.Type_.fixed:
            return p.JOINT_FIXED

        if joint_type in (
            PhysicLink.Joint.Type_.revolute,
            PhysicLink.Joint.Type_.continuous,
        ):
            return p.JOINT_REVOLUTE

        if joint_type == PhysicLink.Joint.Type_.prismatic:
            return p.JOINT_PRISMATIC

        if joint_type in (
            PhysicLink.Joint.Type_.planar,
            PhysicLink.Joint.Type_.floating,
        ):
            raise NotImplementedError(
                "PyBullet does not support planar or floating joints in createMultiBody"
            )

        raise ValueError(f"Unknown joint type {joint_type}")

    def _initPhysics( self ) -> None:
        """
        Initialize physics for this gameObject, sets position, orientation and mass
        https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstartguide.pdf
        """
        self.transform._createWorldModelMatrix()

        if self.physics_id or self.base_mass < 0.0:
            return

        _, world_rotation_quat, world_position = self.transform.world_model_matrix.decompose()

        collision_shape = p.createCollisionShape(
            p.GEOM_BOX, 
            halfExtents = self.transform.local_scale
        )

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

        # hacky stuff :D
        #Base/root (0)
        # |_ Link A (1)
        #     |_ Link B (2)

        self._physics_link_index = {}
        i = 0

        for link in self.physics_links:
            if link is self.root_link:
                continue

            link.runtime_link_index = i
            self._physics_link_index[link] = i + 1
            i += 1

        linkMasses = []
        linkParents = []
        linkPositions = []
        linkOrientations = []
        linkJointTypes = []
        linkJointAxis = []
        linkCollisionShapes = []
        linkVisualShapes = []
        linkInertialFramePositions = []
        linkInertialFrameOrientations = [] 

        for link in self.physics_links:
            if link is self.root_link:
                continue

            gameObject = link.gameObject

            # parent/link indexing
            parent = link.joint.getParent()

            # connect to base, when no parent
            if not parent:
                parent = self.gameObject

            if parent is self.gameObject:
                parent_index = 0  # parent is base (self/this)
            else:
                parent_link : PhysicLink = parent.getAttachable(PhysicLink)
                parent_index = self._physics_link_index[parent_link]
                #parent_index = parent_link.runtime_link_index
            linkParents.append(parent_index)

            # position & orientation
            local_pos, local_rot = self.compute_physics_local_transform(
                gameObject.transform,
                parent.transform
            )

            linkPositions.append(local_pos)
            linkOrientations.append(local_rot)

            # mass
            linkMasses.append(link.inertia.mass)

            # type
            linkJointTypes.append( self.pybullet_joint_type(link.joint.type) )
            linkJointAxis.append([0,1,0])  # example

            # collision shape
            linkCollisionShapes.append(-1)

            # visuals shape
            linkVisualShapes.append(-1)

            # inertials
            linkInertialFramePositions.append( 0 )
            linkInertialFrameOrientations.append( 0 )

            # debug
            print( f"{gameObject.name} links to {parent_index}: {parent.name}" )

        self.physics_id = p.createMultiBody(
            baseMass                = self.base_mass, 
            baseCollisionShapeIndex = collision_shape, 
            basePosition            = world_position,
            baseOrientation         = [
                world_rotation_quat[0], 
                world_rotation_quat[1], 
                world_rotation_quat[2], 
                -world_rotation_quat[3] # handedness
            ],

            linkMasses                      = linkMasses,
            linkCollisionShapeIndices       = linkCollisionShapes,
            linkVisualShapeIndices          = linkVisualShapes,
            linkPositions                   = linkPositions,
            linkOrientations                = linkOrientations,
            linkInertialFramePositions      = linkInertialFramePositions,
            linkInertialFrameOrientations   = linkInertialFrameOrientations,
            linkParentIndices               = linkParents,
            linkJointTypes                  = linkJointTypes,
            linkJointAxis                   = linkJointAxis
        )

        # update the physics id on links to reference this multibody
        for link in self.physics_links:
            link.runtime_base_physic = self
            link.physics_id = self.physics_id


    def _deInitPhysics( self) -> None:
        if self.physics_id is None or self.base_mass < 0.0:
            return

        p.removeBody( self.physics_id )
        self.physics_id = None

    def _runPhysics( self ) -> bool:
        """Run phyisics engine on this gameObject updating position and orientation"""
        if not self.renderer.game_running or self.physics_id is None or self.base_mass < 0.0:
            return False

        world_position, world_rotation_quat = p.getBasePositionAndOrientation(self.physics_id)
        # getLinkState

        self.transform.world_model_matrix = self.transform.compose_matrix(
            world_position,
            Quaternion([
                world_rotation_quat[0], 
                world_rotation_quat[1], 
                world_rotation_quat[2], 
                -world_rotation_quat[3] # ~handedness
            ]),
            self.transform.local_scale
        )

        if self.base_mass > 0.0:
            self.transform._update_local_from_world()

        return True

    def _updatePhysicsBody(self):
        """
        Physics engine requires are update call 
        whenever translation or rotation has changed externally (gui or script)
        """
        if self.physics_id is None or self.base_mass < 0.0:
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
