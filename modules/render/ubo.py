from typing import TYPE_CHECKING, TypedDict

import os
import struct

from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *
from OpenGL.GL.ARB.bindless_texture import *

import numpy as np
import enum

from modules.shader import Shader
from modules.render.types import DrawItem, MatrixItem

if TYPE_CHECKING:
    from main import EmberEngine
    from modules.renderer import Renderer
    from modules.models import Models
    from gameObjects.gameObject import GameObject

import ctypes
from collections import defaultdict
import uuid as uid

class DrawElementsIndirectCommand(ctypes.Structure):
    _fields_ = [
        ("count",         ctypes.c_uint),
        ("instanceCount", ctypes.c_uint),
        ("firstIndex",    ctypes.c_uint),
        ("baseVertex",    ctypes.c_uint),
        ("baseInstance",  ctypes.c_uint),
    ]

class DrawBlock(ctypes.Structure):
    _fields_ = [
        ("model",               ctypes.c_float * 16),
        ("material",            ctypes.c_int),
        ("meshNodeMatrixId",    ctypes.c_int),
        ("gameObjectMatrixId",  ctypes.c_int),
        ("pad2",                ctypes.c_int),
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


    class GpuBuffer:
        def __init__( self, max_elements, element_type, target ):
            self.max_elements   = max_elements
            self.element_type   = element_type
            self.target         = target

            if isinstance(element_type, int):
                # flat float array
                self.element_size = element_type      # number of floats per element
                self.buffer = (ctypes.c_float * (max_elements * self.element_size))()
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

    def initialize( self ):
        # context
        self.renderer   : 'Renderer' = self.context.renderer

        #
        # general
        #
        self.ubo_lights             : UBO.LightUBO     = UBO.LightUBO( self.renderer.general, "Lights" )
        if self.renderer.USE_BINDLESS_TEXTURES:
            self.ubo_materials      : UBO.MaterialUBOBindless  = UBO.MaterialSSBOBindless()
        else:
            self.ubo_materials      : UBO.MaterialUBO  = UBO.MaterialUBO( self.renderer.general, "Materials" )

        #
        # indirect
        #
        if self.renderer.USE_INDIRECT:
            MAX_MATRICES = 10000
            MAX_DRAWS = 10000

            # compute
            self.comp_meshnode_matrices_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_MATRICES,
                 element_type   = 16, # 64 bytes mat4 item buffer
                 target         = GL_SHADER_STORAGE_BUFFER
            )

            self.comp_gameobject_matrices_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_MATRICES,
                 element_type   = 16, # 64 bytes mat4 item buffer
                 target         = GL_SHADER_STORAGE_BUFFER
            )

            # render
            self.draw_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_DRAWS,
                 element_type   = DrawBlock,
                 target         = GL_SHADER_STORAGE_BUFFER
            )

            self.indirect_ssbo : UBO.GpuBuffer = UBO.GpuBuffer(
                 max_elements   = MAX_DRAWS,
                 element_type   = DrawElementsIndirectCommand,
                 target         = GL_DRAW_INDIRECT_BUFFER
            )

    #
    # general 330 compat, 
    # TODO: Maybe merge with GpuBuffer eventually?
    #
    class MaterialSSBOBindless:
        MAX_MATERIALS = 2096
        # std430 layout: 5 uint64_t, 1 int, 1 uint padding = 48 bytes per material
        STRUCT_LAYOUT = struct.Struct("QQQQQiI")

        class Material(TypedDict):
            albedo          : int
            normal          : int
            phyiscal        : int
            emissive        : int
            opacity         : int
            hasNormalMap    : int

        def __init__( self ):
            self._dirty = True

            self.data = bytearray()

            self.ubo = glGenBuffers(1)
            glBindBuffer( GL_SHADER_STORAGE_BUFFER, self.ubo )

            total_size = self.MAX_MATERIALS * self.STRUCT_LAYOUT.size
            glBufferData( GL_SHADER_STORAGE_BUFFER, total_size, None, GL_DYNAMIC_DRAW )
            glBindBuffer( GL_SHADER_STORAGE_BUFFER, 0 )

        def update(self, materials: list[dict]):
            num_materials = min(len(materials), self.MAX_MATERIALS)
            self.data = bytearray()

            # u_materials
            for mat in materials[:num_materials]:
                self.data += self.STRUCT_LAYOUT.pack(
                    mat["albedo"],
                    mat["normal"],
                    mat["phyiscal"],
                    mat["emissive"],
                    mat["opacity"],
                    mat.get("hasNormalMap", 0),
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

        class Material(TypedDict):
            albedo          : int   # skipped in non-bindless
            normal          : int   # skipped in non-bindless
            phyiscal        : int   # skipped in non-bindless
            emissive        : int   # skipped in non-bindless
            opacity         : int   # skipped in non-bindless
            hasNormalMap    : int

        def __init__(self, 
                     shader : Shader, 
                     block_name     : str ="Material"
            ):
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

        def update( self, materials ):
            num_materials = min(len(materials), self.MAX_MATERIALS)

            self.data = bytearray()

            # u_materials
            for mat in materials[:num_materials]:

                self.data += self.STRUCT_LAYOUT.pack(
                    mat["hasNormalMap"], 0.0, 0.0, 0.0
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

        def update( self, lights ):
            num_lights = min(len(lights), self.MAX_LIGHTS)

            self.data = bytearray()

            # u_num_lights
            self.data += struct.pack("I 3I", num_lights, 0, 0, 0)

            # u_lights
            for light in lights[:num_lights]:
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
            materials : list[UBO.MaterialUBO.Material] = []

            for i, mat in enumerate(self.context.materials.materials):
                materials.append( UBO.MaterialUBO.Material(
                    # bindless
                    albedo          = self.context.images.texture_to_bindless[ mat.get( "albedo",     self.context.images.defaultImage)     ],       
                    normal          = self.context.images.texture_to_bindless[ mat.get( "normal",     self.context.images.defaultNormal)    ],       
                    phyiscal        = self.context.images.texture_to_bindless[ mat.get( "phyiscal",   self.context.images.defaultRMO)       ],       
                    emissive        = self.context.images.texture_to_bindless[ mat.get( "emissive",   self.context.images.blackImage)       ],       
                    opacity         = self.context.images.texture_to_bindless[ mat.get( "opacity",    self.context.images.whiteImage)       ],
                        
                    # both bindless and non-bindless paths
                    hasNormalMap    = mat.get( "hasNormalMap", 0 ),
                )
            )

            self.ubo_materials.update( materials )

    def _upload_lights_ubo( self, sun : "GameObject" ) -> None:
        """Build a UBO of lights, rebuilds every frame (currently)
        
        :param sun: The sun GameObject, light is excluded from UBO
        :type sun: GameObject
        """
        lights : list[UBO.LightUBO.Light] = []

        for uuid in self.context.world.lights.keys():
            obj : "GameObject" = self.context.world.gameObjects[uuid]

            if not obj.hierachyActive() or obj is sun:
                continue

            if not self.renderer.game_runtime and not obj.hierachyVisible():
                continue

            lights.append( UBO.LightUBO.Light(
                origin      = obj.transform.position,
                rotation    = obj.transform.rotation,


                color       = obj.light.light_color,
                radius      = obj.light.radius,
                intensity   = obj.light.intensity,
                t           = obj.light.light_type
            ) )

        self.ubo_lights.update( lights )

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

        offset = 0
        for model_index, items in self.comp_meshnode_matrices_nested.items():
            for item in items:
                self.comp_meshnode_matrices_ssbo.buffer[offset*16:(offset+1)*16] = item.matrix.flatten()
            
                # create a map
                self.comp_meshnode_matrices_map[(model_index, item.mesh_index)] = offset
                offset += 1

        # upload to SSBO
        self.comp_meshnode_matrices_ssbo.upload( offset )

        self.comp_meshnode_matrices_dirty = False   

    def _upload_comp_gameobject_matrices_map_ssbo( self ):
        """Build a SSBO with all gameObjects world matrices
        
            Still happens per frame.
        
        """
        # clear the mapping table, it is rebuilt.
        self.comp_gameobject_matrices_map = {}

        offset = 0
        for uuid, transform in self.context.world.transforms.items():
            self.comp_gameobject_matrices_ssbo.buffer[offset*16:(offset+1)*16] = transform.world_model_matrix.flatten()

            # create a map
            self.comp_gameobject_matrices_map[uuid] = offset
            offset += 1

        # upload to SSBO
        self.comp_gameobject_matrices_ssbo.upload( offset )

    def _build_batched_draw_list( self, _draw_list : list[DrawItem] ) -> dict[tuple[int, int], list[DrawItem]]:
        """Convert draw_list to a grouped list per model:mesh(node) used for indirect batching"""
        batches = {}

        for item in _draw_list:
            key = (item.model_index, item.mesh_index)

            if key not in batches:
                batches[key] = []

            batches[key].append(item)

        return batches, len(_draw_list)

    def _upload_draw_blocks_ssbo( self, batches : dict[tuple[int, int], list[DrawItem]], num_draw_items : int ):
        """
        Create the per draw ssbo used for indirect rendering
        For indirect rendering, this holds the mesh and gameobject indexes, and material index.

        Modelmatrix is empty and filled on the GPU compute pass when compute is enabled
        """
        i = 0
        for (model_index, mesh_index), batch in batches.items():
            mesh : "Models.Mesh" = self.context.models.model_mesh[model_index][mesh_index]

            for item in batch:
                mesh_id = (model_index, item.mesh_index)

                if item.uuid:
                    #self.draw_ssbo.buffer[i].model[:]             = np.zeros((16,), dtype=np.float32)
                    self.draw_ssbo.buffer[i].meshNodeMatrixId     = int(self.comp_meshnode_matrices_map[mesh_id]) if mesh_id in self.comp_meshnode_matrices_map else 0
                    self.draw_ssbo.buffer[i].gameObjectMatrixId   = int(self.comp_gameobject_matrices_map[item.uuid])
                else:
                    # probably never hits anymore and can be deprecated?
                    self.draw_ssbo.buffer[i].model[:]             = np.asarray(item.matrix, dtype=np.float32).reshape(16)
                
                self.draw_ssbo.buffer[i].material             = mesh["material"]
                i += 1

        self.draw_ssbo.upload( num_draw_items )

    def _upload_indirect_buffer( self, batches : dict[tuple[int, int], list[DrawItem]], num_draw_items : int  ):
        """
        Create the shared indirect buffer and draw ranges dictionary, 
        This used to submit glMultiDrawElementsIndirect drawcalls later.
        """
        draw_offset = 0
        i = 0 
        draw_ranges : dict[(int, int), (int, int)] = {}

        for (model_index, mesh_index), batch in batches.items():
            mesh : "Models.Mesh" = self.context.models.model_mesh[model_index][mesh_index]
            start_offset = i

            for j in range(len(batch)):
                self.indirect_ssbo.buffer[i].count = mesh["num_indices"]
                self.indirect_ssbo.buffer[i].instanceCount = 1
                self.indirect_ssbo.buffer[i].firstIndex = 0
                self.indirect_ssbo.buffer[i].baseVertex = 0
                self.indirect_ssbo.buffer[i].baseInstance = draw_offset + j
                i += 1

            draw_ranges[(model_index, mesh_index)] = (start_offset, len(batch))
            draw_offset += len(batch)

        self.indirect_ssbo.upload( num_draw_items )

        return draw_ranges