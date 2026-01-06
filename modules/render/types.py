from pyrr import matrix44, Matrix44, Vector3
import uuid as uid

from dataclasses import dataclass, field
import numpy as np

@dataclass(slots=True)
class DrawItem:
    model_index : int       = field( default_factory=int )
    mesh_index  : int       = field( default_factory=int )
    matrix      : Matrix44  = field( default_factory=Matrix44 )
    uuid        : uid.UUID  = field( default_factory=uid.UUID )

@dataclass(slots=True)
class MatrixItem:
    mesh_index  : int           = field( default_factory=int )
    matrix      : np.ndarray    = field( default_factory=lambda: np.zeros((4, 4), dtype=np.float32))
    min_aabb    : np.ndarray    = field( default_factory=lambda: np.zeros(3, dtype=np.float32))
    max_aabb    : np.ndarray    = field( default_factory=lambda: np.zeros(3, dtype=np.float32)) 