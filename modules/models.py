import sys
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, Any, List, Dict, Callable

from gameObjects.attachables.model import Model

if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject

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
from dataclasses import dataclass, field

from queue import Queue
from threading import Thread
import traceback

class Models( Context ):
    @dataclass(slots=True)
    class CPUMeshData:
        """
        CPU-side representation of a mesh.

        Stores interleaved vertex data, indices, and metadata required
        for uploading the mesh to the GPU.

        :param combined: Interleaved vertex attributes (pos, normal, uv, tangent, bitangent)
        :param indices: Triangle index buffer (uint32)
        :param num_indices: Total number of indices
        :param material: Material ID assigned to the mesh
        :param path: Source model path
        :param mesh: Original imported mesh reference
        """
        combined    : np.ndarray      # interleaved vertex data
        indices     : np.ndarray       # uint32
        num_indices : int
        material    : int
        path        : Path
        mesh        : Any

    @dataclass(slots=True)
    class Load:
        """
        Model load request descriptor.

        Contains the source path and optional material override.


        :param path: Path to the model file
        :param material: Optional material override (-1 = auto)
        """
        path        : Path
        material    : int

    class Mesh(TypedDict):
        vao             : int
        vbo             : vbo.VBO
        vbo_size        : int
        vbo_shape       : Any # np._shape
        indices         : int # uint32/uintc
        num_indices     : int
        material        : int

    def __init__( self, context ):
        """Setup model buffers, containg mesh and material information 
        required to render.

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )

        self.materials  : Materials = context.materials
        
        self._num_models = 0
        self.model = [i for i in range(300)]
        self.model_mesh: List[List[Models.Mesh]] = [{} for _ in range(300)]
        self.model_map : Dict[Path, int] = {}
        self.model_loading : Dict[int, bool] = {}

        # default models
        self.default_cube_path = f"{self.settings.engineAssets}models\\cube\\model.obj"
        self.default_cube : Model = Model( 
            handle  = self.loadOrFind( Path(self.default_cube_path), self.context.materials.defaultMaterial, lazy_load=False ),
            path    = Path(self.default_cube_path)
        )

        self.default_sphere_path = f"{self.settings.engineAssets}models\\sphere\\model.obj"
        self.default_sphere : Model = Model( 
            handle  = self.loadOrFind( Path(self.default_sphere_path), self.context.materials.defaultMaterial, lazy_load=False ),
            path    = Path(self.default_sphere_path)
        )

        self.default_cilinder_path = f"{self.settings.engineAssets}models\\cilinder\\model.obj"
        self.default_cilinder : Model = Model( 
            handle  = self.loadOrFind( Path(self.default_cilinder_path), self.context.materials.defaultMaterial, lazy_load=False ),
            path    = Path(self.default_cilinder_path)
        )


        self.create_matrices( self.default_cube.handle )
        self.create_matrices( self.default_sphere.handle )
        self.create_matrices( self.default_cilinder.handle )
        self.context.renderer.comp_meshnode_matrices_dirty = True

        self.model_load_queue = Queue()
        self.model_ready_queue = Queue()

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

    def prepare_mesh_cpu( self, mesh, path: Path, material: int ) -> CPUMeshData:
        """
        Convert a mesh into an CPUMeshData CPU-side format.

        Generates missing attributes if needed and computes tangents
        and bitangents for normal mapping.

        :param mesh: Imported mesh object
        :param path: Source model path
        :type path: Path
        :param material: Material ID override (-1 = auto)
        :type material: int
        :return: CPU-side mesh data
        :rtype: CPUMeshData
        """
        v = np.asarray(mesh.vertices, dtype=np.float32)
        n = np.asarray(mesh.normals, dtype=np.float32)

        if n.shape[0] == 0:
            n = np.zeros_like(v)

        if mesh.texture_coords and len(mesh.texture_coords) > 0:
            t = np.asarray(mesh.texture_coords[0], dtype=np.float32)
        else:
            t = np.zeros((len(v), 2), dtype=np.float32)

        indices = np.asarray(mesh.faces, dtype=np.uint32).ravel()
        #indices  = np.array(mesh.faces, dtype=np.uint32).flatten()
        #indices  = np.array(mesh.faces).flatten()

        tangents, bitangents = self.compute_tangents_bitangents(v, t, indices)

        combined = np.hstack((v, n, t, tangents, bitangents)).astype(np.float32, copy=False)

        if material == -1:
            material = self.materials.loadOrFind( mesh.material, path )

        return Models.CPUMeshData(
            combined    = combined,
            indices     = indices,
            num_indices = len(indices),
            material    = material,
            path        = path,
            mesh        = mesh
        )

    def create_mesh_and_gl_buffers( self, cpu: CPUMeshData ) -> Mesh:
        """
        Upload CPU mesh data to the GPU and create OpenGL buffers.

            Sets up VBO, VAO, index buffer, and vertex attribute layout.

        :param cpu: CPU-side mesh data
        :return: GPU mesh handle
        :rtype: Mesh
        """
        _mesh : Models.Mesh = Models.Mesh()

        _mesh["vbo"]        = vbo.VBO( cpu.combined )
        _mesh["vbo_size"]   = cpu.combined.itemsize
        _mesh["vbo_shape"]  = cpu.combined.shape[1]

        _mesh["vao"]        = glGenVertexArrays(1)
        glBindVertexArray(_mesh["vao"])

        _mesh["vbo"].bind()

        stride = _mesh["vbo_size"] * _mesh["vbo_shape"]

        # Fill the buffer for vertex positions
        _mesh["indices"] = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, _mesh["indices"])
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, cpu.indices, GL_STATIC_DRAW)
        _mesh["num_indices"] = len(cpu.mesh.faces) * 3

        # Vertex Positions
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))

        # Normals
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(_mesh["vbo_size"] * 3))

        # UVs
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(_mesh["vbo_size"] * 6))

        # Tangents
        glEnableVertexAttribArray(3)
        glVertexAttribPointer(3, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(_mesh["vbo_size"] * 9))

        # Bitangents
        glEnableVertexAttribArray(4)
        glVertexAttribPointer(4, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(_mesh["vbo_size"] * 12))

        # Unbind VAO (which also unbinds the VBO from ARRAY_BUFFER target)
        glBindVertexArray(0)

        # Unbind buffers
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

        # material
        #if material == -1:
        #    _mesh["material"] = self.materials.loadOrFind( mesh.material, cpu.path.parent )
        #else:
        _mesh["material"] = cpu.material

        return _mesh

    def prepare_on_CPU( self, index : int, path : Path, material : int = -1 ) -> None:
        """
        Load a model from disk and prepare all meshes on the CPU.

        Returns a list of CPU-ready mesh data objects.

        :param index: Internal model index
        :type index: int
        :param path: Path to the model file
        :type path: Path
        :param material: Material ID override (-1 = auto)
        :type material: int
        :return: List of prepared CPU meshes
        :rtype: list[CPUMeshData]
        """
        self.model[index] = imp.load( str(path), processing=ProcessingStep.Triangulate | ProcessingStep.CalcTangentSpace )

        cpu_meshes : list[Models.CPUMeshData] = [
            self.prepare_mesh_cpu( mesh, path, material )
                for mesh_idx, mesh in enumerate( self.model[index].meshes )
        ]

        return cpu_meshes

    def upload_to_GPU( self, index : int, cpu_meshes: list[CPUMeshData] ) -> bool:
        """
        Upload CPU-prepared meshes to the GPU. Then free the list

        :param index: Internal model index
        :type index: int
        :param cpu_meshes: List of CPU mesh data objects
        :type cpu_meshes: list[CPUMeshData]
        :return: True if upload succeeded
        :rtype: bool
        """
        for mesh_idx, cpu in enumerate(cpu_meshes):
            self.model_mesh[index][mesh_idx] = self.create_mesh_and_gl_buffers( cpu )

        cpu_meshes.clear()

    def model_loader_thread( self ):
        """
        Worker thread for model loading and CPU pre-processing.

        Pulls load requests from the queue, assimp loads and prepares models (tangents).
        Then outputs prepared meshes to the ready queue.
        """
        while self.renderer.running:
            index, load = self.model_load_queue.get()

            try:
                cpu_meshes : Models.CPUMeshData = self.prepare_on_CPU( index, load.path, load.material )
                self.model_ready_queue.put( ( index, cpu_meshes ) )

            except Exception as e:
                _path = str(load.path.relative_to( self.settings.rootdir ) )
                _msg = f"Model failed to load: {_path}"
                exc_type, exc_value, exc_tb = sys.exc_info()

                self.console.error( _msg )
                self.console.error( e, traceback.format_tb(exc_tb) )
                print( _msg )

            self.model_load_queue.task_done()

    def model_loader_thread_flush( self ) -> None:
        """Receives ready CPU prepared meshes from work thread and uploads them to the GPU."""
        while not self.model_ready_queue.empty():
            index, cpu_meshes = self.model_ready_queue.get()

            self.upload_to_GPU( index, cpu_meshes )
            self.model_loading.pop( index )

            # construct static mesh matrix buffer
            self.create_matrices( index )
            self.context.renderer.comp_meshnode_matrices_dirty = True

    def loadOrFind( self, path : Path, material : int = -1, lazy_load : bool = True ) -> int:
        """Load or find an model, implement find later

        :param path: The path to the model file
        :type path: Path
        :param material: Could contain a material override if not -1
        :type material: int
        :param lazy: Lazy load models using threading
        :type lazy: bool
        """
        index = self._num_models

        if not path:
            return

        if not path.is_file():
            raise ValueError( f"Invalid model path!{str(path)}" )

        # try to locate existing model
        if path in self.model_map:
            return self.model_map[path]

        self.model_map[path] = index

        # lazy load
        if lazy_load:
            self.model_load_queue.put( ( index, Models.Load(
                path        = path,
                material    = material
            ) ) )
            self.model_loading[index] = True
            self.model[index] = None

        # wait tis frame for load to complete 
        # (default engine models, eg: cube, sphere and cilinder )
        else:
            cpu_meshes = self.prepare_on_CPU( index, path, material )
            self.upload_to_GPU( index, cpu_meshes )

        self._num_models += 1
        return index

    def __create_node_matrices( self, node, model_index : int, model_matrix : Matrix44 ):
        """Recursivly construct a list of nodes with their precomputed local model matrices"""
        world_matrix = model_matrix * Matrix44(node.transformation).transpose()

        for mesh in node.meshes:
            mesh_index = self.model[model_index].meshes.index(mesh)

            self.renderer.addNodeMatrix( model_index, mesh_index, world_matrix )

        for child in node.children:
            self.__create_node_matrices( child, model_index, world_matrix )

    def create_matrices( self, model ):
        """Collect local model matrices for nodes in this model"""
        if model == -1 or self.model[model] is None or model in self.model_loading:
            return

        model_matrix = Matrix44.identity()
        self.__create_node_matrices( self.model[model].root_node, model, model_matrix  )

    def __draw_collect( self, model_index, mesh_index, world_matrix, uuid = None ):
        self.renderer.addDrawItem( model_index, mesh_index, world_matrix, uuid )

    def __draw_instantly( self, model_index, mesh_index, world_matrix ):
        self.renderer.submitDrawItem( model_index, mesh_index, world_matrix )

    def __draw_node( self, node, model_index : int, model_matrix : Matrix44, dispatch : Callable ):
        """Recursivly process nodes (parent and child nodes)

        :param node: A node of model
        :type node: int
        :param model_index: The index of a loaded model
        :type model_index: int
        :param model_matrix: The transformation model matrix, used along with view and projection matrices
        :type model_matrix: matrix44
        :param dispatch: Reference to what function to dispatch (collect or immidiate rendering)
        :type dispatch: Callable
        """
        # apply transformation matrices recursivly
        world_matrix = model_matrix * Matrix44(node.transformation).transpose()

        for mesh in node.meshes:
            mesh_index = self.model[model_index].meshes.index(mesh)
            dispatch( model_index, mesh_index, world_matrix )

        # process child nodes
        for child in node.children:
            self.__draw_node( child, model_index, world_matrix, dispatch )

    def __collect_node( self, node, model_index, uuid ):
        """Collect node data with uuid, then use compute shader for modelmatrices"""
        for mesh in node.meshes:
            mesh_index = self.model[model_index].meshes.index(mesh)
            self.__draw_collect( model_index, mesh_index, None, uuid )

        # process child nodes
        for child in node.children:
            self.__collect_node( child, model_index, uuid )

    def draw( self, model : Model, model_matrix : Matrix44, instant : bool = False, uuid = None ) -> None:
        """Begin drawing a model

        :param model: The model object
        :type model: Model
        :param model_matrix: The transformation model matrix, used along with view and projection matrices
        :type model_matrix: matrix44
        :param instant:  either collect the drawcalls and submit them in renderer.end_frame() or render now/nstantly
        :type instant: bool
        """
        # this is still bad
        if model.handle == -1 or self.model[model.handle] is None or model.handle in self.model_loading:
            return

        # compute model matrices on CPU
        if instant or not self.context.renderer.USE_INDIRECT:
            # either collect the drawcalls and submit them in renderer.end_frame() or render instantly
            dispatch = self.__draw_collect if not instant else self.__draw_instantly
            self.__draw_node( self.model[model.handle].root_node, model.handle, model_matrix, dispatch )

        # compute model matrices on GPU usinf compute shader
        else:
            self.__collect_node( self.model[model.handle].root_node, model.handle, uuid )