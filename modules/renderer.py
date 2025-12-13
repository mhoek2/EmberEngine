from typing import TYPE_CHECKING, TypedDict

import os
import math
from OpenGL.arrays import returnPointer
from pygame.math import Vector2
from pyrr import matrix44
import pygame
from pygame.locals import *

from imgui_bundle.python_backends.pygame_backend import imgui, PygameRenderer
from imgui_bundle import icons_fontawesome_6 as fa

from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *
import struct

import numpy as np
import enum

from modules.settings import Settings
from modules.project import ProjectManager
from modules.shader import Shader
from modules.camera import Camera

import pybullet as p

if TYPE_CHECKING:
    from main import EmberEngine

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
        self.create_shaders()

        # ubo
        self.ubo_lights = Renderer.LightUBO( self.general, "Lights", 0 )

        # debug
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
            ]

        # FBO
        self.current_fbo = None;
        self.create_screen_vao()

        self.main_fbo = {}
        self.main_fbo["size"] = Vector2( int(self.display_size.x), int(self.display_size.y) )
        self.main_fbo["fbo"], self.main_fbo["color_image"] = self.create_fbo_with_depth( self.main_fbo["size"] )
        self.main_fbo['output'] = self.main_fbo["color_image"]

        if self.settings.msaaEnabled:
            self.main_fbo["resolve"] = {}
            self.main_fbo["resolve"]["color_image"] = self.create_resolve_texture( self.main_fbo["size"]  )
            self.main_fbo["resolve"]["fbo"] = self.create_resolve_fbo( self.main_fbo["resolve"]["color_image"]  )
            self.main_fbo['output'] = self.main_fbo["resolve"]["color_image"]

        glClearColor(0.0, 0.0, 0.0, 1)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.setup_projection_matrix( 
            size = self.display_size 
        )

        # physics
        self._initPhysics()

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

    def get_window_title(self) -> str:
        return self.project.meta.get("name") if self.settings.is_exported else self.settings.application_name
    
    def create_instance( self ) -> None:
        """Create the window and instance with openGL"""
        pygame.init()
        pygame.display.set_caption( self.get_window_title() )

        gl_version = (3, 3)
        #pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, gl_version[0])
        #pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, gl_version[1])
        #pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

        if self.settings.msaaEnabled:
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

        display = pygame.display.Info()
        self.display_size = imgui.ImVec2(display.current_w, display.current_h)

        # this is a bit of a hack to get windowed fullscreen?
        self.display_size -= imgui.ImVec2( 0.0, 80.0 );

        self.screen = pygame.display.set_mode( self.display_size, RESIZABLE | DOUBLEBUF | OPENGL )
        
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

    def create_resolve_texture( self, size : Vector2 ):
        """Create a image attachment used as the resolved MSAA

        :param size: The dimensions of the image
        :type size: Vector2
        :return: The uid of the texture in GPU memory
        :rtype: uint32/uintc
        """
        texture_id = glGenTextures( 1 )
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, int(size.x), int(size.y), 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)
        return texture_id

    def create_resolve_fbo( self, resolved_texture ):
        """Create the resolve framebuffer (FBO) and bind the resolve image attachment

        :param resolved_texture: The image attachment MSAA should resolve to (not sample from)
        :type resolved_texture: uint32/uintc
        :return: The uid of the framebuffer (FBO)
        :rtype: uint32/uintc
        """
        resolve_fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, resolve_fbo)

        glBindTexture(GL_TEXTURE_2D, resolved_texture)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, resolved_texture, 0)

        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise Exception("Resolve framebuffer is not complete!")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        return resolve_fbo

    def resolve_multisample_texture( self ):
        """The 'renderpass' that samples from main framebuffer and resolves to MSAA"""
        glBindFramebuffer( GL_FRAMEBUFFER, self.main_fbo["resolve"]["fbo"] )
        glClear( GL_COLOR_BUFFER_BIT )

        self.use_shader( self.resolve )

        glBindVertexArray( self.screenVAO )
        glDisable(GL_DEPTH_TEST);

        glActiveTexture( GL_TEXTURE0 )
        glBindTexture( GL_TEXTURE_2D_MULTISAMPLE, self.main_fbo["color_image"] )
        glUniform1i( glGetUniformLocation( self.shader.program, "msaa_texture"), 0 )
        glUniform1i( glGetUniformLocation( self.shader.program, "samples"), self.settings.msaa )

        glUniform1i(glGetUniformLocation( self.shader.program, "screenTexture" ), 0)
        glDrawArrays(GL_TRIANGLES, 0, 6)

        glBindVertexArray(0)

        glBindFramebuffer( GL_FRAMEBUFFER, 0 )

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

        # Set MSAA
        if self.settings.msaaEnabled:
            glEnable( GL_MULTISAMPLE );

            glBindTexture( GL_TEXTURE_2D_MULTISAMPLE, color_texture )
            glTexImage2DMultisample(GL_TEXTURE_2D_MULTISAMPLE, self.settings.msaa, GL_RGBA16F, int(size.x), int(size.y), GL_TRUE)
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D_MULTISAMPLE, color_texture, 0)
        else:
            glBindTexture( GL_TEXTURE_2D, color_texture )
            glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA16F, int(size.x), int(size.y), 0, GL_RGBA, GL_FLOAT, None )
            glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR )
            glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )
            glFramebufferTexture2D( GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, color_texture, 0 )

        # Create a renderbuffer for depth
        depth_buffer = glGenRenderbuffers( 1 )
        glBindRenderbuffer( GL_RENDERBUFFER, depth_buffer )
        
        # Set MSAA
        if self.settings.msaaEnabled:
            glRenderbufferStorageMultisample( GL_RENDERBUFFER, self.settings.msaa, GL_DEPTH24_STENCIL8, int(size.x), int(size.y) )
            glFramebufferRenderbuffer( GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, depth_buffer )
        else:
            glRenderbufferStorage( GL_RENDERBUFFER, GL_DEPTH_COMPONENT, int(size.x), int(size.y) )
            glFramebufferRenderbuffer( GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depth_buffer )

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

        return fbo, color_texture

    def bind_fbo( self, fbo ) -> None:
        """Bind a framebuffer (FBO) to the command buffer.
        
        :param fbo: The framebuffer uid
        :type fbo: uint32/uintc
        """
        # if rendering to a FBO, stop ..
        self.unbind_fbo()

        self.current_fbo = fbo
        glBindFramebuffer( GL_FRAMEBUFFER, self.current_fbo["fbo"] )
        glViewport( 0, 0, int(self.current_fbo["size"].x), int(self.current_fbo["size"].y) )
        glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
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

    def use_shader( self, shader : Shader ) -> None:
        """Bind a shader program to the command buffer

        :param shader: the shader object containing the program
        :type shader: Shader
        """
        self.shader : Shader = shader
        glUseProgram( self.shader.program )

    def create_shaders( self ) -> None:
        """Create the GLSL shaders used for the editor and general pipeline"""
        self.general            = Shader( self.context, "general" )
        self.skybox             = Shader( self.context, "skybox" )
        self.skybox_proc        = Shader( self.context, "skybox_proc" )
        self.gamma              = Shader( self.context, "gamma" )
        self.color              = Shader( self.context, "color" )
        self.resolve            = Shader( self.context, "resolve" )

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
            t           : int # Light(GameObject).Type_

        def __init__(self, 
                     shader : Shader, 
                     block_name     : str ="Lights", 
                     binding        : int = 0
            ):
            self.binding = binding
            self.block_index = glGetUniformBlockIndex( shader.program, block_name )

            if self.block_index == GL_INVALID_INDEX:
                raise RuntimeError( f"Uniform block [{block_name}] not found in shader." )

            glUniformBlockBinding( shader.program, self.block_index, binding )

            self.ubo = glGenBuffers(1)
            glBindBuffer( GL_UNIFORM_BUFFER, self.ubo )

            # (u_num_lights 4b + 12bpad = 16 bytes) + 32 * 64 bytes
            total_size = 16 + self.MAX_LIGHTS * self.LIGHT_STRUCT.size
            glBufferData( GL_UNIFORM_BUFFER, total_size, None, GL_DYNAMIC_DRAW )
            glBindBuffer( GL_UNIFORM_BUFFER, 0 )
            glBindBufferBase( GL_UNIFORM_BUFFER, binding, self.ubo )

        def update( self, lights ):
            num_lights = min(len(lights), self.MAX_LIGHTS)

            data = bytearray()

            # u_num_lights
            data += struct.pack("I 3I", num_lights, 0, 0, 0)

            # u_lights
            for light in lights[:num_lights]:
                ox, oy, oz  = light["origin"]
                cx, cy, cz  = light["color"]
                rx, ry, rz  = light["rotation"]

                data += self.LIGHT_STRUCT.pack(
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
                data += empty * empty_count

            glBindBuffer(GL_UNIFORM_BUFFER, self.ubo)
            glBufferSubData(GL_UNIFORM_BUFFER, 0, len(data), data)
            glBindBuffer(GL_UNIFORM_BUFFER, 0)

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
            self.ImGuiInputFocussed = True
            pygame.mouse.set_visible( False )
            pygame.mouse.set_pos( self.screen_center )
        else:
            self.ImGuiInput = True
            pygame.mouse.set_visible( True )

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
        mouse_moving = False

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

            if not self.paused: 
                if event.type == pygame.MOUSEMOTION:
                    self.mouse_move = [event.pos[i] - self.screen_center[i] for i in range(2)]
                    mouse_moving = True

        if not self.ImGuiInput and not mouse_moving:
            pygame.mouse.set_pos( self.screen_center )

    def _initPhysics( self ):
        """Initialize the pybullter physics engine and set gravity"""
        self.physics_client = p.connect(p.DIRECT)

        #p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, -10, 0)

        # debug print list of available functions
        #for name in dir(p):
        #    if callable(getattr(p, name)):
        #        print(name)

    def _runPhysics( self ):
        """Run the step simulation when game is running"""
        if self.game_running:
            for _ in range( int(self.deltaTime / (1./240.)) ):
                p.stepSimulation()

    def bind_light_ubo( self, lights : LightUBO.Light ) -> None:
        self.ubo_lights.update( lights )

    def begin_frame( self ) -> None:
        """Start for each frame, but triggered after the event_handler.
        Bind framebuffer (FBO), view matrix, frame&delta time"""
        self.frameTime = self.clock.tick(0)
        self.deltaTime = self.frameTime / self.DELTA_SHIFT

        # set the deltatime for ImGui
        #print(self.clock.get_fps())
        io = imgui.get_io()
        io.delta_time = self.deltaTime 

        imgui.new_frame()
        self.camera.new_frame()
        # bind main FBO
        self.bind_fbo( self.main_fbo )

        self.view = self.context.camera.get_view_matrix()

        # physics
        self._runPhysics()

    def end_frame( self ) -> None:
        """End for each frame, clear GL states, resolve MSAA if enabled, draw ImGui.
        ImGui in will draw the 3D viewport.
        otherwise render_fbo() will directly render to the swapchain"""
        glUseProgram( 0 )
        glFlush()

        # stop rendering to main FBO
        self.unbind_fbo()

        # resolve multisampled main FBO
        if self.settings.msaaEnabled:
            self.resolve_multisample_texture()

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

        # upload to swapchain image
        pygame.display.flip()