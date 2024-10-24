import math
from OpenGL.arrays import returnPointer
from pygame.math import Vector2
from pyrr import matrix44, Vector3
import pygame
from pygame.locals import *

from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

import numpy as np

import imgui

from modules.shader import Shader
from modules.camera import Camera
from modules.pyimgui_renderer import PygameRenderer

class Renderer:

    """The rendering backend"""
    def __init__( self, context ):
        self.context = context

        # window
        self.display_size : Vector2 = Vector2( 1500, 1000 )
        self.viewport_size : Vector2 = Vector2( 600, 800 )
        self.create_instance()

        # imgui
        imgui.create_context()
        imgui.get_io().display_size = self.display_size
        imgui.get_io().config_flags |= imgui.CONFIG_DOCKING_ENABLE
        imgui.get_io().config_flags |= imgui.CONFIG_VIEWPORTS_ENABLE

        self.imgui_renderer = PygameRenderer()

        self.paused = False
        self.running = True
        self.ImGuiInput = True # True: imgui, Fase: Game
        self.ImGuiInputFocussed = False # True: imgui, Fase: Game

        # frames and timing
        self.clock = pygame.time.Clock()
        self.DELTA_SHIFT = 1000
        self.framenum = 0
        self.frameTime = 0
        self.deltaTime = 0

        # init mouse movement and center mouse on screen
        self.screen_center = [self.screen.get_size()[i] // 2 for i in range(2)]
        pygame.mouse.set_pos( self.screen_center )

        # camera
        self.cam = Camera()

        # shaders
        self.create_shaders()

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
            ]

        self.animSun = False

        # FBO
        self.current_fbo = False;
        self.create_screen_vao()
        self.main_fbo = {}
        self.main_fbo["size"] = Vector2( int(self.display_size.x), int(self.display_size.y) )
        self.main_fbo["fbo"], self.main_fbo["texture"] = self.create_fbo_with_depth( self.main_fbo["size"] )

        #glClearColor(0.0, 0.3, 0.7, 1)
        glClearColor(0.0, 0.0, 0.0, 1)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.setup_projection_matrix( self.display_size)

    @staticmethod
    def check_opengl_error():
        err = glGetError()
        if err != GL_NO_ERROR:
            print(  f"OpenGL Error: {err}" )

    def create_instance( self ) -> None:
        pygame.init()

        gl_version = (3, 3)

        #pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, gl_version[0])
        #pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, gl_version[1])
        #pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

        self.screen = pygame.display.set_mode( self.display_size, DOUBLEBUF | OPENGL )
        pygame.display.set_caption( "EmberEngine 3D" )
     
    def shutdown( self ) -> None:
        self.imgui_renderer.shutdown()
        pygame.quit()

    def create_screen_vao( self ):
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

    def create_fbo( self, size ):
        fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)

        # Create a texture to render
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, size.x, size.y, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
        # Attach the texture to the FBO
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0)

        # Check if FBO is complete
        if glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE:
            raise ValueError("Framebuffer not complete!")

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        return fbo, texture

    def create_fbo_with_depth( self, size : Vector2 ):
        fbo = glGenFramebuffers( 1 )
        glBindFramebuffer( GL_FRAMEBUFFER, fbo )

        # Create a texture to render the color
        color_texture = glGenTextures( 1 )
        glBindTexture( GL_TEXTURE_2D, color_texture )
        glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA, size.x, size.y, 0, GL_RGBA, GL_UNSIGNED_BYTE, None )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR )
        glTexParameteri( GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR )
    
        # Attach the color texture to the FBO
        glFramebufferTexture2D( GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, color_texture, 0 )

        # Create a renderbuffer for depth
        depth_buffer = glGenRenderbuffers( 1 )
        glBindRenderbuffer( GL_RENDERBUFFER, depth_buffer )
        glRenderbufferStorage( GL_RENDERBUFFER, GL_DEPTH_COMPONENT, int(size.x), int(size.y) )

        # Attach the depth renderbuffer to the FBO
        glFramebufferRenderbuffer( GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depth_buffer )

        # Check if the FBO is complete
        if glCheckFramebufferStatus( GL_FRAMEBUFFER ) != GL_FRAMEBUFFER_COMPLETE:
            print( "Framebuffer not complete!" )
    
        glBindFramebuffer( GL_FRAMEBUFFER, 0 )

        return fbo, color_texture

    def bind_fbo( self, fbo ) -> None:
        # if rendering to a FBO, stop ..
        self.unbind_fbo()

        self.current_fbo = fbo
        glBindFramebuffer( GL_FRAMEBUFFER, self.current_fbo["fbo"] )
        glViewport( 0, 0, int(self.current_fbo["size"].x), int(self.current_fbo["size"].y) )
        glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
        glEnable(GL_DEPTH_TEST);

    def unbind_fbo( self ) -> None:
        """Stop rending to current fbo"""
        if self.current_fbo:
            self.current_fbo = False

        glBindFramebuffer( GL_FRAMEBUFFER, 0 )

    def render_fbo( self, fbo_texture ):
        self.use_shader( self.gamma )

        glBindVertexArray( self.screenVAO )
        glDisable(GL_DEPTH_TEST);

        glActiveTexture( GL_TEXTURE0 )
        glBindTexture( GL_TEXTURE_2D, fbo_texture )
        glUniform1i(glGetUniformLocation( self.shader.program, "screenTexture" ), 0)
        glDrawArrays(GL_TRIANGLES, 0, 6)

        glBindVertexArray(0)

    def use_shader( self, shader ) -> None:
        self.shader = shader
        glUseProgram( self.shader.program )

    def create_shaders( self ) -> None:
        self.general = Shader( self.context, "general" )
        self.skybox = Shader( self.context, "skybox" )
        self.gamma = Shader( self.context, "gamma" )

        # keep this here for now since only one shader is used
        # ..!

        # general
        self.use_shader( self.general )

        self.uMMatrix = glGetUniformLocation(self.shader.program, "uMMatrix")
        self.uVMatrix = glGetUniformLocation(self.shader.program, "uVMatrix")
        self.uPMatrix = glGetUniformLocation(self.shader.program, "uPMatrix")

        self.sTexture = glGetUniformLocation(self.shader.program, "sTexture")
        self.sNormal = glGetUniformLocation(self.shader.program, "sNormal")
        self.sEnvironment = glGetUniformLocation(self.shader.program, "sEnvironment")

        self.u_ViewOrigin = glGetUniformLocation(self.shader.program, "u_ViewOrigin")
        self.in_lightdir = glGetUniformLocation(self.shader.program, "in_lightdir")
       
        self.in_renderMode = glGetUniformLocation(self.shader.program, "in_renderMode")

        # skybox
        self.use_shader( self.skybox )
        self.uVMatrix2 = glGetUniformLocation(self.shader.program, "uVMatrix")
        self.uPMatrix2 = glGetUniformLocation(self.shader.program, "uPMatrix")

        # gamma
        # add gamma modifier float

    def setup_projection_matrix( self, size : Vector2 ) -> None:
        glViewport( 0, 0, int(size.x), int(size.y) )

        self.aspect_ratio = size.x / size.y
        self.projection = matrix44.create_perspective_projection_matrix(45.0, self.aspect_ratio, 0.1, 1000.0)

    def toggle_input_state( self ) -> None:
        """Toggle input between application and viewport"""
        if self.ImGuiInput:
            self.ImGuiInput = False
            self.ImGuiInputFocussed = True
            pygame.mouse.set_visible( False )
            pygame.mouse.set_pos( self.screen_center )
        else:
            self.ImGuiInput = True
            pygame.mouse.set_visible( True )

    def event_handler( self, events ) -> None:
        mouse_moving = False

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False

            #if event.type == pygame.VIDEORESIZE:
                #screen_size = (event.w, event.h)
                #screen = pygame.display.set_mode(screen_size, pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
                #imgui.get_io().display_size = screen_size  # Update ImGui display size

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    self.toggle_input_state()

                if event.key == pygame.K_ESCAPE:
                    self.running = False

                if event.key == pygame.K_PAUSE or event.key == pygame.K_p:
                    if not self.ImGuiInput:
                        self.paused = not self.paused
                        pygame.mouse.set_pos( self.screen_center ) 

            if not self.paused: 
                if event.type == pygame.MOUSEMOTION:
                    self.mouse_move = [event.pos[i] - self.screen_center[i] for i in range(2)]
                    mouse_moving = True

            self.imgui_renderer.process_event(event)

        if not self.ImGuiInput and not mouse_moving:
            pygame.mouse.set_pos( self.screen_center )

    def do_movement(self) -> None:
        keypress = pygame.key.get_pressed()
        velocity = 0.05;

        if keypress[pygame.K_LCTRL] or keypress[pygame.K_RCTRL]:
            velocity *= 30

        if keypress[pygame.K_w]:
            self.cam.process_keyboard( "FORWARD", velocity )
        if keypress[pygame.K_s]:
            self.cam.process_keyboard( "BACKWARD", velocity )
        if keypress[pygame.K_d]:
            self.cam.process_keyboard( "RIGHT", velocity )
        if keypress[pygame.K_a]:
            self.cam.process_keyboard( "LEFT", velocity )
        
    def do_mouse( self ):
        xpos, ypos = pygame.mouse.get_rel()

        if self.ImGuiInputFocussed:
            """Input state changed, dont process mouse movement on the first """
            self.ImGuiInputFocussed = False
            return

        self.cam.process_mouse_movement( xpos, -ypos )
        return

    def begin_frame( self ) -> None:
        self.frameTime = self.clock.tick(60)
        self.deltaTime = self.frameTime / self.DELTA_SHIFT

        imgui.new_frame()

        if not self.ImGuiInput:
            self.do_movement()
            self.do_mouse()

        # animate sun
        keypress = pygame.key.get_pressed()
        if keypress[pygame.K_o]:
            self.animSun = True
        elif self.animSun:
            self.animSun = False

    def end_frame( self ) -> None:
        self.framenum += 1

        # clear swapchain
        glClear( GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT )

        # render fbo texture to swapchain
        #self.render_fbo( self.main_fbo["texture"] )
   
        # render imgui buffer
        imgui.render()
        self.imgui_renderer.render( imgui.get_draw_data() )

        self.check_opengl_error()

        # upload to swapchain image
        pygame.display.flip()