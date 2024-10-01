import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

from gameObjects.gameObject import GameObject

class Cube( GameObject ):
    def __init__( self , translate=( 0.0, 0.0, 0.0 ), rotation=( 0.0, 0.0, 0.0, 0.0 ) ) -> None:
        self.translate = translate
        self.rotation = rotation
    
        self.vertices = [
            ( 1, 1, -1 ),  # Top right front
            ( 1, -1, -1 ), # Bottom right front
            ( -1, -1, -1 ),# Bottom left front
            ( -1, 1, -1 ), # Top left front
            ( 1, 1, 1 ),   # Top right back
            ( 1, -1, 1 ),  # Bottom right back
            ( -1, -1, 1 ), # Bottom left back
            ( -1, 1, 1 ),  # Top left back
        ]

        self.edges = [
            ( 0, 1 ), ( 1, 2 ), ( 2, 3 ), ( 3, 0 ),  # Front face
            ( 4, 5 ), ( 5, 6 ), ( 6, 7 ), ( 7, 4 ),  # Back face
            ( 0, 4 ), ( 1, 5 ), ( 2, 6 ), ( 3, 7 )   # Connect front and back
        ]

    def update( self ) -> None:
        return

    def draw( self ) -> None:
        """Draws a wireframe cube with colored axes."""
        return
        glPushMatrix()
        glRotatef( self.rotation[0], self.rotation[1], self.rotation[2], self.rotation[3] ); 
        glTranslatef( self.translate[0], self.translate[1], self.translate[2] ); 

        # Draw the edges of the cube
        glBegin( GL_LINES )
        for edge in self.edges:
            for vertex in edge:
                glColor3f( 1.0, 1.0, 1.0 )  # White color for cube edges
                glVertex3fv( self.vertices[vertex] )
        glEnd(  )

        # Draw colored axes
        # X-axis ( Red )
        glBegin( GL_LINES )
        glColor3f( 1.0, 0.0, 0.0 )  # Red color
        glVertex3f( -2, 0, 0 )  # Start point of X-axis
        glVertex3f( 2, 0, 0 )   # End point of X-axis
        glEnd(  )

        # Y-axis ( Green )
        glBegin( GL_LINES )
        glColor3f( 0.0, 1.0, 0.0 )  # Green color
        glVertex3f( 0, -2, 0 )  # Start point of Y-axis
        glVertex3f( 0, 2, 0 )   # End point of Y-axis
        glEnd(  )

        # Z-axis ( Blue )
        glBegin( GL_LINES )
        glColor3f( 0.0, 0.0, 1.0 )  # Blue color
        glVertex3f( 0, 0, -2 )  # Start point of Z-axis
        glVertex3f( 0, 0, 2 )   # End point of Z-axis
        glEnd(  )

        glPopMatrix()