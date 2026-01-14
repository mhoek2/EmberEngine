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
                 name           : str = "",
                 local_callback = None
                 ) -> None :
        self.settings = context.settings
        self.gameObject = gameObject

        if local_callback is None:
            local_callback = partial(gameObject._mark_dirty, gameObject.DirtyFlag_.transform)

        # physic stuff
        self.is_physic_shape = False

        # coordination
        # row-major, post-multiply, intrinsic rotation
        # R = Rx * Ry * Rz
        # tbh, so much has changed, I lost track ..
        self._local_position        = self.vectorInterface( translate,  local_callback, name )
        self._local_rotation        = self.vectorInterface( rotation,   local_callback, name )
        self._local_scale           = self.vectorInterface( scale,      local_callback, name )
        self._local_rotation_quat   : Quaternion = Quaternion(self.euler_to_quat(self._local_rotation))
        self.world_model_matrix     : Matrix44 = self._createWorldModelMatrix()

        # Proxy/passthrough: unlike local transforms, world transforms are not stored;
        # they are always computed from the current model matrix.
        #
        # Each vectorInterface instance acts as a *live proxy*:
        #   - data is updated on every access.
        #   - Element-wise writes (e.g. position[1] = 10) trigger the setter.
        #   - Whole-value writes (e.g. position = [0,0,0]) also trigger the setter.
        #   - This allows transparent editing from scripts and the editor GUI.
        self._world_position_proxy  = self.vectorInterface( self.extract_position(),    None, name, setter=self.set_position )
        self._world_rotation_proxy  = self.vectorInterface( self.extract_euler(),       None, name, setter=self.set_rotation )
        self._world_scale_proxy     = self.vectorInterface( self.extract_scale(),       None, name, setter=self.set_scale )

    @staticmethod
    def vec_to_degrees( v ):
        return [math.degrees(x) for x in v]

    @staticmethod
    def vec_to_radians( v ):
        return [math.radians(x) for x in v]

    class vectorInterface( list ):
        def __init__( self, data, callback, name : str = "test", setter=None ):
            super().__init__( data )
            self._callback = callback
            self._name = name

            # world only (proxy)
            self._setter = setter

        def _trigger( self ):
            if self._callback:
                self._callback()

            # world only (proxy)
            if self._setter:
                self._setter( list(self) )

        def __setitem__( self, key, value ):
            """
            !important
            only update physics when value changed (gui or script)
            this is detected by the data type specifier,
            physics engine : tuple
            gui or scripts : list, int, float
            """
            update_physics : bool = isinstance( value, (list, int, float) );

            if isinstance( key, slice ):
                if not isinstance( value, type(self) ):
                    value = type(self)( value, self._callback )
                    #if self._name == "testcube" and self._callback:
                    #    print("(phys)")

            super().__setitem__(key, value)

            if update_physics:
                self._trigger()
                #if self._name == "testcube" and self._callback:
                #    print("(gui-script)")

        def __iadd__( self, other ):
            result = super().__iadd__(other)
            self._trigger()
            return result

        def __isub__( self, other ):
            result = super().__isub__(other)
            self._trigger()
            return result

        def __ne__( self, other ):
            return list(self) != list(other)

        def __eq__( self, other ):
            return list(self) == list(other)

        def __mul__(self, other):
            if isinstance(other, (int, float)):
                return list([v * other for v in self])

            elif isinstance(other, (list, tuple, Transform.vectorInterface)):
                return list([a * b for a, b in zip(self, other)])

            return NotImplemented

    #
    # LOCAL (master)
    #
    # local position
    @property
    def local_position(self):
        return self._local_position
    
    @local_position.setter
    def local_position(self, data):
        self._local_position.__setitem__(slice(None), data)

    def set_local_position( self, data : list ):
        """Lambda wrapper"""
        self.local_position = list( data )

    # local rotation (euler)
    @property
    def local_rotation(self):
        return self._local_rotation
    
    @local_rotation.setter
    def local_rotation(self, data):
        self._local_rotation.__setitem__(slice(None), data)

    def set_local_rotation( self, data : list ):
        """Lambda wrapper"""
        self.local_rotation = list( data )

    # local scale
    @property
    def local_scale(self):
        return self._local_scale
    
    @local_scale.setter
    def local_scale(self, data):
        self._local_scale.__setitem__(slice(None), data)

    def set_local_scale( self, data : list ):
        """Lambda wrapper"""
        self.local_scale = list( data )

    #
    # WORLD (slave)
    # 
    # world position
    @property
    def position( self ):
        """
        Get current position in world space

            world transforms are not stored, it is always computed from the latest model matrix
            A persistent proxy Transform.VectorInterface instance:

            - dats is updated on every access
            - writes are forwarded to set_position() - as list
            - allows writes from scripts and editor gui

        """
        self._world_position_proxy.__setitem__(slice(None), tuple(self.extract_position()))
        return self._world_position_proxy

    @position.setter
    def position( self, data ):
        T = Matrix44.from_translation( data )

        if self.gameObject.parent is not None:
            # local = inverse(parent_world) * world
            parent_inv = self._getParentModelMatrix().inverse
            local_matrix = parent_inv * T

            self.local_position = list(self.extract_position(local_matrix))
        else:
            # no parent > world = local
            self.local_position = list(Vector3(data))

    def set_position( self, data : list ) -> None:
        """Lambda/Proxy wrapper"""
        self.position = list( data )

    # world rotation
    @property
    def rotation( self ):
        """
        Get current rotation in world space

            world transforms are not stored, it is always computed from the latest model matrix
            A persistent proxy Transform.VectorInterface instance:

            - dats is updated on every access
            - writes are forwarded to set_rotation() - as list
            - allows writes from scripts and editor gui

        """
        self._world_rotation_proxy.__setitem__(slice(None), tuple(self.extract_euler()))
        return self._world_rotation_proxy

    @rotation.setter
    def rotation( self, data ):
        world_quat = self.euler_to_quat( data )

        quat : Quaternion = Quaternion()

        if self.gameObject.parent is not None:
            parent_world_quat = self.extract_quat(self._getParentModelMatrix())
            quat = parent_world_quat.inverse * world_quat
        else:
            # no parent > world = local
            quat = world_quat

        self.local_rotation = list(self.quat_to_euler(quat))
    
    def set_rotation( self, data : list ) -> None:
        """Lambda/Proxy wrapper"""
        self.rotation = list( data )

    # world scale
    @property
    def scale( self ):
        """
        Get current scale in world space

            world transforms are not stored, it is always computed from the latest model matrix
            A persistent proxy Transform.VectorInterface instance:

            - dats is updated on every access
            - writes are forwarded to set_scale() - as list
            - allows writes from scripts and editor gui

        """      
        self._world_scale_proxy.__setitem__(slice(None), tuple(self.extract_scale()))
        return self._world_scale_proxy

    @scale.setter
    def scale( self, data ):
        data = Vector3(data)

        if self.gameObject.parent is not None:
            parent_scale = self.extract_scale(self._getParentModelMatrix())

            # local scale = world / parent
            self.local_scale = list([
                data.x / parent_scale.x if parent_scale.x != 0 else 0,
                data.y / parent_scale.y if parent_scale.y != 0 else 0,
                data.z / parent_scale.z if parent_scale.z != 0 else 0,
            ])
        else:
            # no parent > local = world
            self.local_scale = list(data)

    def set_scale( self, data : list ) -> None:
        """Lambda/Proxy wrapper"""
        self.scale = list( data )

    def _update_local_from_world( self, ignore_scale : bool = False ):
        """Recompute local transform from world transform and parent safely."""
    
        world_matrix = Matrix44(self.world_model_matrix)

        if self.gameObject.parent is not None:
            parent_inv = self._getParentModelMatrix().inverse
            local_matrix = parent_inv * world_matrix
        else:
            local_matrix = world_matrix

        scale, rot_quat, pos = local_matrix.decompose()
    
        self.local_position = tuple(pos)
        if not ignore_scale:
            self.local_scale = tuple(scale)

        # Use quaternions for rotation to avoid flipping
        self._local_rotation_quat = Quaternion(rot_quat)
        self.local_rotation = tuple(self.quat_to_euler(self._local_rotation_quat))

    def compose_matrix( self, position, quat, scale) -> Matrix44:
        T = Matrix44.from_translation(position)
        R = Matrix44.from_quaternion(quat)
        S = Matrix44.from_scale(scale)
        return T * R * S #  (row-major)

    def _getModelMatrix( self ) -> Matrix44:
        return self.world_model_matrix

    def _getParentModelMatrix( self ) -> Matrix44:
        # A physic shape (collision/visual) is relative/local to the gameObject transform
        # Thefor, return gameObject.transform and not the parent 
        if self.is_physic_shape:
            return self.gameObject.transform.world_model_matrix

        # Otherwise, inherit the parent game object's transform
        elif self.gameObject.parent is not None:
            return self.gameObject.parent.transform.world_model_matrix

        return Matrix44.identity()

    def _createWorldModelMatrix( self, local_matrix : Matrix44 = None, includeParent : bool = True ) -> Matrix44:
        """Create model matrix with translation, rotation and scale vectors"""
        if local_matrix is not None:
            _local_model_matrix = local_matrix
        else:
            _local_model_matrix = self.compose_matrix(
                self._local_position,
                self._local_rotation_quat,
                self._local_scale
            )

        # here or _getParentModelMatrix()?
        #if self.is_physic_shape:
        #    self.world_model_matrix = self.gameObject.transform._getModelMatrix() * local_model_matrix
        #else:
        if self.gameObject.parent is not None or self.is_physic_shape:
            self.world_model_matrix = Matrix44(self._getParentModelMatrix() * _local_model_matrix)
        else:
            self.world_model_matrix = Matrix44(_local_model_matrix)

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
        sx = max(np.linalg.norm(R[0]), 1e-8)
        sy = max(np.linalg.norm(R[1]), 1e-8)
        sz = max(np.linalg.norm(R[2]), 1e-8)
        R[0] /= sx
        R[1] /= sy
        R[2] /= sz

        # Re-orthogonalize (Gram-Schmidt)
        R[0] = R[0] / np.linalg.norm(R[0])

        n = np.linalg.norm(R[1])
        if n < 1e-8:
            R[1] = np.array([0, 1, 0], dtype=float)
        else:
            R[1] /= n

        R[2] = np.cross(R[0], R[1])
        if np.linalg.norm(R[2]) < 1e-8:
            R[2] = np.array([0, 0, 1], dtype=float)

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

        #x = Vector3(mat.column(0)[:3]).length
        #y = Vector3(mat.column(1)[:3]).length
        #z = Vector3(mat.column(2)[:3]).length

        return Vector3([x, y, z])