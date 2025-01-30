import math
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

from modules.context import Context

import numpy as np

class Skybox( Context ):
    """This class is responsible for setting up the VAO and VBO for the skybox, also rendering commands to draw the skybox"""
    def __init__( self, context ):
        """Handles VAO, VBO creation for the skybox
        
        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )

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
        """Issue render commands to draw the skybox"""
        self.renderer.use_shader( self.renderer.skybox )

        # bind projection matrix
        glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection )

        # viewmatrix
        glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view )

        self.context.cubemaps.bind( self.context.environment_map, GL_TEXTURE0, "sEnvironment", 0 )

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