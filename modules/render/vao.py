from typing import TYPE_CHECKING

from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

import numpy as np

if TYPE_CHECKING:
    from main import EmberEngine

class VAO:
    @staticmethod
    def vertex_stride():
        """
        Use a 56 byte stride

            Reference:
            combined = np.hstack((
                v,          # 3 : 12 bytes
                n,          # 3 : 12 bytes
                t,          # 2 : 8 bytes
                tangents,   # 3 : 12 bytes
                bitangents  # 3 : 12 bytes
            )).astype(np.float32, copy=False)

        """
        return 14 * 4  # 56 bytes

    @staticmethod
    def bytes_in_vertices( num_vertices : int ):
        return num_vertices * VAO.vertex_stride()

    @staticmethod
    def bytes_in_indices( num_indices : int ):
        return num_indices * 4

    @staticmethod
    def vertices_in_bytes( b : int ):
        return b // VAO.vertex_stride()

    @staticmethod
    def indices_in_bytes( b : int ):
        return b // 4

    def __init__( self, vertex_bytes : int, index_bytes : int ):
        stride = self.vertex_stride()

        self.max_vertices = VAO.vertices_in_bytes( vertex_bytes )
        self.max_indices  = VAO.indices_in_bytes( index_bytes )

        self.vertex_count = 0
        self.index_count  = 0

        self.vao = glGenVertexArrays( 1 )
        glBindVertexArray( self.vao )

        # vertices
        self.vbo = glGenBuffers( 1 )
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData( GL_ARRAY_BUFFER, self.max_vertices * stride,  None,  GL_STATIC_DRAW )

        # indices
        self.ebo = glGenBuffers( 1 )
        glBindBuffer( GL_ELEMENT_ARRAY_BUFFER, self.ebo )
        glBufferData( GL_ELEMENT_ARRAY_BUFFER, self.max_indices * 4, None, GL_STATIC_DRAW )

        #
        # vertex layout
        #
        # Position
        glEnableVertexAttribArray( 0 )
        glVertexAttribPointer( 0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0) )

        # Normal
        glEnableVertexAttribArray( 2 )
        glVertexAttribPointer( 2, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12) )

        # UV
        glEnableVertexAttribArray( 1 )
        glVertexAttribPointer( 1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(24) )

        # Tangent
        glEnableVertexAttribArray( 3 )
        glVertexAttribPointer( 3, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(32) )

        # Bitangent
        glEnableVertexAttribArray( 4 )
        glVertexAttribPointer( 4, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(44) )

        glBindVertexArray( 0 )

    def append_mesh( self, cpu_mesh ):
        """
        Appends a CPUMeshData to the arena.
        Returns (baseVertex, firstIndex).
        """

        vtx_count = cpu_mesh.combined.shape[0]
        idx_count = len(cpu_mesh.mesh.faces) * 3
        #idx_count = cpu_mesh.num_indices
        #idx_count = cpu_mesh.indices.size

        if self.vertex_count + vtx_count > self.max_vertices:
            raise RuntimeError("VAO: vertex buffer overflow")

        if self.index_count + idx_count > self.max_indices:
            raise RuntimeError("VAO: index buffer overflow")

        # actual stride.. which sucks
        stride = cpu_mesh.combined.itemsize * cpu_mesh.combined.shape[1]
        print( stride )

        base_vertex = self.vertex_count
        first_index = self.index_count

        # Upload vertices
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferSubData(
            GL_ARRAY_BUFFER,
            base_vertex * self.vertex_stride(),
            cpu_mesh.combined.nbytes,
            cpu_mesh.combined
        )

        # Upload indices
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferSubData(
            GL_ELEMENT_ARRAY_BUFFER,
            first_index * 4,
            cpu_mesh.indices.nbytes,
            cpu_mesh.indices
        )

        # Upload indices
        #indices = cpu_mesh.indices + base_vertex
        #glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        #glBufferSubData(GL_ELEMENT_ARRAY_BUFFER,
        #                first_index * 4,
        #                indices.nbytes,
        #                indices)

        self.vertex_count += vtx_count
        self.index_count  += idx_count

        return base_vertex, first_index
   