import math
from OpenGL.arrays import returnPointer
from pyrr import matrix44, Vector3
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

from modules.shader import Shader
from modules.camera import Camera

class Renderer:
    """The rendering backend"""
    def __init__( self ):
        # window
        self.create_instance( 1200, 800 )

        self.clock = pygame.time.Clock()

        self.paused = False
        self.running = True

        # frames and timing
        self.DELTA_SHIFT = 1000
        self.framenum = 0
        self.frameTime = 0
        self.deltaTime = 0

        # init mouse movement and center mouse on screen
        self.screen_center = [self.screen.get_size()[i] // 2 for i in range(2)]
        
        # camera
        self.cam = Camera()
        self.lastX, self.lastY = 960, 540
        self.first_mouse = True

        pygame.mouse.set_pos( self.screen_center )
        #pygame.mouse.set_visible( False )

        # shaders
        self.create_shaders()

        glEnable(GL_DEPTH_TEST)

    def create_shaders( self ) -> None:
        self.shader = Shader( "general" )

        # keep this here for now since only one shader is used
        self.uMMatrix = glGetUniformLocation(self.shader.program, "uMMatrix")
        self.uVMatrix = glGetUniformLocation(self.shader.program, "uVMatrix")
        self.uPMatrix = glGetUniformLocation(self.shader.program, "uPMatrix")
        self.sTexture = glGetUniformLocation(self.shader.program, "sTexture")
       
        self.aVertex = glGetAttribLocation(self.shader.program, "aVertex")
        self.aNormal = glGetAttribLocation(self.shader.program, "aNormal")
        self.aTexCoord = glGetAttribLocation(self.shader.program, "aTexCoord")

        glUseProgram( self.shader.program )
        glEnableVertexAttribArray( self.aVertex )
        glEnableVertexAttribArray( self.aNormal )
        glEnableVertexAttribArray( self.aTexCoord )

    def create_instance( self, width, height ) -> None:
        self.width = width
        self.height = height

        pygame.init()
        self.display = ( self.width, self.height )
        self.screen = pygame.display.set_mode( self.display, DOUBLEBUF | OPENGL )

    def setup_frustum_mvp( self ) -> None:
        glViewport( 0, 0, self.width, self.height )

        self.aspect_ratio = self.width / self.height
        self.model = matrix44.create_from_translation(Vector3([-14.0, -8.0, 0.0]))
        self.projection = matrix44.create_perspective_projection_matrix(45.0, self.aspect_ratio, 0.1, 100.0)

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
            velocity *= 3

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

        glClear( GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT )

    def end_frame( self ) -> None:

        self.framenum += 1
        pygame.display.flip()
