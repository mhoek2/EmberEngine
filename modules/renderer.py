import math
from OpenGL.arrays import returnPointer
from pyrr import matrix44, Vector3
import pygame
from pygame.locals import *

from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

import numpy as np

from modules.shader import Shader
from modules.camera import Camera

class Renderer:
    """The rendering backend"""
    def __init__( self, context ):
        self.context = context

        # window
        self.create_instance( 1200, 800 )

        self.paused = False
        self.running = True

        # frames and timing
        self.clock = pygame.time.Clock()
        self.DELTA_SHIFT = 1000
        self.framenum = 0
        self.frameTime = 0
        self.deltaTime = 0

        # init mouse movement and center mouse on screen
        self.screen_center = [self.screen.get_size()[i] // 2 for i in range(2)]
        pygame.mouse.set_pos( self.screen_center )
        pygame.mouse.set_visible( False )

        # camera
        self.cam = Camera()

        # shaders
        self.create_shaders()

        # debug
        self.renderMode = 0
        self.animSun = False

        #glClearColor(0.0, 0.3, 0.7, 1)
        glClearColor(0.0, 0.0, 0.0, 1)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.setup_projection_matrix()

    def use_shader( self, shader ) -> None:
        self.shader = shader
        glUseProgram( self.shader.program )

    def create_shaders( self ) -> None:
        self.general = Shader( self.context, "general" )
        self.skybox = Shader( self.context, "skybox" )

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

    def create_instance( self, width, height ) -> None:
        self.width = width
        self.height = height

        pygame.init()

        gl_version = (3, 3)

        #pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, gl_version[0])
        #pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, gl_version[1])
        #pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)

        self.display = ( self.width, self.height )
        self.screen = pygame.display.set_mode( self.display, DOUBLEBUF | OPENGL )

    def setup_projection_matrix( self ) -> None:
        glViewport( 0, 0, self.width, self.height )

        self.aspect_ratio = self.width / self.height
        self.projection = matrix44.create_perspective_projection_matrix(45.0, self.aspect_ratio, 0.1, 1000.0)

    def event_handler_render_mode( self, event ) -> None:
        if event.key == pygame.K_0: self.renderMode = 0
        if event.key == pygame.K_1: self.renderMode = 1
        if event.key == pygame.K_2: self.renderMode = 2
        if event.key == pygame.K_3: self.renderMode = 3
        if event.key == pygame.K_4: self.renderMode = 4
        if event.key == pygame.K_5: self.renderMode = 5
        if event.key == pygame.K_6: self.renderMode = 6
        if event.key == pygame.K_7: self.renderMode = 7
        if event.key == pygame.K_8: self.renderMode = 8
        if event.key == pygame.K_9: self.renderMode = 9

    def event_handler( self, events ) -> None:
        mouse_moving = False

        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    self.running = False
                if event.key == pygame.K_PAUSE or event.key == pygame.K_p:
                    self.paused = not self.paused
                    pygame.mouse.set_pos( self.screen_center ) 

                self.event_handler_render_mode( event )
            if not self.paused: 
                if event.type == pygame.MOUSEMOTION:
                    self.mouse_move = [event.pos[i] - self.screen_center[i] for i in range(2)]
                    mouse_moving = True

        if not mouse_moving:
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

        self.cam.process_mouse_movement( xpos, -ypos )
        return

    def begin_frame( self ) -> None:
        self.frameTime = self.clock.tick(60)
        self.deltaTime = self.frameTime / self.DELTA_SHIFT

        self.do_movement()
        self.do_mouse()

        # animate sun
        keypress = pygame.key.get_pressed()
        if keypress[pygame.K_o]:
            self.animSun = True
        elif self.animSun:
            self.animSun = False

        # clear swapchain or FBO
        glClear( GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT )

    def end_frame( self ) -> None:
        self.framenum += 1

        # upload to swapchain image
        pygame.display.flip()
