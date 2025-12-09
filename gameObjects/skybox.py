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
        #glBufferData( GL_ARRAY_BUFFER, self.skyboxVertices, GL_STATIC_DRAW );
        glBufferData(GL_ARRAY_BUFFER, self.skyboxVertices.nbytes, self.skyboxVertices, GL_STATIC_DRAW)
        glBindBuffer( GL_ARRAY_BUFFER, 0 );

        glBindVertexArray( self.VAO );
        glEnableVertexAttribArray(0);
        glVertexAttribPointer( 0, 3, GL_FLOAT, GL_FALSE, 3 * self.skyboxVertices.itemsize, None );

        glBindBuffer( GL_ARRAY_BUFFER, 0 );
        glBindVertexArray( 0 );

        # procedural
        self.procedural : bool = True

    def draw( self ) -> None:
        """Issue render commands to draw the skybox"""

        if self.procedural:
            self.renderer.use_shader( self.renderer.skybox_proc )
        else:
            self.renderer.use_shader( self.renderer.skybox )

        # bind projection matrix
        glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection )

        # viewmatrix
        glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view )

        if self.procedural:
            _sun = self.scene.getSun()
            _sun_active = _sun and _sun.hierachyActive()

            if not self.renderer.game_runtime:
                _sun_active = _sun_active and _sun.hierachyVisible()

            light_dir   = _sun.transform.local_position if _sun_active else self.settings.default_light_color
            light_color = _sun.light_color              if _sun_active else self.settings.default_ambient_color

            glUniform3f( self.renderer.shader.uniforms["uSkyColor"], 0.4, 0.6, 1.0)
            glUniform3f( self.renderer.shader.uniforms["uHorizonColor"], 0.9, 0.9, 1.0)
            glUniform3f( self.renderer.shader.uniforms["uGroundColor"], 0.2, 0.25, 0.3)

            glUniform3f( self.renderer.shader.uniforms["uSunDirection"], light_dir[0], light_dir[1], light_dir[2] )
            glUniform3f( self.renderer.shader.uniforms["uSunColor"], light_color[0], light_color[1], light_color[2] )

        else:
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