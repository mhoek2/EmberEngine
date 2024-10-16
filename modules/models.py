from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo

from modules.renderer import Renderer
from modules.material import Material

import impasse  as imp
from impasse.constants import MaterialPropertyKey, ProcessingStep
import numpy as np

import os

class Models:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer
        self.materials : Material = context.materials
        
        self.model = [i for i in range(30)]
        self.model_mesh = [{} for i in range(30)]
        #self.model_material = [[] for i in range(30)]

        self.num_models = 0

        return

    @staticmethod
    def normalize(vectors):
        # Normalize a vector array
        lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
        return np.divide(vectors, lengths, where=lengths != 0)

    def compute_tangents_bitangents(self, vertices, tex_coords, indices):
        # Create empty tangent and bitangent arrays
        tangents = np.zeros_like(vertices)
        bitangents = np.zeros_like(vertices)

        # Iterate through each triangle
        for i in range(0, len(indices), 3):
            # Get vertex indices
            i0, i1, i2 = indices[i], indices[i + 1], indices[i + 2]

            # Get vertex positions
            v0 = vertices[i0]
            v1 = vertices[i1]
            v2 = vertices[i2]

            # Get texture coordinates
            uv0 = tex_coords[i0]
            uv1 = tex_coords[i1]
            uv2 = tex_coords[i2]

            # Calculate edges
            delta_pos1 = v1 - v0
            delta_pos2 = v2 - v0
            delta_uv1 = uv1 - uv0
            delta_uv2 = uv2 - uv0

            # Calculate the tangent and bitangent
            r = 1.0 / (delta_uv1[0] * delta_uv2[1] - delta_uv1[1] * delta_uv2[0])
            tangent = r * (delta_pos1 * delta_uv2[1] - delta_pos2 * delta_uv1[1])
            bitangent = r * (-delta_pos1 * delta_uv2[0] + delta_pos2 * delta_uv1[0])

            # Assign the computed tangents and bitangents to the vertices
            tangents[i0] += tangent
            tangents[i1] += tangent
            tangents[i2] += tangent

            bitangents[i0] += bitangent
            bitangents[i1] += bitangent
            bitangents[i2] += bitangent

        # Normalize the tangents and bitangents
        tangents = self.normalize( tangents )
        bitangents = self.normalize( bitangents )

        return tangents, bitangents


    def prepare_gl_buffers( self, mesh ):
        gl = {}

        v = np.array( mesh.vertices, dtype='f' )  # Shape: (n_vertices, 3)
        n = np.array( mesh.normals, dtype='f' )    # Shape: (n_vertices, 3)

        if mesh.texture_coords is not None and len(mesh.texture_coords) > 0:
            t = np.array( mesh.texture_coords[0], dtype='f' )  # Shape: (n_vertices, 2)
        else:
            t = np.zeros( ( len(v), 2 ), dtype='f' )

        # create tangents
        indices = np.array(mesh.faces).flatten()
        tangents, bitangents = self.compute_tangents_bitangents( v, t, indices )

        combined = np.hstack( ( v, n, t, tangents, bitangents ) )  # Shape: (n_vertices, 8)

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

        # material
        gl["material"] = self.materials.loadOrFind( mesh.material, self.path_dir )

        return gl

    def loadOrFind( self, path : str ) -> int:
        """Load or find an model, implement find later"""
        index = self.num_models

        self.model[index] = imp.load( path, processing=ProcessingStep.Triangulate | ProcessingStep.CalcTangentSpace )

        # used for textures
        self.path_dir = os.path.dirname( path )

        for mesh_idx, mesh in enumerate( self.model[index].meshes ):
            self.model_mesh[index][mesh_idx] = self.prepare_gl_buffers(mesh)

        # need to release?

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
            
            # vertex
            glEnableVertexAttribArray( 0 )
            glVertexAttribPointer( 0, 3, GL_FLOAT, GL_FALSE, stride, None )

            # normal
            glEnableVertexAttribArray( 2 )
            glVertexAttribPointer( 2, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p( size * 3 ) )

            # uv
            glEnableVertexAttribArray( 1 )
            glVertexAttribPointer( 1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p( size * 6 ) )

            # tangents
            glEnableVertexAttribArray( 3 )
            glVertexAttribPointer( 3, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p( size * 9 ) )

            # bitangents
            glEnableVertexAttribArray( 4 )
            glVertexAttribPointer( 4, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p( size * 12 ) )


            # material
            self.materials.bind( mesh_gl["material"] )

            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh_gl["faces"])
            glDrawElements(GL_TRIANGLES, mesh_gl["nbfaces"] * 3, GL_UNSIGNED_INT, None)

            vbo.unbind()
        return