from typing import TYPE_CHECKING, TypedDict

import os
import math
from OpenGL.arrays import returnPointer
from pygame.math import Vector2
from pyrr import matrix44, Matrix44, Vector3
import pygame
from pygame.locals import *

from imgui_bundle.python_backends.pygame_backend import imgui, PygameRenderer
from imgui_bundle import icons_fontawesome_6 as fa

from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *
from OpenGL.GL.ARB.bindless_texture import *

import struct

import numpy as np
import enum

from modules.settings import Settings
from modules.project import ProjectManager
from modules.render.shader import Shader
from modules.camera import Camera
from modules.scene import SceneManager

import pybullet as p

if TYPE_CHECKING:
    from main import EmberEngine
    from modules.models import Models

    from gameObjects.gameObject import GameObject

from dataclasses import dataclass, field


import ctypes
from collections import defaultdict
import uuid as uid

from modules.render.types import DrawItem, MatrixItem
from modules.render.ubo import UBO, DrawElementsIndirectCommand

class Renderer:
    class GameState_(enum.IntEnum):
        """Runtime states"""
        none        = 0             # (= 0)
        running     = enum.auto()   # (= 1)
        paused      = enum.auto()   # (= 2)

    """The rendering backend"""
    def __init__( self, context ):
        """Renderer backend, creating window instance, openGL, FBO's, shaders and rendertargets

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        self.context    : 'EmberEngine' = context
        self.camera     : Camera = context.camera
        self.settings   : Settings = context.settings
        self.project    : ProjectManager = context.project

        # window
        self.display_size : imgui.ImVec2 = imgui.ImVec2( 1500, 1000 )
        self.viewport_size : imgui.ImVec2 = imgui.ImVec2( 600, 800 )
        self.create_instance()

        # imgui
        imgui.create_context()
        io = imgui.get_io()
        io.display_size = imgui.ImVec2(self.display_size.x, self.display_size.y)

        # exported apps do not use imgui docking
        if not self.settings.is_exported:
            io.config_flags |= imgui.ConfigFlags_.docking_enable
            io.config_flags |= imgui.ConfigFlags_.viewports_enable

        # fonts
        io.fonts.add_font_default()

        _font_cfg = imgui.ImFontConfig()
        _font_cfg.merge_mode = True
        _font_cfg.pixel_snap_h = True
        _icon_ranges = [fa.ICON_MIN_FA, fa.ICON_MAX_FA, 0]
        _font_file : str = str(os.path.join(self.settings.engineAssets, "gui/fonts/Font_Awesome_6_Free-Solid-900.otf"))
        io.fonts.add_font_from_file_ttf(
            _font_file, 12.0, _font_cfg
        )

        self.render_backend = PygameRenderer()

        # application
        self.paused = False
        self.running = True
        self.ImGuiInput = True # True: imgui, Fase: Game
        self.ImGuiInputFocussed = False # True: imgui, Fase: Game

        # game runtime
        self._game_state = self.GameState_.none
        self.game_start = False
        self.game_stop = False

        # frames and timing
        self.clock = pygame.time.Clock()
        self.DELTA_SHIFT = 1000
        self.framenum = 0
        self.frameTime = 0
        self.deltaTime = 0

        # init mouse movement and center mouse on screen
        self.screen_center = [self.screen.get_size()[i] // 2 for i in range(2)]
        pygame.mouse.set_pos( self.screen_center )

        # shaders
        self.shader : Shader = None

        # editor
        self.editor_grid_vao = None
        self.editor_axis_vao = None

        self.renderMode = 0
        self.renderModes : str = [
	        "Final Image", 
	        "Diffuse", 
	        "Specular", 
	        "Roughness", 
	        "Ambient Occlusion", 
	        "Normals", 
	        "Normals + Normalmap",  
	        "Light direction",
	        "View direction",
	        "Tangents",
	        "Light color",
	        "Ambient color",
	        "Reflectance",
	        "Attenuation",
	        "H - Half vector lightdir/viewdir",
	        "Fd - CalcDiffuse",
	        "Fs - CalcSpecular",
	        "NdotE - Normal dot View direction",
	        "NdotL - Normal dot Light direction",
	        "LdotH - Light direction dot Half vector",
	        "NdotH - Normal dor Half vector",
	        "VdotH - View direction dot Half vector",
	        "IBL Contribution",
            "Emissive",
            "Opacity",
            "Light Contribution",
            "View Origin",
            "Shadowmap",
            ]

        # UBO / SSBO
        self.ubo : UBO = UBO( context )

        # FBO
        self.current_fbo = None;
        self.create_screen_vao()

        self.shadowmap_fbo = self.create_shadowmap_fbo( Vector2( 4096, 4096 ) )
        self.main_fbo = self.create_fbo_with_depth( Vector2( int(self.display_size.x), int(self.display_size.y) ) )
        self.fog_fbo = self.create_color_fbo( self.main_fbo["size"] )

        if self.settings.msaaEnabled:
            self.main_fbo["resolve"] = self.create_resolve_fbo( self.main_fbo["size"] )
            self.main_fbo['output'] = self.main_fbo["resolve"]["color_image"]
        else:
            self.main_fbo['output'] = self.main_fbo["color_image"]

        glClearColor(0.0, 0.0, 0.0, 1)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.setup_projection_matrix( 
            size = self.display_size 
        )

        # identity matrix
        self.identity_matrix : Matrix44 = Matrix44.identity()

        # physics
        self._initPhysics()

        # draw list
        self.draw_list : list[DrawItem] = []


    @property
    def game_state( self ) -> GameState_:
        """Get the current game state.
        
        :return: The current set enum integer
        :rtype: GameState_
        """
        return self._game_state

    @game_state.setter
    def game_state( self, new_state : GameState_ ):
        """Set a new game state, and trigger start/stop events."""
        if self._game_state is new_state:
            return

        match new_state:
            case self.GameState_.none: 
                self.game_stop = True
                self.camera.camera = None   # editor default

            case self.GameState_.running:
                if not self.game_paused:
                    self.game_start = True
                    self.camera.camera = self.context.scene.getCamera()

        self._game_state = new_state

    @property
    def game_runtime( self ) -> bool:
        """"Check current state of the runtime

        :return: True if GameState_.running or GameState_.paused
        :rtype: bool
        """
        return self._game_state is self.GameState_.running or self._game_state is self.GameState_.paused

    @property
    def game_running( self ) -> bool:
        """"Check current state of the runtime

        :return: True if GameState_.running
        :rtype: bool
        """
        return self._game_state is self.GameState_.running

    @property
    def game_paused( self ) -> bool:
        """"Check current state of the runtime

        :return: True if GameState_.paused
        :rtype: bool
        """
        return self._game_state is self.GameState_.paused

    @staticmethod
    def check_opengl_error():
        err = glGetError()
        if err != GL_NO_ERROR:
            print(  f"OpenGL Error: {err}" )

    @staticmethod
    def print_opengl_version() -> None:
        version = glGetString(GL_VERSION)
        renderer = glGetString(GL_RENDERER)
        vendor   = glGetString(GL_VENDOR)
        glsl_ver = glGetString(GL_SHADING_LANGUAGE_VERSION)

        print("OpenGL Version:", version.decode())
        print("Renderer:", renderer.decode())
        print("Vendor:", vendor.decode())
        print("GLSL Version:", glsl_ver.decode())

        return version.decode(), renderer.decode(), vendor.decode(), glsl_ver.decode()

    def get_window_title(self) -> str:
        return self.project.meta.get("name") if self.settings.is_exported else self.settings.application_name

    def set_supported_opengl_extensions( self ) -> None:
        num_ext = glGetIntegerv( GL_NUM_EXTENSIONS )

        return [
            glGetStringi( GL_EXTENSIONS, i ).decode()
            for i in range(num_ext)
        ]

    def has_extension( self, extension : str ) -> bool:

        # debugging
        if self.RENDERDOC:
            return True

        if extension in self.gl_extensions:
            return True

        return False

    def create_instance( self ) -> None:
        """Create the window and instance with openGL"""
        pygame.init()
        pygame.display.set_caption( self.get_window_title() )
   
        # Request this OpenGL version
        request_gl_version = (4, 6)

        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, request_gl_version[0])
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, request_gl_version[1])
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, 1)

        if self.settings.msaaEnabled:
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

        display = pygame.display.Info()
        self.display_size = imgui.ImVec2(display.current_w, display.current_h)

        # this is a bit of a hack to get windowed fullscreen?
        self.display_size -= imgui.ImVec2( 0.0, 80.0 );

        self.screen = pygame.display.set_mode( 
            size        = self.display_size, 
            flags       = RESIZABLE | DOUBLEBUF | OPENGL,
            vsync       = 0
           )

        # Retrieve the OpenGL version used? (doubts)
        gl_version, renderer, vendor, glsl_version = Renderer.print_opengl_version()
        major, minor = map(int, gl_version.split('.')[0:2])

        # Retrieve supported OpenGL extensions 
        # https://opengl.gpuinfo.org/listextensions.php
        self.RENDERDOC = False
        self.gl_extensions = self.set_supported_opengl_extensions()
 
        # renderer configuration
        # OpenGL ver. < 4.6.0 will fallback to simple rendering and GLSL 330 core features for backwards compat.
        supports_gl_460 = (major, minor) >= (4, 6)
        #
        self.USE_BINDLESS_TEXTURES  : bool = supports_gl_460 and self.has_extension("GL_ARB_bindless_texture") 
        self.USE_INDIRECT           : bool = supports_gl_460  
        self.SHARED_VAO             : bool = supports_gl_460
        
        # do not change
        self.USE_GPU_DRIVEN_RENDERING : bool = self.USE_INDIRECT and self.SHARED_VAO and self.USE_BINDLESS_TEXTURES
        self.USE_INDIRECT_COMPUTE : bool = True and self.USE_GPU_DRIVEN_RENDERING
        self.USE_FULL_GPU_DRIVEN : bool = True and self.USE_INDIRECT_COMPUTE

        # RenderDoc debug overrrides
        if self.RENDERDOC:
            # bindless not supported, 
            # will break rendering but ok to inspect dispatches
            self.USE_BINDLESS_TEXTURES = False  

        if supports_gl_460:
            print( "OpenGL 4.6.0 is supported, use Indirect and Bindless rendering" )
        else:
            print( "OpenGL 4.6.0 is NOT supported, fallback to non-bindless and non-indirect")

        # frozen-exported set fullscreen here ..
        #if self.settings.is_exported:
            #self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            #pygame.display.toggle_fullscreen()

        if self.settings.msaaEnabled:
            glEnable( GL_MULTISAMPLE )
     
    def shutdown( self ) -> None:
        """Quit the application"""
        self.render_backend.shutdown()
        pygame.quit()

    def create_screen_vao( self ):
        """Create vertex buffer for 2d operations like gamma, msaa resolve"""
        quad = np.array([
            # positions        # texCoords
            -1.0,  1.0,  0.0, 1.0,
            -1.0, -1.0,  0.0, 0.0,
             1.0, -1.0,  1.0, 0.0,
            -1.0,  1.0,  0.0, 1.0,
             1.0, -1.0,  1.0, 0.0,
             1.0,  1.0,  1.0, 1.0,
        ], dtype='float32')

        self.screenVAO = glGenVertexArrays(1)
        self.screenVBO = glGenBuffers(1)

        glBindVertexArray( self.screenVAO )

        size = quad.itemsize
        stride = size * 4

        glBindBuffer(GL_ARRAY_BUFFER, self.screenVBO )
        glBufferData(GL_ARRAY_BUFFER, quad.nbytes, quad, GL_STATIC_DRAW)

        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, None)
        glEnableVertexAttribArray(0)

        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(2 * size))
        glEnableVertexAttribArray(1)

        # Unbind VBO and VAO
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

    def create_color_fbo( self, size: Vector2, hdr=True ):
        fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)

        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)

        internal = GL_RGBA16F if hdr else GL_RGBA8
        glTexImage2D( GL_TEXTURE_2D, 0, internal, int(size.x), int(size.y), 0, GL_RGBA, GL_FLOAT, None )

        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )

        glFramebufferTexture2D( GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0 )

        assert glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        return {
            "fbo"           : fbo, 
            "color_image"   : texture, 
            "size"          : size
        }

    def create_resolve_fbo( self, size: Vector2 ):
        fbo = glGenFramebuffers(1)
        glBindFramebuffer( GL_FRAMEBUFFER, fbo )

        # Create the image attachment
        color_texture = glGenTextures( 1 )
        depth_texture = glGenTextures( 1 )

        # color
        glBindTexture( GL_TEXTURE_2D, color_texture)
        glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA16F, int(size.x), int(size.y), 0, GL_RGBA, GL_FLOAT, None )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )
        glFramebufferTexture2D( GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, color_texture, 0 )

        # depth (postprocessing, need guard?)
        glBindTexture( GL_TEXTURE_2D, depth_texture )
        glTexImage2D( GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT32F, int(size.x), int(size.y), 0, GL_DEPTH_COMPONENT, GL_FLOAT, None )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )
        glFramebufferTexture2D( GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth_texture, 0 )

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise Exception("Resolve FBO is not complete!")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        return {
            "fbo"           : fbo, 
            "color_image"   : color_texture, 
            "depth_image"   : depth_texture
        }

    def resolve_multisample( self ):
        width, height = int(self.main_fbo["size"].x), int(self.main_fbo["size"].y)

        glBindFramebuffer( GL_READ_FRAMEBUFFER, self.main_fbo["fbo"] )
        glBindFramebuffer( GL_DRAW_FRAMEBUFFER, self.main_fbo["resolve"]["fbo" ])

        # color
        glReadBuffer( GL_COLOR_ATTACHMENT0 )
        glDrawBuffer( GL_COLOR_ATTACHMENT0 )
        glBlitFramebuffer(
            0, 0, width, height,  # src
            0, 0, width, height,  # dst
            GL_COLOR_BUFFER_BIT,
            GL_NEAREST
        )

        # depth

        glBindFramebuffer( GL_READ_FRAMEBUFFER, self.main_fbo["fbo"] )
        glBindFramebuffer( GL_DRAW_FRAMEBUFFER, self.main_fbo["resolve"]["fbo"] )
        glBlitFramebuffer(
            0, 0, width, height,
            0, 0, width, height,
            GL_DEPTH_BUFFER_BIT,
            GL_NEAREST
        )

        # Unbind
        glBindFramebuffer(GL_READ_FRAMEBUFFER, 0 )
        glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0 )

    def create_fbo_with_depth( self, size : Vector2 ):
        """Create the a framebuffer (FBO) with a bound image attachment.
        Adjust image attachment properties based on MSAA state. 

        :param size: The dimensions of the texture
        :type size: Vector2
        :return: The uid of the texture in GPU memory
        :rtype: uint32/uintc
        """
        fbo = glGenFramebuffers( 1 )
        glBindFramebuffer( GL_FRAMEBUFFER, fbo )
        
        # Create the image attachment
        color_texture = glGenTextures( 1 )
        depth_texture = glGenTextures( 1 )

        # color
        if self.settings.msaaEnabled:
            glEnable( GL_MULTISAMPLE );

            glBindTexture( GL_TEXTURE_2D_MULTISAMPLE, color_texture )
            glTexImage2DMultisample( GL_TEXTURE_2D_MULTISAMPLE, self.settings.msaa, GL_RGBA16F, int(size.x), int(size.y), GL_TRUE )
            glFramebufferTexture2D( GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D_MULTISAMPLE, color_texture, 0 )
        else:
            glBindTexture( GL_TEXTURE_2D, color_texture )
            glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA16F, int(size.x), int(size.y), 0, GL_RGBA, GL_FLOAT, None )
            glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR )
            glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )
            glFramebufferTexture2D( GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, color_texture, 0 )

        # depth
        if self.settings.msaaEnabled:
            glBindTexture( GL_TEXTURE_2D_MULTISAMPLE, depth_texture )
            glTexImage2DMultisample( GL_TEXTURE_2D_MULTISAMPLE, self.settings.msaa, GL_DEPTH_COMPONENT32F, int(size.x), int(size.y), GL_TRUE )
            glFramebufferTexture2D( GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D_MULTISAMPLE, depth_texture, 0 )

        else:
            # single-sample depth
            glBindTexture(GL_TEXTURE_2D, depth_texture)
            glTexImage2D( GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT32F, int(size.x), int(size.y), 0, GL_DEPTH_COMPONENT, GL_FLOAT, None )
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)

            glFramebufferTexture2D( GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth_texture, 0 )

        # Check if the FBO is complete
        framebuffer_status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
        if framebuffer_status != GL_FRAMEBUFFER_COMPLETE:
            if framebuffer_status == GL_FRAMEBUFFER_UNSUPPORTED:
                print("Framebuffer is unsupported.")
            elif framebuffer_status == GL_FRAMEBUFFER_INCOMPLETE_ATTACHMENT:
                print("Framebuffer incomplete: Attachment is not complete.")
            elif framebuffer_status == GL_FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT:
                print("Framebuffer incomplete: Missing attachment.")
            elif framebuffer_status == GL_FRAMEBUFFER_INCOMPLETE_DRAW_BUFFER:
                print("Framebuffer incomplete: Missing draw buffer.")
            elif framebuffer_status == GL_FRAMEBUFFER_INCOMPLETE_READ_BUFFER:
                print("Framebuffer incomplete: Missing read buffer.")
            else:
                print("Framebuffer incomplete: Unknown error.")
    
        glBindFramebuffer( GL_FRAMEBUFFER, 0 )

        return {
            "fbo"           : fbo, 
            "color_image"   : color_texture, 
            "depth_image"   : depth_texture,
            "size"          : size
        }
    
    def create_shadowmap_fbo( self, size : Vector2 ) -> None:
        fbo = glGenFramebuffers(1)
        glBindFramebuffer( GL_FRAMEBUFFER, fbo )

        depth_texture = glGenTextures(1)

        glBindTexture( GL_TEXTURE_2D, depth_texture )
        glTexImage2D( GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT32F, int(size.x), int(size.y), 0, GL_DEPTH_COMPONENT, GL_FLOAT, None )

        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER )
        glTexParameterfv( GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, [1, 1, 1, 1] )

        glFramebufferTexture2D( GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depth_texture, 0 )

        glDrawBuffer( GL_NONE )
        glReadBuffer( GL_NONE )

        assert glCheckFramebufferStatus(GL_FRAMEBUFFER) == GL_FRAMEBUFFER_COMPLETE
        glBindFramebuffer( GL_FRAMEBUFFER, 0 )

        return {
            "fbo"           : fbo, 
            "depth_image"   : depth_texture,
            "size"          : size
        }

    def bind_fbo( self, fbo, clear_bits : int = GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT ) -> None:
        """Bind a framebuffer (FBO) to the command buffer.
        
        :param fbo: The framebuffer uid
        :type fbo: uint32/uintc
        """
        # if rendering to a FBO, stop ..
        self.unbind_fbo()

        self.current_fbo = fbo
        glBindFramebuffer( GL_FRAMEBUFFER, self.current_fbo["fbo"] )
        glViewport( 0, 0, int(self.current_fbo["size"].x), int(self.current_fbo["size"].y) )
        glClear( clear_bits )
        glEnable(GL_DEPTH_TEST);

    def unbind_fbo( self ) -> None:
        """Stop rending to current fbo, and unbind framebuffer (FBO)"""
        if self.current_fbo:
            self.current_fbo = None

        glBindFramebuffer( GL_FRAMEBUFFER, 0 )

    def render_fbo( self, fbo ):
        """Render a framebuffer to the swapchain using the 2d VAO

        :param fbo: The framebuffer uid
        :type fbo: uint32/uintc
        """
        self.use_shader( self.gamma )

        glBindVertexArray( self.screenVAO )
        glDisable(GL_DEPTH_TEST);

        glActiveTexture( GL_TEXTURE0 )

        _texture_type = GL_TEXTURE_2D_MULTISAMPLE if self.settings.msaaEnabled else GL_TEXTURE_2D
        glBindTexture( _texture_type, fbo )

        glUniform1i(glGetUniformLocation( self.shader.program, "screenTexture" ), 0)
        glDrawArrays(GL_TRIANGLES, 0, 6)

        glBindVertexArray(0)

    #
    # shader
    #
    def use_shader( self, shader : Shader ) -> None:
        """Bind a shader program to the command buffer

        :param shader: the shader object containing the program
        :type shader: Shader
        """
        self.shader : Shader = shader
        glUseProgram( self.shader.program )

    def create_shaders( self ) -> None:
        """Create the GLSL shaders used for the editor and general pipeline"""
        self.general            = Shader( self.context, "general", templated = True )
        self.skybox             = Shader( self.context, "skybox" )
        self.skybox_proc        = Shader( self.context, "skybox_proc" )
        self.gamma              = Shader( self.context, "gamma" )
        self.color              = Shader( self.context, "color" )
        self.resolve            = Shader( self.context, "resolve" ) # deprecated
        self.shadowmap          = Shader( self.context, "shadowmap", templated = True )
        self.fog                = Shader( self.context, "fog", templated = True )

        self.object_modelmatrix = Shader( self.context, "object_modelmatrix", compute=True )
        self.indirect           = Shader( self.context, "indirect", compute=True )

        # Full GPU driven
        self.gpu_driven_batch_counter       = Shader( self.context, "gpu_driven_batch_counter", compute=True )
        self.gpu_driven_batch_compact       = Shader( self.context, "gpu_driven_batch_compact", compute=True )
        self.gpu_driven_build_instances     = Shader( self.context, "gpu_driven_build_instances", compute=True )
        
        self.gpu_driven_build_object_buffer = Shader( self.context, "gpu_driven_build_object_buffer", compute=True )

    #
    # UBO / SSBO
    #

    
    #
    # editor visuals
    #
    def create_grid_vbo( self, size, spacing ):
        lines = []
        for i in np.arange(-size, size + spacing, spacing):
            # lines along Z
            lines.append([i, 0, -size])
            lines.append([i, 0, size])
            # lines along X
            lines.append([-size, 0, i])
            lines.append([size, 0, i])
        lines = np.array(lines, dtype=np.float32)
    
        # create VAO and VBO
        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)
    
        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, lines.nbytes, lines, GL_STATIC_DRAW)
    
        # position attribute
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 0, None)
    
        glBindVertexArray(0)

        return vao, len(lines)

    def create_axis_vbo( self, length: float = 1.0, centered: bool = False ):
        if centered:
            start = -length
            end   =  length
        else:
            start = 0.0
            end   = length

        vertices = np.array([
            # X axis : red
            start, 0.0,   0.0,
            end,   0.0,   0.0,

            # Y axis : green
            0.0,   start, 0.0,
            0.0,   end,   0.0,

            # Z axis : blue
            0.0,   0.0,   start,
            0.0,   0.0,   end,
        ], dtype=np.float32)

        vao = glGenVertexArrays(1)
        glBindVertexArray(vao)

        vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(
            GL_ARRAY_BUFFER,
            vertices.nbytes,
            vertices,
            GL_STATIC_DRAW
        )

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(
            0,              # location
            3,              # vec3
            GL_FLOAT,
            GL_FALSE,
            0,
            None
        )

        glBindVertexArray(0)

        return vao

    def create_editor_vaos( self ) -> None:
        self.editor_grid_vao, self.editor_grid_lines = self.create_grid_vbo( 
            size    = self.settings.grid_size, 
            spacing = self.settings.grid_spacing 
        )

        self.editor_axis_vao = self.create_axis_vbo(
            length      = 100.0,
            centered    = False
        )
    
    def draw_grid( self ):
        """Draw the horizontal grid to the framebuffer"""
        if not self.settings.drawGrid or not self.editor_grid_vao:
            return

        self.use_shader( self.color )

        glUniformMatrix4fv( self.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.projection )
        glUniformMatrix4fv( self.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.view )
        glUniformMatrix4fv( self.shader.uniforms['uMMatrix'], 1, GL_FALSE, self.identity_matrix )

        # color
        grid_color = self.settings.grid_color
        glUniform4f( self.shader.uniforms['uColor'],  grid_color[0],  grid_color[1], grid_color[2], 1.0 )
           
        glBindVertexArray( self.editor_grid_vao )
        glDrawArrays( GL_LINES, 0, self.editor_grid_lines )
        glBindVertexArray( 0 )

        # deprecated (26-12-2025)
        # switched to VAO
        #size = self.settings.grid_size
        #spacing = self.settings.grid_spacing
        #
        ## Draw the grid lines on the XZ plane
        #for i in np.arange(-size, size + spacing, spacing):
        #    # Draw lines parallel to Z axis
        #    glBegin(GL_LINES)
        #    glVertex3f(i, 0, -size)
        #    glVertex3f(i, 0, size)
        #    glEnd()
        #
        #    # Draw lines parallel to X axis
        #    glBegin(GL_LINES)
        #    glVertex3f(-size, 0, i)
        #    glVertex3f(size, 0, i)
        #    glEnd()

    def draw_axis( self, width : float = 3.0 ):
        """Draw axis lines. width and length can be adjust, also if axis is centered or half-axis"""
        if not self.settings.drawAxis or not self.editor_axis_vao:
            return
        
        depth_test_enabled  = glIsEnabled( GL_DEPTH_TEST )
        depth_write_mask    = glGetBooleanv( GL_DEPTH_WRITEMASK )

        glDisable( GL_DEPTH_TEST )
        glDepthMask( GL_FALSE )

        self.use_shader( self.color )
        glLineWidth( width )
        
        glUniformMatrix4fv( self.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.projection )
        glUniformMatrix4fv( self.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.view )
        glUniformMatrix4fv( self.shader.uniforms['uMMatrix'], 1, GL_FALSE, self.identity_matrix)

        glBindVertexArray( self.editor_axis_vao )

        # X axis : red
        glUniform4f( self.shader.uniforms['uColor'], 1, 0, 0, 1 )
        glDrawArrays( GL_LINES, 0, 2 )

        # Y axis : green
        glUniform4f( self.shader.uniforms['uColor'], 0, 1, 0, 1 )
        glDrawArrays(GL_LINES, 2, 2)

        # Z axis : blue
        glUniform4f( self.shader.uniforms['uColor'], 0, 0, 1, 1 )
        glDrawArrays( GL_LINES, 4, 2 )

        glBindVertexArray( 0 )
        glLineWidth( 1.0 )

        if depth_test_enabled:
            glEnable( GL_DEPTH_TEST )

        glDepthMask( depth_write_mask )

        # deprecated (26-12-2025)
        # switched to VAO
        #glLineWidth(width)
        #
        #self.use_shader(self.color)
        #
        ## bind projection matrix
        #glUniformMatrix4fv(self.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.projection)
        #
        ## viewmatrix
        #glUniformMatrix4fv(self.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.view)
        #
        ## modelamtrix identrity
        #glUniformMatrix4fv(self.shader.uniforms['uMMatrix'], 1, GL_FALSE, self.identity_matrix)
        #
        #
        #if centered:
        #    start = -length
        #    end   = +length
        #else:
        #    start = 0.0
        #    end   = length
        #
        ## X axis : red
        #glUniform4f(self.shader.uniforms['uColor'], 1.0, 0.0, 0.0, 1.0)
        #glBegin(GL_LINES)
        #glVertex3f(start, 0.0,   0.0)
        #glVertex3f(end,   0.0,   0.0)
        #glEnd()
        #
        ## Y axis : green
        #glUniform4f(self.shader.uniforms['uColor'], 0.0, 1.0, 0.0, 1.0)
        #glBegin(GL_LINES)
        #glVertex3f(0.0, start,   0.0)
        #glVertex3f(0.0, end,     0.0)
        #glEnd()
        #
        ## Z axis : blue
        #glUniform4f(self.shader.uniforms['uColor'], 0.0, 0.0, 1.0, 1.0)
        #glBegin(GL_LINES)
        #glVertex3f(0.0,   0.0, start)
        #glVertex3f(0.0,   0.0, end)
        #glEnd()
        #
        #glLineWidth(1.0)
    
    #
    # projection
    #
    def setup_projection_matrix( self, size : Vector2 = None ) -> None:
        """Setup the viewport and projection matrix using Matrix44

        :param size: The dimensions of the current viewport
        :type size: Vector2
        """
        if size:
            glViewport( 0, 0, int(size.x), int(size.y) )
            self.aspect_ratio = size.x / size.y

        self.projection = matrix44.create_perspective_projection_matrix( 
            fovy    = self.camera._fov, 
            aspect  = self.aspect_ratio, 
            near    = self.camera._near, 
            far     = self.camera._far
        )

    def toggle_input_state( self ) -> None:
        """Toggle input between application and viewport
        Toggling visibility and position of the mouse"""
        if self.ImGuiInput:
            self.ImGuiInput = False
            self.ImGuiInputFocussed = True # first frame hack
            pygame.event.set_grab(True)
            pygame.mouse.set_visible( False )
            pygame.mouse.set_pos( self.screen_center )
        else:
            self.ImGuiInput = True
            pygame.event.set_grab(False)
            pygame.mouse.set_visible( True )
            
    #
    # events
    #
    def editor_viewport_event_handler( self, event ):
        if self.game_runtime:
            return

        if not self.ImGuiInput:
            if event.type == pygame.KEYUP:
                if (event.key & pygame.KMOD_SHIFT) or (event.key & pygame.KMOD_LCTRL):
                    self.camera.velocity_mode = Camera.VelocityModifier_.normal

            elif event.type == pygame.KEYDOWN:
                if (event.mod & pygame.KMOD_SHIFT):
                    self.camera.velocity_mode = Camera.VelocityModifier_.speed_up

                elif (event.mod & pygame.KMOD_LCTRL):
                    self.camera.velocity_mode = Camera.VelocityModifier_.slow_down

        # toggle between viewport and gui input
        if event.type == pygame.MOUSEBUTTONUP:
            if not self.ImGuiInput and event.button == 3:
                self.toggle_input_state()

        elif event.type == pygame.MOUSEBUTTONDOWN :
            if self.ImGuiInput and event.button == 3:
                self.toggle_input_state()

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self.toggle_input_state()

    def event_handler( self ) -> None:
        """The main event handler for the application itself, handling input event states
        eg. Keep mouse hidden and in center of window when F1 is pressed to go into 3D space."""
        #mouse_moving = False

        for event in self.context.events.get():
            self.render_backend.process_event(event)

            if event.type == pygame.QUIT:
                self.running = False

            # handle events for editor viewport
            self.editor_viewport_event_handler( event )

            #if event.type == pygame.VIDEORESIZE:
                #screen_size = (event.w, event.h)
                #screen = pygame.display.set_mode(screen_size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
                #imgui.get_io().display_size = screen_size  # Update ImGui display size

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                if event.key == pygame.K_PAUSE or event.key == pygame.K_p:
                    if not self.ImGuiInput:
                        self.paused = not self.paused
                        pygame.mouse.set_pos( self.screen_center ) 

                # handle custom events
                if (event.mod & pygame.KMOD_CTRL):
                    if event.key == pygame.K_s:
                        self.context.cevent.add("save")

                    if event.key == pygame.K_c:
                        self.context.cevent.add("copy")

                    if event.key == pygame.K_v:
                        self.context.cevent.add("paste")

                    if event.key == pygame.K_z:
                        self.context.cevent.add("undo")

                    if event.key == pygame.K_y:
                        self.context.cevent.add("redo")

                if event.key == pygame.K_TAB:
                    self.context.cevent.add("tab")

        # deprecated and replaced with pygame.event.set_grab (08-01-2026)
            #if not self.paused: 
            #    if event.type == pygame.MOUSEMOTION:
            #        self.mouse_move = [event.pos[i] - self.screen_center[i] for i in range(2)]
            #        mouse_moving = True

        #if not self.ImGuiInput and not mouse_moving:
        #    pygame.mouse.set_pos( self.screen_center )

    #
    # physics
    #
    def _initPhysics( self ):
        """Initialize the pybullter physics engine and set gravity"""
        self.physics_client = p.connect(p.DIRECT)

        #p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, -10, 0)

        self.physics_step = 1.0 / 240.0
        p.setTimeStep(self.physics_step)

        #p.setPhysicsEngineParameter(
        #    numSolverIterations    = 10,
        #    numSubSteps            = 1
        #)

        self.physics_accumulator = 0.0
        # debug print list of available functions
        #for name in dir(p):
        #    if callable(getattr(p, name)):
        #        print(name)

    def _runPhysics( self ):
        """Run the step simulation when game is running"""
        if not self.game_running:
            return

        self.physics_accumulator += self.deltaTime
        max_steps = 8
        steps = 0

        while self.physics_accumulator >= self.physics_step and steps < max_steps:
            p.stepSimulation()
            self.physics_accumulator -= self.physics_step
            steps += 1

    #
    # shadowmap
    #
    def _compute_light_vp( self ) -> tuple[Matrix44, Matrix44]:
        """
        Compute light View and Projection matrices for directional light (sun)
        """

        _sun = self.context.scene.getSun()
        _sun_active = _sun and _sun.hierachyActive()

        if not self.game_runtime:
            _sun_active = _sun_active and _sun.hierachyVisible()

        if _sun_active:
            # Use world-space direction
            sun_position = Vector3(_sun.transform.local_position)
        else:
            sun_position = Vector3([0.0, 1.0, 0.0])

        if self.context.renderer.game_runtime:
            cam_pos = Vector3(self.context.camera._camera.transform._local_position)
        else:
            cam_pos = Vector3(self.camera.camera_pos)

        if self.context.renderer.game_runtime and self.camera._camera:
            cam_pos = Vector3(self.camera._camera.transform._local_position)
            # target point in front of camera
            cam_forward = (self.camera.place_object_in_front_of_another(cam_pos, self.camera._camera.transform._local_rotation_quat, 1.0) - cam_pos).normalized
        else:
            cam_pos = self.camera.camera_pos
            cam_forward = Vector3(self.camera.camera_front).normalized

        SHADOW_DISTANCE = 20.0
        up = Vector3([0.0, 1.0, 0.0])

        #shadow_center = cam_pos + cam_forward * (SHADOW_DISTANCE / 2)
        shadow_center = Vector3([0,0,0])
        light_dir = Vector3(shadow_center - sun_position).normalized
        light_pos = shadow_center - light_dir * SHADOW_DISTANCE
        light_view = matrix44.create_look_at(light_pos, shadow_center, up)

        SHADOW_EXTENT = 10.0
        NEAR_PLANE = 0.1
        FAR_PLANE = 100.0

        light_proj = matrix44.create_orthogonal_projection(
            left   = -SHADOW_EXTENT,
            right  =  SHADOW_EXTENT,
            bottom = -SHADOW_EXTENT,
            top    =  SHADOW_EXTENT,
            near   =  NEAR_PLANE,
            far    =  FAR_PLANE
        )

        return light_view, light_proj

    #
    # draw list
    #
    def addDrawItem( self, model_index : int, mesh_index : int, world_matrix : Matrix44, uuid ):
        self.draw_list.append( DrawItem( model_index, mesh_index, world_matrix, uuid ) )

    #
    # non-indirect (simple)
    #
    def submitDrawItem( self, model_index : int , mesh_index : int , model_matrix : Matrix44 ):
        """Render the mesh from a node

        :param model_index: The index of a loaded model
        :type model_index: int
        :param mesh_index:  The index of a mesh within that model
        :type mesh_index: int
        :param model_matrix: The transformation model matrix, used along with view and projection matrices
        :type model_matrix: matrix44
        """
        mesh : "Models.Mesh" = self.context.models.model_mesh[model_index][mesh_index]

        # bind material
        if "u_MaterialIndex" in self.shader.uniforms:
            glUniform1i( self.shader.uniforms['u_MaterialIndex'], int(mesh["material"]) )

        # directly bind 2D samplers in non-bindless mode:
        if not self.USE_BINDLESS_TEXTURES:
            self.context.materials.bind( mesh["material"] )

        glUniformMatrix4fv( self.shader.uniforms['uMMatrix'], 1, GL_FALSE, model_matrix )

        # Bind VAO that stores all attribute and buffer state
        # 
        # in case of shared VAO, this is not the right place. but ok for now
        # this mode is used in older system with shared VAO disabled
        # or for instant rendering which is only used for editor rendering (colliders)
        glBindVertexArray( mesh["vao_simple"].vao )

        if self.SHARED_VAO:
            glDrawElementsBaseVertex( GL_TRIANGLES, mesh["num_indices"], GL_UNSIGNED_INT,
                ctypes.c_void_p(mesh["firstIndex"] * 4),
                mesh["baseVertex"]
            )
        else:
            glDrawElements( GL_TRIANGLES, mesh["num_indices"], GL_UNSIGNED_INT, None )

    #
    # indirect
    #
    def addNodeMatrix( self, model_mesh : "Models.Mesh", model_index : int, mesh_index : int, matrix : Matrix44 ):
        """
        Indirect drawing only, collect mesh matrices for a model:node(mesh) after it loads

            Later, Upload the node(mesh) matrices in a single flat static SSBO with a mappings table (model_index, mesh_index) -> offset. 
            That way a GPU compute shader can compute the final model matrix for each gameObject

        """
        if model_index not in self.ubo.comp_meshnode_matrices_nested:
            self.ubo.comp_meshnode_matrices_nested[model_index] = []

        matrix_np = np.array(matrix, dtype=np.float32)
        min_l, max_l = model_mesh["aabb"]

        # 8 corners
        corners = np.array([
            [min_l[0], min_l[1], min_l[2], 1.0],
            [min_l[0], min_l[1], max_l[2], 1.0],
            [min_l[0], max_l[1], min_l[2], 1.0],
            [min_l[0], max_l[1], max_l[2], 1.0],
            [max_l[0], min_l[1], min_l[2], 1.0],
            [max_l[0], min_l[1], max_l[2], 1.0],
            [max_l[0], max_l[1], min_l[2], 1.0],
            [max_l[0], max_l[1], max_l[2], 1.0],
        ], dtype=np.float32)

        world = (matrix_np @ corners.T).T[:, :3]

        min_aabb = world.min(axis=0)
        max_aabb = world.max(axis=0)

        # add to the nested list, this is flattened and mapped when uploading to SSBO
        self.ubo.comp_meshnode_matrices_nested[model_index].append( 
            MatrixItem( 
                mesh_index, 
                matrix_np,
                min_aabb   = min_aabb,
                max_aabb   = max_aabb
            ) 
        )


    
    #
    # Renderpasses
    #
    def prepareMainRenderpass( self, _scene : SceneManager.Scene, 
                               light_view : Matrix44 = None, 
                               light_projection : Matrix44 = None
        ) -> None:
        self.use_shader( self.general )

        if self.USE_INDIRECT:
            # shadowmap
            glUniform1i( self.shader.uniforms['ushadowmapEnabled'], int(_scene["shadowmap_enabled"]) )
            if _scene["shadowmap_enabled"]:
                glUniformMatrix4fv( self.shader.uniforms['uLightPMatrix'], 1, GL_FALSE, light_projection )
                glUniformMatrix4fv( self.shader.uniforms['uLightVMatrix'], 1, GL_FALSE, light_view )
                self.context.images.bind_gl( self.shadowmap_fbo["depth_image"], GL_TEXTURE7, "sShadowMap", 7 )

        # bind the projection and view  matrix beginning (until shader switch)
        glUniformMatrix4fv( self.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.projection )
        glUniformMatrix4fv( self.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.view )

        # static textures
        self.context.cubemaps.bind( self.context.environment_map, GL_TEXTURE5, "sEnvironment", 5 )
        self.context.images.bind( self.context.cubemaps.brdf_lut, GL_TEXTURE6, "sBRDF", 6 )

        # editor uniforms
        glUniform1i( self.shader.uniforms['in_renderMode'], self.renderMode )
        glUniform1f( self.shader.uniforms['in_roughnessOverride'], self.context.roughnessOverride  )
        glUniform1f( self.shader.uniforms['in_metallicOverride'], self.context.metallicOverride )

        # camera origin
        glUniform4f( self.shader.uniforms['u_ViewOrigin'], self.camera.camera_pos[0], self.camera.camera_pos[1], self.camera.camera_pos[2], 0.0 )

        # sun direction, position and color
        _sun : "GameObject" = self.context.scene.getSun()
        _sun_active = _sun and _sun.hierachyActive()

        if not self.game_runtime:
            _sun_active = _sun_active and _sun.hierachyVisible()

        light_dir   = _sun.transform.local_position if _sun_active else self.settings.default_light_color
        light_color = _sun.light.light_color        if _sun_active else self.settings.default_ambient_color

        glUniform4f( self.shader.uniforms['in_lightdir'], light_dir[0], light_dir[1], light_dir[2], 0.0 )
        glUniform4f( self.shader.uniforms['in_lightcolor'], light_color[0], light_color[1], light_color[2], 1.0 )
        glUniform4f( self.shader.uniforms['in_ambientcolor'], _scene["ambient_color"][0], _scene["ambient_color"][1], _scene["ambient_color"][2], 1.0 )

        # lights
        self.ubo._upload_lights_ubo( _sun )
        self.ubo.ubo_lights.bind( binding = 0 )  

        # materials
        self.ubo._upload_material_ubo()
        self.ubo.ubo_materials.bind( binding = 1 )

    def submitMainRenderpassIndirect( self, 
                                      num_batches : int,               # used for drawcount using instancing
                                      draw_ranges : dict[(int, int), (int, int)]    # only used for per mesh
        ) -> None:
        if self.settings.drawWireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )
    
        self.ubo.indirect_ssbo.bind_buffer()

        if self.SHARED_VAO:
            glBindVertexArray( self.context.models.shared_vao.vao )
    
        #for model_index, mesh_index in draw_ranges:
        #    mesh = self.context.models.model_mesh[model_index][mesh_index]
        #    print(f"Mesh {model_index},{mesh_index}: baseVertex={mesh['baseVertex']}, firstIndex={mesh['firstIndex']}, num_indices={mesh['num_indices']}")
    
        # support for indirect, bindless, and shared VAO is enabled.
        # allowing to render the scene in one indirect instanced drawcall
        if self.context.renderer.USE_GPU_DRIVEN_RENDERING: 
            glMultiDrawElementsIndirect(
                GL_TRIANGLES,
                GL_UNSIGNED_INT,
                ctypes.c_void_p(0),
                num_batches, # issue all commands at once (instanced + bindless + shared VAO )
                0
            )

        # Indirect rendering per mesh: batches group game objects sharing the same mesh,
        # but VAO and material bindings are performed per batch on the CPU.
        else:
            for (model_index, mesh_index), (start_offset, drawcount) in draw_ranges.items():
                mesh : "Models.Mesh" = self.context.models.model_mesh[model_index][mesh_index]
            
                if not self.USE_BINDLESS_TEXTURES:
                    self.context.materials.bind( mesh["material"] )
            
                if not self.SHARED_VAO:
                    glBindVertexArray( mesh["vao_simple"].vao )
            
                glMultiDrawElementsIndirect(
                    GL_TRIANGLES,
                    GL_UNSIGNED_INT,
                    ctypes.c_void_p(start_offset * ctypes.sizeof(DrawElementsIndirectCommand)),
                    1, # single command per mesh batch (instance for each gamobject)
                    0
                )

        if self.settings.drawWireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )

    def submitMainRenderpassSimple( self, _draw_list : list[DrawItem] ) -> None:
        if self.settings.drawWireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_LINE )

        for item in _draw_list:
            self.submitDrawItem( item.model_index, item.mesh_index, item.matrix )

        if self.settings.drawWireframe:
            glPolygonMode( GL_FRONT_AND_BACK, GL_FILL )

    def submitShadowRenderpass( self, 
                                num_batches : int, 
                                draw_ranges : dict[(int, int), (int, int)], 
                                light_view : Matrix44, 
                                light_projection : Matrix44 
        ):
        self.bind_fbo( self.shadowmap_fbo, GL_DEPTH_BUFFER_BIT )
        self.use_shader (self.shadowmap )

        glEnable( GL_CULL_FACE )
        glCullFace( GL_FRONT )  # reduce peter-panning

        glUniformMatrix4fv(
            self.shader.uniforms["uVMatrix"],
            1, GL_FALSE, light_view
        )

        glUniformMatrix4fv(
            self.shader.uniforms["uPMatrix"],
            1, GL_FALSE, light_projection
        )

        if self.SHARED_VAO:
            glBindVertexArray( self.context.models.shared_vao.vao )

        if self.context.renderer.USE_GPU_DRIVEN_RENDERING: 
            glMultiDrawElementsIndirect(
                GL_TRIANGLES,
                GL_UNSIGNED_INT,
                ctypes.c_void_p(0),
                num_batches, # issue all commands at once (instanced + bindless + shared VAO )
                0
            )
        else:
            for (model_index, mesh_index), (start_offset, drawcount) in draw_ranges.items():
                mesh = self.context.models.model_mesh[model_index][mesh_index]

                if not self.SHARED_VAO:
                    glBindVertexArray( mesh["vao_simple"].vao )

                glMultiDrawElementsIndirect(
                    GL_TRIANGLES,
                    GL_UNSIGNED_INT,
                    ctypes.c_void_p(start_offset * ctypes.sizeof(DrawElementsIndirectCommand)),
                    1, # single command per mesh batch (instance for each gamobject)
                    0
                )

        #glCullFace(GL_BACK)
        glDisable(GL_CULL_FACE)

        self.unbind_fbo()
    
    def submitFogRenderPass( self, _scene : SceneManager.Scene, current_image ) -> None:
        self.bind_fbo( self.fog_fbo )
        self.use_shader( self.fog )

        glUniformMatrix4fv( self.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.projection )
        glUniformMatrix4fv( self.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.view )
        glUniform4f( self.shader.uniforms['u_ViewOrigin'], self.camera.camera_pos[0], self.camera.camera_pos[1], self.camera.camera_pos[2], 0.0 )

        _sun : "GameObject" = self.context.scene.getSun()
        _sun_active = _sun and _sun.hierachyActive()

        if not self.game_runtime:
            _sun_active = _sun_active and _sun.hierachyVisible()

        #light_dir   = _sun.transform.local_position if _sun_active else self.settings.default_light_color
        fog_color = _scene["fog_color"]

        #glUniform4f( self.shader.uniforms['in_lightdir'], light_dir[0], light_dir[1], light_dir[2], 0.0 )
        glUniform4f( self.shader.uniforms['in_lightcolor'], fog_color[0], fog_color[1], fog_color[2], 1.0 )
        glUniform1f( self.shader.uniforms['ufogDensity'], _scene["fog_density"] )
        glUniform1f( self.shader.uniforms['ufogHeight'], _scene["fog_height"] )
        glUniform1f( self.shader.uniforms['ufogFalloff'], _scene["fog_falloff"] )
        glUniform1i( self.shader.uniforms['ufogLightsContrib'], int(_scene["fog_lights_contrib"]) )

        # lights
        self.ubo.ubo_lights.bind( binding = 0 )  

        glDisable(GL_DEPTH_TEST)

        self.context.images.bind_gl( current_image,  GL_TEXTURE0, "sColorTexture",     0 )

        if self.settings.msaaEnabled:
            self.context.images.bind_gl( self.context.renderer.main_fbo["resolve"]["depth_image"], GL_TEXTURE1, "sDepthTexture",     1 )
        else:
            self.context.images.bind_gl( self.context.renderer.main_fbo['depth_image'], GL_TEXTURE1, "sDepthTexture",     1 )
   
        glBindVertexArray( self.screenVAO )
        glDrawArrays(GL_TRIANGLES, 0, 6)

        self.unbind_fbo()

        return self.fog_fbo["color_image"]

    #
    # Full GPU driven dispatch pipeline
    #
    # +-----------------------+
    # |  Game Objects         
    # |  (CPU-side transforms)
    # +-----------------------+
    #             |
    #             v
    # +-----------------------+
    # | SSBO : comp_gameobject_matrices_ssbo
    # |  - Stores per-game-object world matrices
    # +-----------------------+
    #             |
    #             v
    # +-----------------------+
    # | Dispatch: gpu_driven_build_object_buffer
    # |  - Builds per-object GPU-side data (model matrices etc.)
    # |  - (key part) CAN be shared across indirect and instance buffers
    # +-----------------------+
    #             |
    #             v
    # +-----------------------+
    # | Dispatch: gpu_driven_collect_batches
    # |  - Count mesh/node instances per object
    # +-----------------------+
    #             |
    #             v
    # +-----------------------+
    # | Dispatch: gpu_driven_batch_compact
    # |  - Remove unused meshes
    # |  - Build compact batch lookup table
    # +-----------------------+
    #             |
    #             v
    # +-----------------------+
    # | Dispatch: gpu_driven_build_instances
    # |  - Construct instances_ssbo
    # +-----------------------+
    #             |
    #             v
    # +-----------------------+
    # | Dispatch: compute_indirect
    # |  - Fill indirect_ssbo
    # +-----------------------+
    #             |
    #             v
    # +-----------------------+
    # | GPU Draw Call
    # |  glMultiDrawElementsIndirect using indirect_ssbo already stored on GPU
    # +-----------------------+
    #
    def _dispatch_full_gpu_collect_batches( self, num_gameObjects : int ) -> None:

        #
        # collect mesh/node batches per gameObject
        #
        self.use_shader( self.gpu_driven_batch_counter )

        # this lets the compute shader know the valid range of global invocation IDs (gid),
        glUniform1ui( self.shader.uniforms['num_gameObjects'], num_gameObjects )

        # reset all 'mesh_instance_counter' entries
        glBindBuffer( GL_SHADER_STORAGE_BUFFER, self.ubo.mesh_instance_counter )
        glClearBufferData( GL_SHADER_STORAGE_BUFFER, GL_R32UI, GL_RED_INTEGER, GL_UNSIGNED_INT, None )          

        glUniformMatrix4fv( self.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.projection )
        glUniformMatrix4fv( self.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.view )

        # visbuf
        glBindBuffer( GL_SHADER_STORAGE_BUFFER, self.ubo.visbuf )
        glClearBufferData( GL_SHADER_STORAGE_BUFFER, GL_R32UI, GL_RED_INTEGER, GL_UNSIGNED_INT, np.array([0], dtype=np.uint32) )

        # dispatch
        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)
        group_count = (num_gameObjects + 63) // 64
        glDispatchCompute(group_count, 1, 1)
        glMemoryBarrier(
            GL_SHADER_STORAGE_BARRIER_BIT |
            GL_COMMAND_BARRIER_BIT
        )

        #
        # fill self.ubo.batch_ssbo and
        # construct a compact batch lookup map 
        # because previous dispatch result in:
        #
        # batches [
        #  model/mesh idx      instances
        #    0:                       1
        #    1:                       2
        #  * 2:                       0   - zero instances, model may be unused
        #    3:                       1
        #    4:                       1
        #  ...
        # ]
        #
        # build 'self.batch_ssbo' with unused models removed,
        # and add a compact batch lookup ap
        # meshnode_to_batch [
        # model/mesh idx         batch idx
        #    0:                       0
        #    1:                       1
        #  * 2:                      -1   - unused
        #    3:                       3
        #    4:                       4
        # 
        # ]
        self.use_shader( self.gpu_driven_batch_compact )

        # reset all 'meshnode_to_batch' entries to -1 first
        glBindBuffer( GL_SHADER_STORAGE_BUFFER, self.ubo.meshnode_to_batch )
        glClearBufferData( GL_SHADER_STORAGE_BUFFER, GL_R32I, GL_RED_INTEGER, GL_INT, np.array([-1], dtype=np.int32) )

        # re-purpose draw count as 'num_batches' counter internally
        glBindBuffer( GL_SHADER_STORAGE_BUFFER, self.ubo.batch_counter )
        glBufferSubData( GL_SHADER_STORAGE_BUFFER, 0, 4, np.array([0], dtype=np.uint32) )

        # 'num_instances'
        glBindBuffer( GL_SHADER_STORAGE_BUFFER, self.ubo.instance_counter )
        glBufferSubData( GL_SHADER_STORAGE_BUFFER, 0, 4, np.array([0], dtype=np.uint32) )

        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)
        group_count = (self.ubo.comp_meshnode_max + 127) // 128
        glDispatchCompute(group_count, 1, 1)
        glMemoryBarrier(
            GL_SHADER_STORAGE_BARRIER_BIT |
            GL_COMMAND_BARRIER_BIT
        )

    def _dispatch_full_gpu_build_instances( self, num_gameObjects : int ) -> None:
        #
        # construct the instance buffer, binding gameObjects to a mesh/node instance
        #
        self.use_shader( self.gpu_driven_build_instances )

        # this lets the compute shader know the valid range of global invocation IDs (gid),
        glUniform1ui( self.shader.uniforms['num_gameObjects'], num_gameObjects )

        glBindBuffer( GL_SHADER_STORAGE_BUFFER, self.ubo.mesh_instance_writer )
        glClearBufferData( GL_SHADER_STORAGE_BUFFER, GL_R32UI, GL_RED_INTEGER, GL_UNSIGNED_INT, None )        

        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)
        group_count = (num_gameObjects + 63) // 64
        glDispatchCompute(group_count, 1, 1)
        glMemoryBarrier(
            GL_SHADER_STORAGE_BARRIER_BIT |
            GL_COMMAND_BARRIER_BIT
        )

    def _dispatch_full_gpu_build_object_buffer( self, num_gameObjects ) -> None:
        #
        # build the shared object buffer
        # contains per instance data, eg; modelmatrix, gameObject and material
        #
        self.use_shader( self.gpu_driven_build_object_buffer )

        # this lets the compute shader know the valid range of global invocation IDs (gid),
        glUniform1ui( self.shader.uniforms['num_gameObjects'], num_gameObjects )

        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)
        group_count = (num_gameObjects + 127) // 128
        glDispatchCompute(group_count, 1, 1)

        # make SSBO writes visible to vertex/fragment shaders
        glMemoryBarrier(
            GL_SHADER_STORAGE_BARRIER_BIT |
            GL_COMMAND_BARRIER_BIT
        )

    def _dispatch_full_gpu( self ) -> None:
        
        num_gameObjects : int = len(self.context.world.transforms)

        # sadly, ton of uniforms
        self.ubo.object_ssbo.bind_base( binding = 0 )
        self.ubo.comp_meshnode_matrices_ssbo.bind_base( binding = 1 )
        glBindBufferBase( GL_SHADER_STORAGE_BUFFER, 2, self.ubo.indirect_ssbo.ssbo )
        self.ubo.batch_ssbo.bind_base( binding = 3 )
        self.ubo.model_ssbo.bind_base( binding = 4 )
        self.ubo.comp_gameobject_matrices_ssbo.bind_base( binding = 5 )
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 6, self.ubo.batch_counter)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 7, self.ubo.mesh_instance_counter)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 8, self.ubo.mesh_instance_writer)
        self.ubo.instances_ssbo.bind_base( binding = 9 )
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 10, self.ubo.visbuf)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 11, self.ubo.instance_counter)
        glBindBufferBase(GL_SHADER_STORAGE_BUFFER, 12, self.ubo.meshnode_to_batch)
        self.ubo.object_base_ssbo.bind_base( binding = 13 )
        self.ubo.physic_ssbo.bind_base( binding = 14 )

        # reset states
        self.ubo.object_ssbo.clear()
        self.ubo.batch_ssbo.clear()
        self.ubo.instances_ssbo.clear()
        self.ubo.indirect_ssbo.clear()

        # build object buffer containing gameObject's model mesh/node data eg; modelmatrix
        self.ubo._cpu_build_object_base()
        self._dispatch_full_gpu_build_object_buffer( num_gameObjects )

        # construct the indirect and instance buffers
        self._dispatch_full_gpu_collect_batches( num_gameObjects )
        self._dispatch_full_gpu_build_instances( num_gameObjects )
        self._dispatch_compute_indirect_sbbo( self.ubo.comp_meshnode_max )

    #
    # Compute (hybrid GPU driven)
    #
    def _dispatch_compute_object_block_modelmatrix( self, num_draw_items ) -> None:
        """Compute all modelmatrices for each gameObject's model mesh/node"""
        self.use_shader( self.object_modelmatrix )

        glMemoryBarrier(GL_SHADER_STORAGE_BARRIER_BIT)

        # number of work items = number of draw blocks
        # local_size_x = 64 -> ceil(num_draw_items / 64)
        group_count = (num_draw_items + 63) // 64
        glDispatchCompute(group_count, 1, 1)

        # make SSBO writes visible to vertex/fragment shaders
        glMemoryBarrier(
            GL_SHADER_STORAGE_BARRIER_BIT |
            GL_COMMAND_BARRIER_BIT
        )

    def _dispatch_compute_indirect_sbbo( self, num_batches ) -> None:
        self.use_shader( self.indirect )

        self.ubo.comp_meshnode_matrices_ssbo.bind_base( binding = 1 )
        glBindBufferBase( GL_SHADER_STORAGE_BUFFER, 2, self.ubo.indirect_ssbo.ssbo )
        self.ubo.batch_ssbo.bind_base( binding = 3 )

        # number of work items = number of batches
        # local_size_x = 64 -> ceil(num_batches / 64)
        group_count = (num_batches + 63) // 64
        glDispatchCompute(group_count, 1, 1)

        # make SSBO writes visible to vertex/fragment shaders
        glMemoryBarrier(
            GL_SHADER_STORAGE_BARRIER_BIT |
            GL_COMMAND_BARRIER_BIT
        )

    #
    # begin/end frame
    #
    def begin_frame( self ) -> None:
        """Start for each frame, but triggered after the event_handler.
        Bind framebuffer (FBO), view matrix, frame&delta time"""
        self.frameTime = self.clock.tick( 0 )
        self.deltaTime = self.frameTime / self.DELTA_SHIFT

        # set the deltatime for ImGui
        #print(self.clock.get_fps())
        io = imgui.get_io()
        io.delta_time = self.deltaTime 

        imgui.new_frame()
        self.camera.new_frame()


        self.view = self.context.camera.get_view_matrix()

        # physics
        self._runPhysics()

        # update static model:node(mesh) matrices when dirty
        if self.USE_INDIRECT:
            self.ubo._update_comp_meshnode_matrices_ssbo()

    def dispatch_drawcalls( self, _scene : SceneManager.Scene ) -> None:
        """"
        Dispatch draw calls using the generated item in the draw list
        
            Depending on the OpenGL version:
            This will either batch meshes VAO's. (indirect rendering + GPU compute modelmatrix)
            or create individual draw calls for each item. (simple rendering) 

        """
        # batch meshes (indirect rendering)
        if self.USE_INDIRECT:
            # upload transforms to SSBO (for compute shader)
            self.ubo._upload_comp_gameobject_matrices_map_ssbo()
            self.ubo._upload_comp_physic_matrices_map_ssbo()

            # Full GPU driven, batching, drawbuffer, and indirict buffer (no drawlist)
            if self.USE_FULL_GPU_DRIVEN:
                self._dispatch_full_gpu()

                draw_ranges = None
                num_batches = self.ubo.comp_meshnode_max # bad

            # Hybrid, use GPU compute for draw and indirect buffers (if enabled)
            else:
                self.ubo.instances_ssbo.bind_base( binding = 9 )
                self.ubo.object_ssbo.bind_base( binding = 0 )
                self.ubo.comp_meshnode_matrices_ssbo.bind_base( binding = 1 )
                self.ubo.comp_gameobject_matrices_ssbo.bind_base( binding = 2 )
                self.ubo.physic_ssbo.bind_base( binding = 3 )

                # sort by model and mesh index, constructing a batched VAO list
                batches, num_draw_items = self.ubo._build_batched_draw_list( self.draw_list )
                num_batches = len(batches)

                # build object buffer containing gameObject's model mesh/node data eg; modelmatrix
                num_object_items = self.ubo._upload_object_blocks_ssbo()
                self._dispatch_compute_object_block_modelmatrix( num_object_items )
            
                # build a shared indirect buffer and draw_ranges
                # *only build draw_ranges when instancing is disabled
                draw_ranges = self.ubo._upload_indirect_buffer( batches, num_draw_items )

            # shadowmap renderpass
            if _scene["shadowmap_enabled"]:
                light_view, light_projection = self._compute_light_vp()
                self.submitShadowRenderpass( num_batches, draw_ranges, light_view, light_projection )
            else:
                light_view = light_projection = None

            #
            # scene
            #
            self.bind_fbo( self.main_fbo )

            self.context.skybox.draw( _scene )

            self.prepareMainRenderpass( _scene, light_view, light_projection )
            self.submitMainRenderpassIndirect( num_batches, draw_ranges )

        # create individual draw calls for each item in the draw list (simple rendering)
        # only draw the main renderpass to prevent performance regression, skips;
        # - shadows
        # -
        else:
            self.bind_fbo( self.main_fbo )

            self.context.skybox.draw( _scene )

            self.prepareMainRenderpass( _scene, None, None )
            self.submitMainRenderpassSimple( self.draw_list )

        glBindVertexArray(0)

    def dispatch_postprocess( self ) -> None:
        _scene : SceneManager.Scene = self.context.scene.getCurrentScene()

        current_image = self.main_fbo['output']

        if _scene["fog_enabled"]:
            current_image = self.submitFogRenderPass( _scene, current_image )

        self.output_image = current_image

    def end_frame( self ) -> None:
        """End for each frame, clear GL states, resolve MSAA if enabled, draw ImGui.
        ImGui in will draw the 3D viewport.
        otherwise render_fbo() will directly render to the swapchain"""

        if self.game_start:
            self.game_start = False

        if self.game_stop:
            self.game_stop = False

        glUseProgram( 0 )
        glFlush()

        # stop rendering to main FBO
        self.unbind_fbo()

        # resolve multisampled main FBO
        if self.settings.msaaEnabled:
            self.resolve_multisample()

        self.dispatch_postprocess()

        self.context.gui.render()

        self.framenum += 1

        # clear swapchain
        glClear( GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT )

        # render fbo texture to swapchain
        #self.render_fbo( self.main_fbo["output"] )
   
        # render imgui buffer
        imgui.render()
        self.render_backend.render( imgui.get_draw_data() )

        self.check_opengl_error()

        self.draw_list.clear()

        # upload to swapchain image
        pygame.display.flip()