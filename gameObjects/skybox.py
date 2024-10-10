import math
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

from modules.renderer import Renderer

import numpy as np

class Skybox:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer

        size = 200
        self.skyboxVertices = np.array([
            # positions          
            -size,  size, -size,
            -size, -size, -size,
             size, -size, -size,
             size, -size, -size,
             size,  size, -size,
            -size,  size, -size,

            -size, -size,  size,
            -size, -size, -size,
            -size,  size, -size,
            -size,  size, -size,
            -size,  size,  size,
            -size, -size,  size,

             size, -size, -size,
             size, -size,  size,
             size,  size,  size,
             size,  size,  size,
             size,  size, -size,
             size, -size, -size,

            -size, -size,  size,
            -size,  size,  size,
             size,  size,  size,
             size,  size,  size,
             size, -size,  size,
            -size, -size,  size,

            -size,  size, -size,
             size,  size, -size,
             size,  size,  size,
             size,  size,  size,
            -size,  size,  size,
            -size,  size, -size,

            -size, -size, -size,
            -size, -size,  size,
             size, -size, -size,
             size, -size, -size,
            -size, -size,  size,
             size, -size,  size
        ], dtype='float32')

        self.VBO = glGenBuffers( 1 );
        self.VAO = glGenVertexArrays( 1 );

        glBindBuffer( GL_ARRAY_BUFFER, self.VBO );
        glBufferData( GL_ARRAY_BUFFER, self.skyboxVertices, GL_STATIC_DRAW );
        glBindBuffer( GL_ARRAY_BUFFER, 0 );

        glBindVertexArray( self.VAO );
        glEnableVertexAttribArray(0);
        glVertexAttribPointer( 0, 3, GL_FLOAT, GL_FALSE, 3 * self.skyboxVertices.itemsize, None );

        glBindBuffer( GL_ARRAY_BUFFER, 0 );
        glBindVertexArray( 0 );

    def draw( self ) -> None:

        glDisable(GL_DEPTH_TEST);
        glBindVertexArray( self.VAO )

        glBindBuffer( GL_ARRAY_BUFFER, self.VBO );
        glEnableVertexAttribArray( 0 )
        glVertexAttribPointer( 0, 3, GL_FLOAT, GL_FALSE, 3 * self.skyboxVertices.itemsize, None )

        glDrawArrays(GL_TRIANGLES, 0, 36);
         
        glEnable(GL_DEPTH_TEST);
        glBindBuffer( GL_ARRAY_BUFFER, 0 );
        glBindVertexArray( 0 )
        glUseProgram(0);

        return