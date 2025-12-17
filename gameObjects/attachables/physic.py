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

class Physic( PhysicLink ):
    def __init__( self, context : "EmberEngine",
                    gameObject      : "GameObject",
                    uuid            : uid.UUID      = None,
                    active          : bool          = False,
                 ) -> None :
        super().__init__( context, gameObject )

        self.physics_id             : int = None
        self.physics_children_flat  : list[PhysicLink] = []

        self.base_mass : float = -1.0

        # 0 : base_footprint
        # 1 :     |_Base_link (0)
        # 2 :       |_ Link A (1)
        # 3 :           |_ Link B (2)
        self._link_to_index : dict = {}
        self._index_to_link : dict = {}


    def __create_uuid( self ) -> uid.UUID:
        return uid.uuid4()

    def find_physic_children( self, obj : "GameObject", _list ):
        for c in obj.children:
            _physic_link = c.getAttachable( PhysicLink )
            if _physic_link:
                _list.append( _physic_link )

            self.find_physic_children( c, _list )
            
    def construct_physic_child_list_flat( self ) -> list[PhysicLink]:
        """Create a flat list of this physic base children with PhysicLink attached"""
        self.physics_children_flat = []

        self.find_physic_children( self.gameObject, self.physics_children_flat )

    def _initPhysics( self ) -> None:
        """
        Initialize physics for this gameObject, sets position, orientation and mass
        https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstartguide.pdf
        """
        is_base_physic = bool(self.gameObject.children)

        if self.physics_id or (not is_base_physic and self.inertia.mass < 0.0):
            return

        # Create a list of all links connected this base_footprint recursivly
        self.construct_physic_child_list_flat()
 
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

        if is_base_physic:

            # build the link index mapping table
            for i, obj_link in enumerate( self.physics_children_flat ):
                # todo:
                # this can be merged with the next enumerator
                # because the hierarchy is flattened, and child always tails the parent..

                obj_link.runtime_link_index     = i         # matches this indexing
                self._link_to_index[obj_link]   = i + 1     # offset +1, because root is 0
                self._index_to_link[i]          = obj_link

            # bind child links and joints
            for i, obj_link in enumerate( self.physics_children_flat ):
                obj : GameObject = obj_link.gameObject

                # parent/link indexing
                _parent = obj.getParent()
                if _parent is self.gameObject:
                    parent_index = 0  # parent is base_footprint (self/this/PhysicBase)
                else:
                    parent_link : PhysicLink = _parent.getAttachable(PhysicLink)
                    parent_index = self._link_to_index[parent_link]

                linkParents.append(parent_index)

                # position & orientation
                #parent_inv      = self.gameObject.transform.world_model_matrix.inverse
                ##parent_inv     = parent.transform.world_model_matrix.inverse
                #local_matrix    = parent_inv * Matrix44(gameObject.transform.world_model_matrix)
                ##scale, rot_quat, pos = local_matrix.decompose()
                #pos             = gameObject.transform.extract_position(local_matrix)
                #rot_quat        = gameObject.transform.extract_quat(local_matrix)
                pos         = obj.transform.local_position
                rot_quat    = [
                    obj.transform._local_rotation_quat[0], 
                    obj.transform._local_rotation_quat[1], 
                    obj.transform._local_rotation_quat[2], 
                    -obj.transform._local_rotation_quat[3] # handedness
                ]

                linkPositions.append( tuple(pos) )
                linkOrientations.append( tuple(rot_quat) )

                # mass
                linkMasses.append( obj_link.inertia.mass )

                # type
                linkJointTypes.append( PhysicLink.pybullet_joint_type( obj_link.joint.geom_type ) )
                linkJointAxis.append([0,1,0])

                # collision shape
                collision_shape = PhysicLink.create_collision_shape( obj_link )
                linkCollisionShapes.append( collision_shape )

                # visual shape
                linkVisualShapes.append( -1 )

                # inertials
                linkInertialFramePositions.append( (0.0, 0.0, 0.0) )
                linkInertialFrameOrientations.append( (0.0, 0.0, 0.0, 1.0) )

                # debug
                print( f"{obj.name} links to {parent_index}: {_parent.name}" )

        # base physic properties
        _base_mass               = self.base_mass
        _base_collision_shape    = -1
        _base_position           = []
        _base_orientation        = []

        if is_base_physic:
            self.transform._createWorldModelMatrix()
            _, world_rotation_quat, world_position = self.transform.world_model_matrix.decompose()

        # no children, meaning its just a single world physic object
        else:
            self.collision.transform._createWorldModelMatrix()
            _, world_rotation_quat, world_position = self.collision.transform.world_model_matrix.decompose()

            _base_mass              = self.inertia.mass
            _base_collision_shape   = PhysicLink.create_collision_shape( self )


        _base_position      = world_position
        _base_orientation   = [
            world_rotation_quat[0], 
            world_rotation_quat[1], 
            world_rotation_quat[2], 
            -world_rotation_quat[3] # handedness
        ]

        self.physics_id = p.createMultiBody(
            # base
            baseMass                = _base_mass, 
            baseCollisionShapeIndex = _base_collision_shape, 

            basePosition            = _base_position,
            baseOrientation         = _base_orientation,

            # links
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
        self.__link_phyisic_children()

    def __link_phyisic_children( self ) -> None:
        """
        Link all physics child objects to this runtime physics instance.

        This assigns the current object as the runtime base physics reference
        for each child and propagates the physics ID to them. After this call,
        all physics children share the same physics context as this object.
        """
        for i, obj_link in enumerate( self.physics_children_flat ):
            obj_link.runtime_base_physic    = self
            obj_link.physics_id             = self.physics_id

    def __unlink_phyisic_children( self ) -> None:
        """
        Unlink all physics child objects from this runtime physics instance.

        This clears internal link/index mappings and removes the runtime physics
        reference and physics ID from each child. After this call, physics
        children are no longer associated with this physics context.
        """
        self._link_to_index.clear()
        self._index_to_link.clear()

        for i, obj_link in enumerate( self.physics_children_flat ):
            obj_link.runtime_base_physic    = None
            obj_link.physics_id             = None
        self.physics_children_flat.clear()

    def _deInitPhysics( self) -> None:
        if self.physics_id is None:
            return

        p.removeBody( self.physics_id )
        self.physics_id = None

        # cleanup links and joints
        self.__unlink_phyisic_children()

    def _runPhysics( self ) -> bool:
        """Run phyisics engine on this gameObject updating position and orientation"""
        if not self.renderer.game_running or self.physics_id is None:
            return False

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
                self.transform.local_scale
            )
        )

        self.transform.world_model_matrix = _model_matrix

        if self.base_mass > 0.0 or self.inertia.mass > 0.0:
            self.transform._update_local_from_world()

        # debug to visualize collisions in runtime:
        if self.context.settings.DEBUG_COLLIDER:
            _collision = self.gameObject.physic.collision
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
