import math
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

class Renderer:
    """The rendering backend"""
    def __init__( self ):
        self.create_instance()
        self.clock = pygame.time.Clock()

        self.pitch = 0.3;
        self.yaw = 0.3;
        self.speed = 0.15;

        self.paused = False
        self.running = True

        # frames and timing
        self.DELTA_SHIFT = 1000
        self.framenum = 0
        self.frameTime = 0
        self.deltaTime = 0

        # init mouse movement and center mouse on screen
        self.screen_center = [self.screen.get_size()[i] // 2 for i in range(2)]
        self.mouse_move = [ 0, 0 ]
        self.up_down_angle = 0.0
        pygame.mouse.set_pos( self.screen_center )

    def create_instance( self ) -> None:
        pygame.init()
        self.display = (1200, 800)
        self.screen = pygame.display.set_mode( self.display, DOUBLEBUF | OPENGL )

    def setup_frustum_mvp( self ) -> None:
        glMatrixMode( GL_PROJECTION )
        gluPerspective( 45, ( self.display[0]/self.display[1] ), 0.1, 50.0 )

        glMatrixMode( GL_MODELVIEW )
        gluLookAt( 0, -8, 0, 0, 0, 0, 0, 0, 1 )
        self.viewMatrix = glGetFloatv( GL_MODELVIEW_MATRIX )
        glLoadIdentity()

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

    def update_camera( self ) -> None:
        # get keys
        keypress = pygame.key.get_pressed()
        self.mouse_move = pygame.mouse.get_rel()
    
        # init model view matrix
        glLoadIdentity()

        # apply the look up and down
        self.up_down_angle += self.mouse_move[1] * self.pitch
        glRotatef( self.up_down_angle, 1.0, 0.0, 0.0 )

        # init the view matrix
        glPushMatrix()
        glLoadIdentity()

        camera_up = np.array([0.0, 1.0, 0.0])  # Up direction in world space (Y axis)
        camera_right = np.array([1.0, 0.0, 0.0])  # Right direction in world space (X axis)
        camera_forward = np.array([0.0, 0.0, -1.0])  # Forward direction in world space (Z axis)

        if keypress[pygame.K_w]:
            # Move forward in the direction of the forward vector
            glTranslatef(*-camera_forward * self.speed)

        if keypress[pygame.K_s]:
            # Move backward in the direction opposite to the forward vector
            glTranslatef(*(camera_forward) * self.speed)

        if keypress[pygame.K_d]:
            # Move to the right
            glTranslatef(*-camera_right * self.speed)

        if keypress[pygame.K_a]:
            # Move to the left
            glTranslatef(*(camera_right) * self.speed)

        if keypress[pygame.K_SPACE]:
            # Move up in the direction of the up vector
            glTranslatef(*-camera_up * self.speed)

        if keypress[pygame.K_LCTRL]:  # Assuming left control key for downward movement
            # Move down in the direction opposite to the up vector
            glTranslatef(*(camera_up) * self.speed)

        # apply the left and right rotation
        glRotatef( self.mouse_move[0] * self.yaw, 0.0, 1.0, 0.0 )

        # multiply the current matrix by the get the new view matrix and store the final vie matrix 
        glMultMatrixf( self.viewMatrix )
        self.viewMatrix = glGetFloatv( GL_MODELVIEW_MATRIX )

        # apply view matrix
        glPopMatrix()
        glMultMatrixf( self.viewMatrix )

    def begin_frame( self ) -> None:
        self.frameTime = self.clock.tick(60)
        self.deltaTime = self.frameTime / self.DELTA_SHIFT

        self.update_camera()

        glClear( GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT )
        glPushMatrix()

    def end_frame( self ) -> None:
        glPopMatrix()

        self.framenum += 1
        pygame.display.flip()
