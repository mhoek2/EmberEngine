from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo

from modules.renderer import Renderer

import impasse  as imp
import numpy as np

class Models:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer
        
        self.model = [i for i in range(30)]
        self.model_mesh = [{} for i in range(30)]

        self.num_models = 0

        self.basepath = "C:/Github-workspace/EmberEngine/assets/models/"
        return

    @staticmethod
    def prepare_gl_buffers( mesh ):
        gl = {}

        v = np.array( mesh.vertices, dtype='f' )  # Shape: (n_vertices, 3)
        n = np.array( mesh.normals, dtype='f' )    # Shape: (n_vertices, 3)

        if mesh.texture_coords is not None and len(mesh.texture_coords) > 0:
            t = np.array( mesh.texture_coords[0], dtype='f' )  # Shape: (n_vertices, 2)
        else:
            t = np.zeros( ( len(v), 2 ), dtype='f' )

        combined = np.hstack( ( v, n, t ) )  # Shape: (n_vertices, 8)

        gl["vbo"] = vbo.VBO( combined )
        gl["vbo_size"] = combined.itemsize
        gl["vbo_shape"] = combined.shape[1]

        # Fill the buffer for vertex positions
        gl["faces"] = glGenBuffers(1)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, gl["faces"])
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                     np.array(mesh.faces, dtype=np.int32),
                     GL_STATIC_DRAW)

        gl["nbfaces"] = len(mesh.faces)

        # Unbind buffers
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        return gl

    def loadOrFind( self, uid : str ) -> int:
        """Load or find an model, implement find later"""
        index = self.num_models

        self.model[index] = imp.load( f"{self.basepath}{uid}" )

        for mesh_idx, mesh in enumerate( self.model[index].meshes ):
            self.model_mesh[index][mesh_idx] = self.prepare_gl_buffers(mesh)

        self.num_models+=1
        return index

    def draw( self, index : int ) -> None:
        for mesh in self.model[index].meshes:
            mesh_index = self.model[index].meshes.index(mesh)

            mesh_gl = self.model_mesh[index][mesh_index]
            vbo = mesh_gl["vbo"]
            vbo.bind()

            size = mesh_gl["vbo_size"]
            stride = size * mesh_gl["vbo_shape"]
            
            glEnableVertexAttribArray( 0 )
            glVertexAttribPointer( 0, 3, GL_FLOAT, GL_FALSE, stride, None )

            glEnableVertexAttribArray( 1 )
            glVertexAttribPointer( 1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p( size * 6 ) )

            glEnableVertexAttribArray( 2 )
            glVertexAttribPointer( 2, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p( size * 3 ) )

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh_gl["faces"])
            glDrawElements(GL_TRIANGLES, mesh_gl["nbfaces"] * 3, GL_UNSIGNED_INT, None)

            vbo.unbind()
        return