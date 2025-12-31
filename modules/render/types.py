from pyrr import matrix44, Matrix44, Vector3
import uuid as uid

from dataclasses import dataclass, field

@dataclass(slots=True)
class DrawItem:
    model_index : int       = field( default_factory=int )
    mesh_index  : int       = field( default_factory=int )
    matrix      : Matrix44  = field( default_factory=Matrix44 )
    uuid        : uid.UUID  = field( default_factory=uid.UUID )

@dataclass(slots=True)
class MatrixItem:
    mesh_index  : int       = field( default_factory=int )
    matrix      : Matrix44  = field( default_factory=Matrix44 )