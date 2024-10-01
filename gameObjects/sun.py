import math
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

from gameObjects.sphere import Sphere

class Sun( Sphere ):
    def __init__( self, renderer, translate=( 0.0, 0.0, 0.0 ), 
                 rotation=( 0.0, 0.0, 0.0, 0.0 ), 
                 radius=1, stacks=20, slices=20,
                 color=( 1.0, 1.0, 1.0 ), 
                 diffuse=( 1.0, 1.0, 1.0 ),
                 ambient=( 1.0, 1.0, 1.0 ),
                 angle=1,
                 anim_speed=0.05,
                 anim_radius=4) -> None:
        super().__init__( translate, rotation, radius, stacks, slices, color )

        # context
        self.renderer = renderer

        self.angle = angle
        self.light_pos = [1, -1, 1];
        self.anim_radius = anim_radius
        self.anim_speed = anim_speed
        self.ambient = ambient
        self.diffuse = diffuse


        glEnable( GL_DEPTH_TEST )
        glEnable( GL_LIGHTING )
        glShadeModel( GL_SMOOTH )
        glEnable( GL_COLOR_MATERIAL )
        glColorMaterial( GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE )

        glEnable( GL_LIGHT0 )
        glLightfv( GL_LIGHT0, GL_AMBIENT, [self.ambient[0], self.ambient[1], self.ambient[2], 1] )
        glLightfv( GL_LIGHT0, GL_DIFFUSE, [self.diffuse[0], self.diffuse[1], self.diffuse[2], 1] )
        return
    
    def update( self ) -> None:
        self.angle += self.renderer.deltaTime * self.anim_speed 

        self.light_pos[0] = self.anim_radius * math.cos( self.angle )  # Update x position
        self.light_pos[2] = self.anim_radius * math.sin( self.angle )  # Update y position for vertical

        glLightfv( GL_LIGHT0, GL_POSITION, 
                  [self.light_pos[0], self.light_pos[1], self.light_pos[2], 0] 
        )

        # the sun sphere position
        self.translate =  self.light_pos;
        return

    def draw( self ) -> None:
        super().draw()