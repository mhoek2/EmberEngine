from pyrr import Matrix44, Vector3, Quaternion
import numpy as np
import math

from modules.settings import Settings

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject

from functools import partial

class Transform:
    def __init__( self, context : "EmberEngine", 
                 gameObject     : "GameObject",
                 translate      = [ 0.0, 0.0, 0.0 ], 
                 rotation       = [ 0.0, 0.0, 0.0 ], 
                 scale          = [ 1.0, 1.0, 1.0 ],
                 name           : str = ""
                 ) -> None :
        self.settings = context.settings
        self.gameObject = gameObject

        # coordination
        # row-major, post-multiply, intrinsic rotation
        # R = Rx * Ry * Rz
        # tbh, so much has changed, I lost track ..
        self._local_position        = self.vectorInterface( translate, partial(gameObject._mark_dirty, gameObject.DirtyFlag_.transform), name )
        self._local_rotation        = self.vectorInterface( rotation, partial(gameObject._mark_dirty, gameObject.DirtyFlag_.transform), name )
        self._local_scale           = self.vectorInterface( scale, partial(gameObject._mark_dirty, gameObject.DirtyFlag_.transform), name )
        self._local_rotation_quat   : Quaternion = Quaternion(self.euler_to_quat(self._local_rotation))
        self.world_model_matrix     : Matrix44 = self._createWorldModelMatrix()

    @staticmethod
    def vec_to_degrees( v ):
        return [math.degrees(x) for x in v]

    @staticmethod
    def vec_to_radians( v ):
        return [math.radians(x) for x in v]

    class vectorInterface(list):
        def __init__(self, data, callback, name : str = "test"):
            super().__init__(data)
            self._callback = callback
            self._name = name

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
                    #if self._name == "testcube" and self._callback:
                    #    print("(phys)")

            super().__setitem__(key, value)

            if update_physics:
                self._trigger()
                #if self._name == "testcube" and self._callback:
                #    print("(gui-script)")

        def __iadd__(self, other):
            result = super().__iadd__(other)
            self._trigger()
            return result

        def __isub__(self, other):
            result = super().__isub__(other)
            self._trigger()
            return result

        def __ne__(self, other):
            return list(self) != list(other)

        def __eq__(self, other):
            return list(self) == list(other)

    # position
    @property
    def local_position(self):
        return self._local_position
    
    @local_position.setter
    def local_position(self, data):
        self._local_position.__setitem__(slice(None), data)

    # rotation (euler)
    @property
    def local_rotation(self):
        return self._local_rotation
    
    @local_rotation.setter
    def local_rotation(self, data):
        self._local_rotation.__setitem__(slice(None), data)

    def set_local_rotation( self, data ):
        """Lambda wrapper"""
        self.local_rotation = data

    #scale
    @property
    def local_scale(self):
        return self._local_scale
    
    @local_scale.setter
    def local_scale(self, data):
        self._local_scale.__setitem__(slice(None), data)

    def _update_local_from_world(self):
        """Recompute local transform from world transform and parent safely."""
    
        world_matrix = Matrix44(self.world_model_matrix)

        if self.gameObject.parent is not None:
            parent_inv = self._getParentModelMatrix().inverse
            local_matrix = parent_inv * world_matrix
        else:
            local_matrix = world_matrix

        scale, rot_quat, pos = local_matrix.decompose()
    
        self.local_position = tuple(pos)
        self.local_scale = tuple(scale)

        # Use quaternions for rotation to avoid flipping
        self._local_rotation_quat = Quaternion(rot_quat)
        self.local_rotation = tuple(self.quat_to_euler(self._local_rotation_quat))

    def updatePositionFromWorld( self, world_position ) -> None:
        T = Matrix44.from_translation(world_position)

        if self.gameObject.parent is not None:
            # local = inverse(parent_world) * world
            parent_inv = self._getParentModelMatrix().inverse
            local_matrix = parent_inv * T

            self.local_position = list(self.extract_position(local_matrix))
        else:
            # no parent > world = local
            self.local_position = list(Vector3(world_position))

    def updateRotationFromWorld(self, world_rotation_euler) -> None:
        world_quat = self.euler_to_quat( world_rotation_euler )

        quat : Quaternion = Quaternion([0,0,0,0])

        if self.gameObject.parent is not None:
            parent_world_quat = self.extract_quat(self._getParentModelMatrix())
            quat = parent_world_quat.inverse * world_quat
        else:
            # no parent > world = local
            quat = world_quat

        self.local_rotation = list(self.quat_to_euler(quat))

    def updateScaleFromWorld( self, world_scale ) -> None:
        world_scale = Vector3(world_scale)

        if self.gameObject.parent is not None:
            parent_scale = self.extract_scale(self._getParentModelMatrix())

            # local scale = world / parent
            self.local_scale = list([
                world_scale.x / parent_scale.x if parent_scale.x != 0 else 0,
                world_scale.y / parent_scale.y if parent_scale.y != 0 else 0,
                world_scale.z / parent_scale.z if parent_scale.z != 0 else 0,
            ])
        else:
            # no parent > local = world
            self.local_scale = list(world_scale)

    def compose_matrix( self, position, quat, scale) -> Matrix44:
        T = Matrix44.from_translation(position)
        R = Matrix44.from_quaternion(quat)
        S = Matrix44.from_scale(scale)
        return T * R * S #  (row-major)

    def _getModelMatrix( self ) -> Matrix44:
        return self.world_model_matrix

    def _getParentModelMatrix( self ) -> Matrix44:
        if self.gameObject.parent is not None:
            return self.gameObject.parent.transform.world_model_matrix
        else:
            return Matrix44.identity()

    def _createWorldModelMatrix( self, includeParent : bool = True ) -> Matrix44:
        """Create model matrix with translation, rotation and scale vectors"""
        local_matrix = self.compose_matrix(
            self._local_position,
            self._local_rotation_quat,
            self._local_scale
        )

        if self.gameObject.parent is not None:
            self.world_model_matrix = Matrix44(self._getParentModelMatrix() * local_matrix)
        else:
            self.world_model_matrix = Matrix44(local_matrix)

        return self.world_model_matrix

    def euler_to_quat( self, euler, order=None) -> Quaternion:
        x, y, z = euler
        qx = Quaternion.from_x_rotation(x)
        qy = Quaternion.from_y_rotation(y)
        qz = Quaternion.from_z_rotation(z)

        if order is None:
            order = self.settings.ENGINE_ROTATION

        order = self.settings.ENGINE_ROTATION_MAP[order]
        order_map = {
            "XYZ": qx * qy * qz,
            "XZY": qx * qz * qy,
            "YXZ": qy * qx * qz,
            "YZX": qy * qz * qx,
            "ZXY": qz * qx * qy,
            "ZYX": qz * qy * qx,
        }
        return Quaternion(order_map[order])

    def safe_asin( self, x):
        return math.asin(max(-1.0, min(1.0, x)))

    def quat_to_euler(self, q: Quaternion, order=None) -> Vector3:
        """
        Convert quaternion to Euler angles using current ENGINE_ROTATION
        """
        if order is None:
            order = self.settings.ENGINE_ROTATION

        # Convert quaternion to rotation matrix
        M = Matrix44.from_quaternion(q)
        R = np.array([
            [M[0][0], M[0][1], M[0][2]],
            [M[1][0], M[1][1], M[1][2]],
            [M[2][0], M[2][1], M[2][2]],
        ], dtype=float)

        # Handle each Euler rotation order
        if order == "XYZ":
            y = math.asin(-R[2,0])
            cy = math.cos(y)
            if abs(cy) < 1e-6:  # gimbal lock
                x = 0
                z = math.atan2(-R[0,1], R[1,1])
            else:
                x = math.atan2(R[2,1], R[2,2])
                z = math.atan2(R[1,0], R[0,0])
            return Vector3([x, y, z])

        elif order == "XZY":
            z = self.safe_asin(-R[1,0])
            cz = math.cos(z)
            if abs(cz) < 1e-6:
                x = 0
                y = math.atan2(-R[2,1], R[1,1])
            else:
                x = math.atan2(-R[1,2], R[1,1])
                y = math.atan2(-R[2,0], R[0,0])
            return Vector3([x, y, z])

        elif order == "YXZ":
            x = self.safe_asin(R[2,1])
            cx = math.cos(x)
            if abs(cx) < 1e-6:
                z = 0
                y = math.atan2(-R[0,2], R[0,0])
            else:
                z = math.atan2(-R[0,1], R[1,1])
                y = math.atan2(-R[2,0], R[2,2])
            return Vector3([x, y, z])

        elif order == "YZX":
            z = math.asin(-R[1,2])
            cz = math.cos(z)
            if abs(cz) < 1e-6:
                y = 0
                x = math.atan2(R[0,1], R[0,0])
            else:
                y = math.atan2(R[2,2], R[0,2])
                x = math.atan2(R[1,0], R[1,1])
            return Vector3([x, y, z])

        elif order == "ZXY":
            x = math.asin(-R[1,2])
            cx = math.cos(x)
            if abs(cx) < 1e-6:
                z = 0
                y = math.atan2(R[0,1], R[0,0])
            else:
                z = math.atan2(R[1,0], R[1,1])
                y = math.atan2(R[2,2], R[0,2])
            return Vector3([x, y, z])

        elif order == "ZYX":
            y = math.asin(-R[0,2])
            cy = math.cos(y)
            if abs(cy) < 1e-6:
                z = 0
                x = math.atan2(R[1,0], R[1,1])
            else:
                z = math.atan2(R[0,1], R[0,0])
                x = math.atan2(R[1,2], R[2,2])
            return Vector3([x, y, z])

        else:
            raise NotImplementedError(f"Euler order {order} not implemented")

    def extract_position(self, mat: Matrix44 = None) -> Vector3:
        if mat is None:
            mat = self.world_model_matrix

        row4 = list(mat[3])
        return Vector3(row4[:3])  # first three components

    def extract_quat(self, mat: Matrix44 = None):
        if mat is None:
            mat = self.world_model_matrix

        # Extract pure rotation matrix R = M with translation removed
        R = np.array([list(mat[i])[:3] for i in range(3)], dtype=float)

        # Remove scale
        sx = np.linalg.norm(R[0])
        sy = np.linalg.norm(R[1])
        sz = np.linalg.norm(R[2])
        R[0] /= sx
        R[1] /= sy
        R[2] /= sz

        # Re-orthogonalize (Gram-Schmidt)
        R[0] = R[0] / np.linalg.norm(R[0])
        R[1] = R[1] - np.dot(R[1], R[0]) * R[0]
        R[1] /= np.linalg.norm(R[1])
        R[2] = np.cross(R[0], R[1])

        return Quaternion.from_matrix(R)

    def extract_euler(self, mat: Matrix44 = None) -> Vector3:
        if mat is None:
            mat = self.world_model_matrix

        quat = self.extract_quat(mat)
        return self.quat_to_euler(quat)

    def extract_scale(self, mat: Matrix44 = None) -> Vector3:
        if mat is None:
            mat = self.world_model_matrix

        x = Vector3(list(mat[0])[:3]).length
        y = Vector3(list(mat[1])[:3]).length
        z = Vector3(list(mat[2])[:3]).length
        return Vector3([x, y, z])