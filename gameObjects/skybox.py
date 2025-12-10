import math
import pygame
from pygame.locals import *
from pyrr import matrix44

from OpenGL.GL import *
from OpenGL.GLU import *

from modules.context import Context

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from modules.scene import SceneManager

import numpy as np
import enum

class Skybox( Context ):
    class Type_(enum.IntEnum):
        procedural      = 0             # (= 0)
        skybox          = enum.auto()   # (= 1)

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

    def create_procedural_cubemap( self, scene : "SceneManager.Scene" )  -> int:

        index = self.context.cubemaps._num_cubemaps

        glBindTexture( GL_TEXTURE_CUBE_MAP, index )
        size : int = 1024

        for i in range(6):
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i,
                         0, GL_RGBA16F,
                         size, size, 0,
                         GL_RGBA, GL_FLOAT, None)

        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)

        # Create FBO
        fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, fbo)

        # Create depth renderbuffer
        depth_rb = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, depth_rb)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, size, size)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depth_rb)

        # Set draw buffer
        glDrawBuffer(GL_COLOR_ATTACHMENT0)

        # Cubemap face orientations
        targets = [
            np.array([1, 0, 0]),   # +X
            np.array([-1, 0, 0]),  # -X
            np.array([0, 1, 0]),   # +Y
            np.array([0,-1, 0]),   # -Y
            np.array([0, 0, 1]),   # +Z
            np.array([0, 0,-1])    # -Z
        ]

        ups = [
            np.array([0,-1,0]),
            np.array([0,-1,0]),
            np.array([0, 0,1]),
            np.array([0, 0,-1]),
            np.array([0,-1,0]),
            np.array([0,-1,0])
        ]

        projection = matrix44.create_perspective_projection_matrix( 
            fovy    = 90, 
            aspect  = 1.0, 
            near    = 0.1, 
            far     = 1000
        )

        # Render each face
        for i in range(6):
            glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                                   GL_TEXTURE_CUBE_MAP_POSITIVE_X + i,
                                   index, 0)

            status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
            if status != GL_FRAMEBUFFER_COMPLETE:
                print("Framebuffer error:", hex(status))
                return

            glViewport(0, 0, size, size)
            glDisable(GL_DEPTH_TEST)

            #view = lookAt(np.zeros(3), targets[i], ups[i])
            view = matrix44.create_look_at(np.zeros(3), targets[i], ups[i])

            # Render procedural skybox using THIS projection + view
            self.draw(scene, projection, view)

        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        self.renderer.setup_projection_matrix( 
            size = self.renderer.viewport_size 
        )
        glEnable(GL_DEPTH_TEST)

        self.context.cubemaps._num_cubemaps += 1

        return index

    def draw( self, scene : "SceneManager.Scene" = None, projection = None, view = None ) -> None:
        """Issue render commands to draw the skybox"""

        if not scene:
            return

        # check this for performance!
        if projection is None:
            projection = self.renderer.projection

        if view is None:
            view = self.renderer.view

        _sky_type : Skybox.Type_ = Skybox.Type_( scene["sky_type"] )

        if _sky_type == Skybox.Type_.procedural:
            self.renderer.use_shader( self.renderer.skybox_proc )
        else:
            self.renderer.use_shader( self.renderer.skybox )

        # bind projection matrix
        glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, projection )

        # viewmatrix
        glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, view )

        if _sky_type == Skybox.Type_.procedural:
            _sun = self.scene.getSun()
            _sun_active = _sun and _sun.hierachyActive()

            if not self.renderer.game_runtime:
                _sun_active = _sun_active and _sun.hierachyVisible()

            light_dir   = _sun.transform.local_position if _sun_active else self.settings.default_light_color
            light_color = _sun.light_color              if _sun_active else self.settings.default_ambient_color

            _sky_color      = scene["procedural_sky_color"]
            _horizon_color  = scene["procedural_horizon_color"]
            _ground_color   = scene["procedural_ground_color"]

            _sunset_color   = scene["procedural_sunset_color"]
            _night_color    = scene["procedural_night_color"]

            _night_brightness = scene["procedural_night_brightness"]

            glUniform3f( self.renderer.shader.uniforms["uSkyColor"], _sky_color[0], _sky_color[1], _sky_color[2] )
            glUniform3f( self.renderer.shader.uniforms["uHorizonColor"], _horizon_color[0], _horizon_color[1], _horizon_color[2] )
            glUniform3f( self.renderer.shader.uniforms["uGroundColor"], _ground_color[0], _ground_color[1], _ground_color[2] )

            glUniform3f( self.renderer.shader.uniforms["uSunsetColor"], _sunset_color[0], _sunset_color[1], _sunset_color[2] )
            glUniform3f( self.renderer.shader.uniforms["uNightColor"], _night_color[0], _night_color[1], _night_color[2] )

            glUniform3f( self.renderer.shader.uniforms["uSunDirection"], light_dir[0], light_dir[1], light_dir[2] )
            glUniform3f( self.renderer.shader.uniforms["uSunColor"], light_color[0], light_color[1], light_color[2] )
            
            glUniform1f( self.renderer.shader.uniforms["uNightBrightness"], _night_brightness )

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