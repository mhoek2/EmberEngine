from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, Any, List, Dict

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
from pyrr import Matrix44

from modules.context import Context
from modules.material import Materials

import impasse as imp
from impasse.constants import MaterialPropertyKey, ProcessingStep
import numpy as np

from modules.settings import Settings

class Models( Context ):
    class Mesh(TypedDict):
        vbo         : vbo.VBO
        vbo_size    : int
        vbo_shape   : Any # np._shape
        faces       : int # uint32/uintc
        nbfaces     : int
        material    : int

    def __init__( self, context ):
        """Setup model buffers, containg mesh and material information 
        required to render.
        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )

        self.materials  : Materials = context.materials
        
        self.model = [i for i in range(300)]
        #self.model_mesh = [{} for i in range(300)]
        self.model_mesh: List[List[Models.Mesh]] = [{} for _ in range(300)]

        self._num_models = 0

        return

    @staticmethod
    def normalize( vectors ):
        """Normalize a vector array"""
        lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
        return np.divide(vectors, lengths, where=lengths != 0)

    def compute_tangents_bitangents( self, vertices, tex_coords, indices ):
        """Compute tangent spaces for vertices
        :param vertices: The vertices in the mesh
        :type vertices: ndarray - shape 3. 
        :param tex_coords: The texture coordinates
        :type tex_coords: ndarray - shape 2. 
        :param indices: The indices for the mesh
        :type indices: ndarray - c. 
        :returns: tangents, bitanges 
        :rtype: ndarray; shape 3, ndarray; shape 3
        """
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

    def prepare_gl_buffers( self, mesh, path : Path, material : int = -1 ) -> Mesh:
        """Prepare and store mesh in a vertex buffer, along with meta data like 
        size or material id
        :param mesh: The mesh loaded from Impasse
        :type mesh:
        :param path: The path of the folder the model is stored in, used to lookup textures
        :type path: Path
        :param material: Could contain a material override if not -1
        :type material: int
        :return: The meta data for this mesh, containing uid where VBO is stored along with size, shape, material id
        :rtype: Mesh
        """
        _mesh : Models.Mesh = Models.Mesh()

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

        _mesh["vbo"] = vbo.VBO( combined )
        _mesh["vbo_size"] = combined.itemsize
        _mesh["vbo_shape"] = combined.shape[1]

        # Fill the buffer for vertex positions
        _mesh["faces"] = glGenBuffers(1)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, _mesh["faces"])
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,
                     np.array(mesh.faces, dtype=np.int32),
                     GL_STATIC_DRAW)

        _mesh["nbfaces"] = len(mesh.faces)

        # Unbind buffers
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        # material
        if material == -1:
            _mesh["material"] = self.materials.loadOrFind( mesh.material, path )
        else:
            _mesh["material"] = material

        return _mesh

    def loadOrFind( self, file : Path, material : int = -1 ) -> int:
        """Load or find an model, implement find later
        :param file: The path to the model file
        :type file: Path
        :param material: Could contain a material override if not -1
        :type material: int
        """
        index = self._num_models

        if not file.is_file():
            raise ValueError( f"Invalid model path!{str(file)}" )

        self.model[index] = imp.load( str(file), processing=ProcessingStep.Triangulate | ProcessingStep.CalcTangentSpace )
        
        for mesh_idx, mesh in enumerate( self.model[index].meshes ):
            self.model_mesh[index][mesh_idx] = self.prepare_gl_buffers( mesh, file.parent, material=material )

        self._num_models += 1
        return index

    def render( self, model_index : int , mesh_index : int , model_matrix : Matrix44 ):
        """Render the mesh from a node
        :param model_index: The index of a loaded model
        :type model_index: int
        :param mesh_index:  The index of a mesh within that model
        :type mesh_index: int
        :param model_matrix: The transformation model matrix, used along with view and projection matrices
        :type model_matrix: matrix44
        """
        mesh : Models.Mesh = self.model_mesh[model_index][mesh_index]

        vbo = mesh["vbo"]
        vbo.bind()

        size = mesh["vbo_size"]
        stride = size * mesh["vbo_shape"]
            
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
        self.materials.bind( mesh["material"] )

        if self.settings.drawWireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

        glUniformMatrix4fv( self.renderer.shader.uniforms['uMMatrix'], 1, GL_FALSE, model_matrix )

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, mesh["faces"])
        glDrawElements(GL_TRIANGLES, mesh["nbfaces"] * 3, GL_UNSIGNED_INT, None)

        if self.settings.drawWireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        vbo.unbind()

    def draw_node( self, node, model_index : int, model_matrix : Matrix44 ):
        """Recursivly process nodes (parent and child nodes)
        :param node: A node of model
        :type node: int
        :param model_index: The index of a loaded model
        :type model_index: int
        :param model_matrix: The transformation model matrix, used along with view and projection matrices
        :type model_matrix: matrix44
        """
        # apply transformation matrices recursivly
        global_transform = model_matrix * Matrix44(node.transformation).transpose()

        for mesh in node.meshes:
            mesh_index = self.model[model_index].meshes.index(mesh)
            self.render( model_index, mesh_index, global_transform )

        # process child nodes
        for child in node.children:
            self.draw_node( child, model_index, global_transform )

    def draw( self, model_index : int, model_matrix : Matrix44 ) -> None:
        """Begin drawing a model by index
        :param model_index: The index of a loaded model
        :type model_index: int
        :param model_matrix: The transformation model matrix, used along with view and projection matrices
        :type model_matrix: matrix44
        """
        self.draw_node( self.model[model_index].root_node, model_index, model_matrix )

        #for mesh in self.model[index].meshes:
        #    mesh_index = self.model[index].meshes.index(mesh)
        #
        #    self.render( index, mesh_index, model_matrix )