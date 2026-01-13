from typing import TYPE_CHECKING, TypedDict

import os
import struct

from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *
from OpenGL.GL.ARB.bindless_texture import *

import numpy as np
import enum

from modules.render.shader import Shader
from modules.render.types import DrawItem, MatrixItem, Material

if TYPE_CHECKING:
    from main import EmberEngine
    from modules.renderer import Renderer
    from modules.models import Models
    from gameObjects.gameObject import GameObject
    from gameObjects.gameObject import Camera

import ctypes
from collections import defaultdict
import uuid as uid

class DrawElementsIndirectCommand(ctypes.Structure):
    _fields_ = [
        ("count",         ctypes.c_uint),
        ("instanceCount", ctypes.c_uint),
        ("firstIndex",    ctypes.c_uint),
        #("baseVertex",    ctypes.c_uint),
        ("baseVertex",    ctypes.c_int),
        ("baseInstance",  ctypes.c_uint),
    ]

class ObjectBlock(ctypes.Structure):
    _fields_ = [
        ("model",               ctypes.c_float * 16),
        ("material",            ctypes.c_int),
        ("meshNodeMatrixId",    ctypes.c_int),
        ("gameObjectMatrixId",  ctypes.c_int),
        ("pad2",                ctypes.c_int),
    ]

class ModelBlock(ctypes.Structure):
    _fields_ = [
        ("nodeOffset",          ctypes.c_int),
        ("nodeCount",           ctypes.c_int),
        ("pad0",                ctypes.c_int),
        ("pad1",                ctypes.c_int),
    ]

class MeshNodeBlock(ctypes.Structure):
    _fields_ = [
        ("model",               ctypes.c_float * 16),
        ("num_indices",         ctypes.c_int),  # use for indirect compute shader only -USE_INDIRECT_COMPUTE
        ("firstIndex",          ctypes.c_int),  # use for indirect compute shader only -USE_INDIRECT_COMPUTE
        ("baseVertex",          ctypes.c_int),  # use for indirect compute shader only -USE_INDIRECT_COMPUTE
        ("material",            ctypes.c_int),
        ("min_aabb",            ctypes.c_float * 4),
        ("max_aabb",            ctypes.c_float * 4),
    ]

class GameObjectBlock(ctypes.Structure):
    _fields_ = [
        ("model",               ctypes.c_float * 16),
        ("model_index",         ctypes.c_int),
        ("enabled",             ctypes.c_int),
        ("pad1",                ctypes.c_int),
        ("pad2",                ctypes.c_int),
    ]

class BatchBlock(ctypes.Structure):
    _fields_ = [
        ("instanceCount",       ctypes.c_int),
        ("baseInstance",        ctypes.c_int),
        ("meshNodeMatrixId",    ctypes.c_int),
        ("pad1",                ctypes.c_int),
    ]

class InstanceBlock(ctypes.Structure):
    _fields_ = [
        ("ObjectId",        ctypes.c_uint),
        ("pad0",            ctypes.c_uint),
        ("pad1",            ctypes.c_uint),
        ("pad1",            ctypes.c_uint),
    ]

class UBO:
    def __init__( self, context ):
        """Renderer backend, creating window instance, openGL, FBO's, shaders and rendertargets

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        self.context    : 'EmberEngine' = context

        # indirect drawing constructs the drawBlock final modelmatrices using 
        # a compute shader, to do that. a list for each model/mesh combo is required
        # this list is then flattened and uploaded to a SSBO
        # to index the correct model/mesh combo, a map is used.
        # also, a map of the gameObjects modelmatrices is required with a map
        self.comp_gameobject_matrices_map   : dict[uid.UUID, int] = {}          # uuid -> offset
        self.comp_meshnode_matrices_dirty   : bool = True
        self.comp_meshnode_matrices_nested  : dict[int, list[MatrixItem]] = {}  # not flattened
        self.comp_meshnode_matrices_map     : dict[(int, int), int] = {}        # (model_index, mesh_index) -> offset
        self.comp_meshnode_max              : int = 0 # max possible bacthes to make

        self.object_map     : dict[(int, int, int), int] = {}

    class GpuBuffer:
        def __init__( self, max_elements, element_type, target, buffer_type = ctypes.c_float ):
            self.max_elements   = max_elements
            self.element_type   = element_type
            self.target         = target

            if isinstance(element_type, int):
                self.element_size = element_type      # number of floats per element
                self.buffer = (buffer_type * (max_elements * self.element_size))()
                self.is_struct = False
            else:
                # structured type
                self.element_size = ctypes.sizeof(element_type)  # bytes per element
                self.buffer = (element_type * max_elements)()
                self.is_struct = True

            self.ssbo           = glGenBuffers(1)

            glBindBuffer( target, self.ssbo )
            glBufferData( target, ctypes.sizeof(self.buffer), None, GL_DYNAMIC_DRAW )

        def upload( self, num_elements ):
            glBindBuffer( self.target, self.ssbo )

            if self.is_struct:
                size_bytes = num_elements * self.element_size
            else:
                size_bytes = num_elements * self.element_size * 4  # float32 = 4 bytes

            glBufferSubData(self.target, 0, size_bytes, self.buffer)
            
        def bind_buffer( self, binding : int = 0 ):
            glBindBuffer( self.target, self.ssbo )

        def bind_base( self, binding : int = 0 ):
            glBindBufferBase( self.target, binding, self.ssbo )

        def clear(self, value=0):
            glBindBuffer(self.target, self.ssbo)

            if self.is_struct:
                glClearBufferData( self.target, GL_R32UI, GL_RED_INTEGER, GL_UNSIGNED_INT, ctypes.c_uint32(value) )

            else:
                glClearBufferData( self.target, GL_R32F, GL_RED, GL_FLOAT, ctypes.c_float(value) )

    def initialize( self ):
        # context
        self.renderer   : 'Renderer' = self.context.renderer

        #
        # general
        #
        self.ubo_lights             : UBO.LightUBO     = UBO.LightUBO( self.renderer.general, "Lights" )
        if self.renderer.USE_BINDLESS_TEXTURES:
            self.ubo_materials      : UBO.MaterialUBOBindless  = UBO.MaterialSSBOBindless( self.context )
        else:
            self.ubo_materials      : UBO.MaterialUBO  = UBO.MaterialUBO( self.context, self.renderer.general, "Materials" )

        #
        # indirect
        #
        if self.renderer.USE_INDIRECT:
            MAX_MATRICES = 10000
            MAX_DRAWS = 10000
            MAX_BATCHES = 1000
            MAX_MODELS = 1000
            MAX_MESH_NODE_BATCHES = 4096    # for alloc only, approx size is calculated at runtime

            # compute
            self.model_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_MODELS,
                 element_type   = ModelBlock,
                 target         = GL_SHADER_STORAGE_BUFFER
            )

            self.comp_meshnode_matrices_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_MATRICES,
                 element_type   = MeshNodeBlock,
                 target         = GL_SHADER_STORAGE_BUFFER
            )

            self.comp_gameobject_matrices_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_MATRICES,
                 element_type   = GameObjectBlock, # 64 bytes mat4 item buffer
                 target         = GL_SHADER_STORAGE_BUFFER
            )

            self.batch_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_BATCHES,
                 element_type   = BatchBlock,
                 target         = GL_SHADER_STORAGE_BUFFER
            )
  
            # render
            self.object_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_DRAWS,
                 element_type   = ObjectBlock,
                 target         = GL_SHADER_STORAGE_BUFFER
            )

            if self.renderer.USE_FULL_GPU_DRIVEN:
                # object base, precomuted index table for: gid(gameObject idx) + nodeIndex
                self.object_base_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                        max_elements   = MAX_MATRICES,
                        element_type   = 4,
                        target         = GL_SHADER_STORAGE_BUFFER,
                        buffer_type    = ctypes.c_uint
                )

            self.indirect_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_DRAWS,
                 element_type   = DrawElementsIndirectCommand,
                 target         = GL_DRAW_INDIRECT_BUFFER
            )

            self.instances_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                    max_elements   = MAX_MESH_NODE_BATCHES,
                    element_type   = InstanceBlock,
                    target         = GL_SHADER_STORAGE_BUFFER
            )
        #
        # Full GPU driven pipeline
        #
        if self.renderer.USE_FULL_GPU_DRIVEN:
            MAX_INSTANCES = 4096 * 10
            MAX_MESH_NODE_BATCHES = 4096    # for alloc only, approx size is calculated at runtime

            # atomics
            self.batch_counter = glGenBuffers(1)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.batch_counter)
            glBufferData(GL_SHADER_STORAGE_BUFFER, 4, None, GL_DYNAMIC_DRAW)  # one uint

            self.instance_counter = glGenBuffers(1)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.instance_counter)
            glBufferData(GL_SHADER_STORAGE_BUFFER, 4, None, GL_DYNAMIC_DRAW)  # one uint

            # buffers
            self.mesh_instance_counter = glGenBuffers(1)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.mesh_instance_counter)
            glBufferData(GL_SHADER_STORAGE_BUFFER, 4 * MAX_MESH_NODE_BATCHES, None, GL_DYNAMIC_DRAW)  # uint array

            self.mesh_instance_writer = glGenBuffers(1)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.mesh_instance_writer)
            glBufferData(GL_SHADER_STORAGE_BUFFER, 4 * MAX_MESH_NODE_BATCHES, None, GL_DYNAMIC_DRAW)  # uint array

            self.meshnode_to_batch = glGenBuffers(1)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.meshnode_to_batch)
            glBufferData(GL_SHADER_STORAGE_BUFFER, 4 * MAX_MESH_NODE_BATCHES, None, GL_DYNAMIC_DRAW)  # uint array

            # visbuf, I dont fancy this. (design issue)
            # reserve 100 node gap between gameobjects, store states for 32 nodes in one uint.
            # needs a 100 gap, because the amount of nodes varies per object. 
            # maybe use 'object_base_ssbo' for this as well?
            MAX_NODES_PER_MODEL = 100
            self.visbuf = glGenBuffers(1)
            glBindBuffer(GL_SHADER_STORAGE_BUFFER, self.visbuf)
            glBufferData(GL_SHADER_STORAGE_BUFFER, 4 * (MAX_DRAWS * MAX_NODES_PER_MODEL), None, GL_DYNAMIC_DRAW)  # uint array

    #
    # general 330 compat, 
    # TODO: Maybe merge with GpuBuffer eventually?
    #
    class MaterialSSBOBindless:
        MAX_MATERIALS = 2096
        # std430 layout: 5 uint64_t, 1 int, 1 uint padding = 48 bytes per material
        STRUCT_LAYOUT = struct.Struct("QQQQQiI")

        def __init__( self, context ):
            self.context    : 'EmberEngine' = context

            self._dirty = True

            self.data = bytearray()

            self.ubo = glGenBuffers(1)
            glBindBuffer( GL_SHADER_STORAGE_BUFFER, self.ubo )

            total_size = self.MAX_MATERIALS * self.STRUCT_LAYOUT.size
            glBufferData( GL_SHADER_STORAGE_BUFFER, total_size, None, GL_DYNAMIC_DRAW )
            glBindBuffer( GL_SHADER_STORAGE_BUFFER, 0 )

        def update( self, count : int, materials : list[Material] ):
            num_materials = min(count, self.MAX_MATERIALS)
            self.data = bytearray()

            # u_materials
            for mat in materials[:num_materials]:
                self.data += self.STRUCT_LAYOUT.pack(
                    self.context.images.tex_to_bindless( mat.albedo   ),
                    self.context.images.tex_to_bindless( mat.normal   ),
                    self.context.images.tex_to_bindless( mat.phyiscal ),
                    self.context.images.tex_to_bindless( mat.emissive ),
                    self.context.images.tex_to_bindless( mat.opacity  ),
                    mat.hasNormalMap,
                    0  # padding
                )

            # fill empty materials
            empty_count = self.MAX_MATERIALS - num_materials
            if empty_count:
                empty = self.STRUCT_LAYOUT.pack( 0, 0, 0, 0, 0, 0, 0 )
                self.data += empty * empty_count

            self._dirty = False

            glBindBuffer( GL_SHADER_STORAGE_BUFFER, self.ubo )
            glBufferSubData( GL_SHADER_STORAGE_BUFFER, 0, len(self.data), self.data )

        def bind( self, binding : int = 0 ):
            glBindBufferBase( GL_SHADER_STORAGE_BUFFER, binding, self.ubo )

    class MaterialUBO:
        MAX_MATERIALS = 2096

        # std140 layout: 1 vec4 = 16 bytes per material
        STRUCT_LAYOUT = struct.Struct( b"4f" )

        def __init__( self, context,
                     shader : Shader, 
                     block_name     : str ="Material"
            ):
            self.context    : 'EmberEngine' = context

            self._dirty : bool = True

            self.data = bytearray()

            # support older openGL versions (sub 4.2):
            self.binding = 1
            self.block_index = glGetUniformBlockIndex( shader.program, block_name )
            if self.block_index == GL_INVALID_INDEX:
                raise RuntimeError( f"Uniform block [{block_name}] not found in shader." )
            glUniformBlockBinding( shader.program, self.block_index, self.binding )

            # create UBO
            self.ubo = glGenBuffers(1)
            glBindBuffer( GL_UNIFORM_BUFFER, self.ubo )

            # MAX_MATERIALS * 16 bytes
            total_size = self.MAX_MATERIALS * self.STRUCT_LAYOUT.size
            glBufferData( GL_UNIFORM_BUFFER, total_size, None, GL_DYNAMIC_DRAW )
            glBindBuffer( GL_UNIFORM_BUFFER, 0 )

        def update( self, count : int, materials : list[Material] ):
            num_materials = min(count, self.MAX_MATERIALS)

            self.data = bytearray()

            # u_materials
            for mat in materials[:num_materials]:

                self.data += self.STRUCT_LAYOUT.pack(
                    mat.hasNormalMap, 0.0, 0.0, 0.0
                )

            # fill empty materials
            empty_count = self.MAX_MATERIALS - num_materials
            if empty_count:
                empty = self.STRUCT_LAYOUT.pack(
                    0, 0, 0, 0, # vec4(origin.xyz + radius)
                )
                self.data += empty * empty_count

            glBindBuffer( GL_UNIFORM_BUFFER, self.ubo )
            glBufferSubData( GL_UNIFORM_BUFFER, 0, len(self.data), self.data )

            self._dirty = False

        def bind( self, binding : int = 0 ):
            glBindBufferBase( GL_UNIFORM_BUFFER, binding, self.ubo )

    class LightUBO:
        MAX_LIGHTS = 64

        # std140 layout:
        # vec4(origin.xyz + radius) + vec4(color.xyzw) + vec3(rotation + pad0) = 48 bytes
        LIGHT_STRUCT = struct.Struct( b"4f 4f 4f" )

        class Light(TypedDict):
            origin      : list[float]
            rotation    : list[float]
            color       : list[float]
            radius      : int
            intensity   : float
            t           : int # gameObjects.attachables.Light.Type_

        def __init__(self, 
                     shader : Shader, 
                     block_name     : str ="Lights"
            ):
            self.data = bytearray()
            self.lights : list[UBO.LightUBO.Light] = [UBO.LightUBO.Light() for _ in range(self.MAX_LIGHTS) ]

            # support older openGL versions (sub 4.2):
            self.binding = 0
            self.block_index = glGetUniformBlockIndex( shader.program, block_name )
            if self.block_index == GL_INVALID_INDEX:
                raise RuntimeError( f"Uniform block [{block_name}] not found in shader." )
            glUniformBlockBinding( shader.program, self.block_index, self.binding )

            # create UBO
            self.ubo = glGenBuffers(1)
            glBindBuffer( GL_UNIFORM_BUFFER, self.ubo )

            # (u_num_lights 4b + 12bpad = 16 bytes) + 32 * 64 bytes
            total_size = 16 + self.MAX_LIGHTS * self.LIGHT_STRUCT.size
            glBufferData( GL_UNIFORM_BUFFER, total_size, None, GL_DYNAMIC_DRAW )
            glBindBuffer( GL_UNIFORM_BUFFER, 0 )

        def update( self, num_lights : int ):
            num_lights = min(num_lights, self.MAX_LIGHTS)

            self.data = bytearray()

            # u_num_lights
            self.data += struct.pack("I 3I", num_lights, 0, 0, 0)

            # u_lights
            for light in self.lights[:num_lights]:
                ox, oy, oz  = light["origin"]
                cx, cy, cz  = light["color"]
                rx, ry, rz  = light["rotation"]

                self.data += self.LIGHT_STRUCT.pack(
                    ox, oy, oz, light["radius"],    # vec4(origin.xyz + radius)
                    cx, cy, cz, int(light["t"]),    # vec4(color.xyz + t(type))
                    rx, ry, rz, light["intensity"], # vec4(rotation.xyz + intensity)
                )

            # fill empty lights
            empty_count = self.MAX_LIGHTS - num_lights
            if empty_count:
                empty = self.LIGHT_STRUCT.pack(
                    0, 0, 0, 0, # vec4(origin.xyz + radius)
                    0, 0, 0, 0,  # vec4(color + type)
                    0, 0, 0, 0  # vec4(rotation + intensiry)
                )
                self.data += empty * empty_count

            glBindBuffer(GL_UNIFORM_BUFFER, self.ubo)
            glBufferSubData(GL_UNIFORM_BUFFER, 0, len(self.data), self.data)

        def bind( self, binding : int = 0 ):
            glBindBufferBase( GL_UNIFORM_BUFFER, binding, self.ubo )
   
  
    def _upload_material_ubo( self ) -> None:
        """Build a UBO of materials and upload to GPU, rebuild when material list is marked dirty"""
        if self.ubo_materials._dirty:
            self.ubo_materials.update( 
                self.context.materials._num_materials, 
                self.context.materials.materials 
            )

    def _upload_lights_ubo( self, sun : "GameObject" ) -> None:
        """Build a UBO of lights, rebuilds every frame (currently)
        
        :param sun: The sun GameObject, light is excluded from UBO
        :type sun: GameObject
        """
        num_lights = 0
        for uuid in self.context.world.lights.keys():
            obj : "GameObject" = self.context.world.gameObjects[uuid]

            if not obj.hierachyActive() or obj is sun:
                continue

            if not self.renderer.game_runtime and not obj.hierachyVisible():
                continue

            self.ubo_lights.lights[num_lights] = UBO.LightUBO.Light(
                origin      = obj.transform.position,
                rotation    = obj.transform.rotation,

                color       = obj.light.light_color,
                radius      = obj.light.radius,
                intensity   = obj.light.intensity,
                t           = obj.light.light_type
            )
            num_lights += 1

        self.ubo_lights.update( num_lights )

    #
    # indirect
    #
    def _update_comp_meshnode_matrices_ssbo( self ):
        """
        Static flattened SSBO containing all local model matrices for each model:node(mesh)
        Updates only occur, when additional model(s) are loaded
        """
        if not self.comp_meshnode_matrices_dirty:
            return

        if not self.renderer.USE_INDIRECT:
            self.comp_meshnode_matrices_dirty = False
            return

        # clear the mapping table, it is rebuilt.
        self.comp_meshnode_matrices_map = {}       # (model_index, mesh_index) -> offset
        self.comp_meshnode_max = 0

        offset = 0
        node_offset = 0;
        _model_ssbo         = self.model_ssbo
        _model_buffer       = self.model_ssbo.buffer
        _mesh_ssbo          = self.comp_meshnode_matrices_ssbo
        _mesh_buffer        = self.comp_meshnode_matrices_ssbo.buffer
        _mesh_offset_map    = self.comp_meshnode_matrices_map

        #for model_index, items in self.comp_meshnode_matrices_nested.items():
        for i, (model_index, items) in enumerate(self.comp_meshnode_matrices_nested.items()):
            for item in items:
                mesh : "Models.Mesh" = self.context.models.model_mesh[model_index][item.mesh_index]

                # before indirect compute ssbo used a one mat4 stride: 
                # renderer.element_type = 16, # 64 bytes mat4 item buffer
                #self.comp_meshnode_matrices_ssbo.buffer[offset*16:(offset+1)*16] = item.matrix.flatten()

                # model matrix
                _mesh_buffer[offset].model[:] = np.asarray(item.matrix, dtype=np.float32).reshape(16)

                # aabb
                _mesh_buffer[offset].min_aabb[:] = ( item.min_aabb[0], item.min_aabb[1], item.min_aabb[2], 1.0 )
                _mesh_buffer[offset].max_aabb[:] = ( item.max_aabb[0], item.max_aabb[1], item.max_aabb[2], 1.0 )

                # material
                _mesh_buffer[offset].material = mesh["material"]

                if self.context.renderer.USE_INDIRECT_COMPUTE:
                    # use for indirect compute shader only -USE_INDIRECT_COMPUTE
                    _mesh_buffer[offset].num_indices = mesh["num_indices"]
                    _mesh_buffer[offset].firstIndex = mesh["firstIndex"]
                    _mesh_buffer[offset].baseVertex = mesh["baseVertex"]
            
                # create a map
                _mesh_offset_map[(model_index, item.mesh_index)] = offset
                offset += 1

            # model info
            _model_buffer[model_index].nodeOffset = node_offset
            _model_buffer[model_index].nodeCount = len(items)
            node_offset += len(items)

        # max num nodes
        self.comp_meshnode_max += node_offset

        # upload to SSBO
        _mesh_ssbo.upload( offset )
        _model_ssbo.upload( len(self.comp_meshnode_matrices_nested) )

        self.comp_meshnode_matrices_dirty = False   

    def _upload_comp_gameobject_matrices_map_ssbo( self ):
        """Build a SSBO with all gameObjects world matrices
        
            Still happens per frame.
        
        """
        # clear the mapping table, it is rebuilt.
        self.comp_gameobject_matrices_map = {}

        self.comp_gameobject_matrices_ssbo.clear()

        offset = 0
        _gameobject_ssbo        = self.comp_gameobject_matrices_ssbo
        _gameobject_buffer      = self.comp_gameobject_matrices_ssbo.buffer
        _gameobject_offset_map  = self.comp_gameobject_matrices_map

        for uuid, transform in self.context.world.transforms.items():
            #if uuid in self.context.world.trash:
            #    continue

            #_gameobject_buffer[offset*16:(offset+1)*16] = transform.world_model_matrix.flatten()
            _gameobject_buffer[offset].model[:] = np.asarray(transform.world_model_matrix, dtype=np.float32).reshape(16)
            
            # active/visible state
            obj : GameObject = transform.gameObject
            _gameobject_buffer[offset].enabled = obj.hierachyActive() \
                         and (self.renderer.game_runtime or obj.hierachyVisible()) \
                         and not (obj.is_camera and self.renderer.game_runtime)

            if uuid in self.context.world.models:
                _gameobject_buffer[offset].model_index = self.context.world.models[uuid].handle
            else:
                _gameobject_buffer[offset].model_index = -1

            # create a map
            _gameobject_offset_map[uuid] = offset
            offset += 1

        # upload to SSBO
        _gameobject_ssbo.upload( offset )

    def _build_batched_draw_list( self, _draw_list : list[DrawItem] ) -> dict[tuple[int, int], list[DrawItem]]:
        """Convert draw_list to a grouped list per model:mesh(node) used for indirect batching"""
        batches = {}

        for item in _draw_list:
            key = (item.model_index, item.mesh_index)

            if key not in batches:
                batches[key] = []

            batches[key].append(item)

        #print( f"{len(batches)}")
        #for (model_index, mesh_index), batch in batches.items():   
        #    mesh_id = (model_index, item.mesh_index)
        #    meshNodeMatrixId = int(self.comp_meshnode_matrices_map[mesh_id]) if mesh_id in self.comp_meshnode_matrices_map else 0
        #    print( f"[{meshNodeMatrixId}] = {len(batch)}")

        return batches, len(_draw_list)

    def _cpu_build_object_base( self ) -> None:
        """object base, precomuted index table for: gid(gameObject idx) + nodeIndex"""
        object_base : int = 0
        object_idx : int = 0

        _object_base_ssbo        = self.object_base_ssbo
        _object_base_buffer      = self.object_base_ssbo.buffer

        _gameobject_buffer  = self.comp_gameobject_matrices_ssbo.buffer
        _model_buffer       = self.model_ssbo.buffer

        for i, uuid in enumerate(self.context.world.transforms.keys()):      
            
            gid = self.comp_gameobject_matrices_map[uuid]

            obj = _gameobject_buffer[gid]
            
            if obj.enabled == 0 or obj.model_index < 0: 
                _object_base_buffer[gid] = -1
                continue

            model = _model_buffer[obj.model_index]
            
            _object_base_buffer[gid] = object_base
            object_base += model.nodeCount

        _object_base_ssbo.upload( i )

    def _upload_object_blocks_ssbo( self ):
        """
        Create the per draw ssbo used for indirect rendering
        For indirect rendering, this holds the mesh and gameobject indexes, and material index.

        Modelmatrix is empty and filled on the GPU compute pass when compute is enabled
        """
        offset = 0
        _object_ssbo        = self.object_ssbo
        _object_buffer      = self.object_ssbo.buffer

        _gameobject_buffer  = self.comp_gameobject_matrices_ssbo.buffer
        _model_buffer       = self.model_ssbo.buffer

        object_idx = 0
        for i, uuid in enumerate(self.context.world.transforms.keys()):

            gid = self.comp_gameobject_matrices_map[uuid]

            obj = _gameobject_buffer[gid]
            
            if obj.enabled == 0: continue
            if obj.model_index < 0: continue

            model = _model_buffer[obj.model_index]

            for n in range(0, model.nodeCount):
                meshNodeMatrixId = model.nodeOffset + n

                _object_buffer[object_idx].meshNodeMatrixId = meshNodeMatrixId
                _object_buffer[object_idx].gameObjectMatrixId = gid
                _object_buffer[object_idx].material = 0

                # done in compute shader
                #_object_buffer[offset].model[:] = np.asarray(item.matrix, dtype=np.float32).reshape(16)

                self.object_map[(obj.model_index, n, uuid)] = object_idx
                object_idx += 1 

        _object_ssbo.upload( object_idx )

        return object_idx

    def _upload_indirect_buffer( self, batches : dict[tuple[int, int], list[DrawItem]], num_draw_items : int  ):
        """
        Create the shared indirect and instances buffer and optional: 
        *draw ranges with insufficient GlExtenstion support.

        These buffers are used to for glMultiDrawElementsIndirect drawcall(s) later.
        """
        base_instance : int = 0
        _batch_ssbo         = self.batch_ssbo
        _batch_buffer       = self.batch_ssbo.buffer

        _instances_ssbo     = self.instances_ssbo
        _instances_buffer   = self.instances_ssbo.buffer
        _instances_offset   = 0

        # CPU driven indirect buffer only
        if not self.context.renderer.USE_INDIRECT_COMPUTE:
            draw_ranges : dict[(int, int), (int, int)] = {}
            _indirect_ssbo        = self.indirect_ssbo
            _indirect_buffer      = self.indirect_ssbo.buffer

        # build and upload the buffers
        for offset, ((model_index, mesh_index), batch) in enumerate(batches.items()):

            # build the instance buffer
            for _object in batch:
                object_key = (model_index, mesh_index, _object.uuid)
                _instances_buffer[_instances_offset].ObjectId = self.object_map[object_key] if object_key in self.object_map else 0
                _instances_offset += 1

            # GPU driven indirect buffer (compute shader)
            if self.context.renderer.USE_INDIRECT_COMPUTE:
                mesh_id = (model_index, mesh_index)
            
                _batch_buffer[offset].instanceCount     = len(batch)
                _batch_buffer[offset].baseInstance      = base_instance
                _batch_buffer[offset].meshNodeMatrixId  = int(self.comp_meshnode_matrices_map[mesh_id]) if mesh_id in self.comp_meshnode_matrices_map else 0
            
                base_instance += len(batch)
            
            # CPU driven indirect buffer
            else:
                mesh : "Models.Mesh" = self.context.models.model_mesh[model_index][mesh_index]
                #print(f"Mesh {model_index},{mesh_index}: instancecount={len(batch)} baseVertex={mesh['baseVertex']}, firstIndex={mesh['firstIndex']}, num_indices={mesh['num_indices']}")
    
                _indirect_buffer[offset].count          = mesh["num_indices"]
                _indirect_buffer[offset].instanceCount  = len(batch)
                _indirect_buffer[offset].firstIndex     = mesh["firstIndex"]
                _indirect_buffer[offset].baseVertex     = mesh["baseVertex"]
                _indirect_buffer[offset].baseInstance   = base_instance

                # support for indirect, bindless, and shared VAO is enabled.
                # allowing to render the scene in one indirect instanced drawcall
                if self.context.renderer.USE_GPU_DRIVEN_RENDERING:
                    draw_ranges = None

                # Indirect rendering per mesh: batches group game objects sharing the same mesh,
                # but VAO and material bindings are performed per batch on the CPU.
                else:
                    draw_ranges[(model_index, mesh_index)] = (offset, len(batch))

                base_instance += len(batch)

        # GPU driven indirect buffer
        if self.context.renderer.USE_INDIRECT_COMPUTE:
            _batch_ssbo.upload( len(batches) )

            self.context.renderer._dispatch_compute_indirect_sbbo( len(batches) )
            _instances_ssbo.upload( _instances_offset )
            return None

        # CPU driven indirect buffer
        _indirect_ssbo.upload( len(batches) )
        _instances_ssbo.upload( _instances_offset )

        return draw_ranges