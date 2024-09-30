import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

from gameObjects.gameObject import GameObject

class Sphere( GameObject ):
    def __init__( self , translate=( 0.0, 0.0, 0.0 ), rotation=( 0.0, 0.0, 0.0, 0.0 ), radius=1, stacks=20, slices=20 ) -> None:
        self.sphere = gluNewQuadric()

        self.translate = translate
        self.rotation = rotation

        self.radius = radius
        self.stacks = stacks
        self.slices = slices

        return
    
    def update( self ) -> None:
        return

    def draw( self ) -> None:
    #def draw_sphere(radius, slices, stacks, position : Tuple = (0,0,0)):
        """Draws a sphere using OpenGL with the given radius, slices, and stacks."""
        glPushMatrix()
        glRotatef( self.rotation[0], self.rotation[1], self.rotation[2], self.rotation[3] ); 
        glTranslatef( self.translate[0], self.translate[1], self.translate[2] ); 

        for i in range( self.stacks ):
            lat0 = np.pi * (-0.5 + float(i) / self.stacks)  # latitude
            z0 = self.radius * np.sin(lat0)
            r0 = self.radius * np.cos(lat0)

            lat1 = np.pi * (-0.5 + float(i + 1) / self.stacks)  # latitude
            z1 = self.radius * np.sin(lat1)
            r1 = self.radius * np.cos(lat1)

            glBegin(GL_QUAD_STRIP)
            for j in range( self.slices + 1 ):
                lng = 2 * np.pi * float(j) / self.slices  # longitude
                x = np.cos(lng)
                y = np.sin(lng)

                # Vertex at (x, y, z)
                # transition to glTranslatef please
                glNormal3f( (x * r0), (y * r0), z0)
                glVertex3f( (x * r0), (y * r0), z0)  # Vertex for the first latitude

                glNormal3f( (x * r1), (y * r1), z1)
                glVertex3f( (x * r1), (y * r1), z1)  # Vertex for the second latitude
            glEnd()
        glPopMatrix()