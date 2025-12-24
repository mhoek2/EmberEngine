import math
import pygame
from pygame.locals import *
from pyrr import matrix44, Matrix44

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

        self.realtime = False

        self.procedural_cubemap = None
        self.procedural_cubemap_size = 256
        self.procedural_cubemap_fbo = None
        self.procedural_cubemap_update = False

        size = 256
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

    def extract_procedural_cubemap( self, scene : "SceneManager.Scene" = None ) -> None:
        """Extract the prodedural sky to a cubemap.
        
        Used in:

            - Environmental reflections (IBL)
            - Optimization when the procedural skybox is NOT in realtime mode.

        Steps:

            1. For each of the 6 cubemap faces:
                - Position the camera at the origin
                - Orient the camera using the face side look direction and up vector
                - Set a 90deg Field-of-view projection
            2. Render the procedural skybox using the same pipeline as realtime mode
               (i.e., call self._draw_procedural, with extract_cubemap=True)
            3. Render into the procedural-sky framebuffer and texture.
        
        :param scene: The scene data
        :type scene: Scene
        """
        if self.procedural_cubemap is None:
            print("Procedural cubemap GlTexture is not invalid")
            return

        if self.procedural_cubemap_fbo is None:
            print("Procedural cubemap FBO is not invalid")
            return

        if scene is None:
            scene = self.scene.getCurrentScene()

        _current_shader = self.renderer.shader
        _current_fbo    = self.renderer.current_fbo

        # Set FBO and drawbuffer
        glBindFramebuffer( GL_FRAMEBUFFER, self.procedural_cubemap_fbo )
        glDrawBuffer( GL_COLOR_ATTACHMENT0 )

        cubemap = self.context.cubemaps.cubemap[self.procedural_cubemap]
        size = self.procedural_cubemap_size

        targets = [
            np.array([-1, 0, 0]),  # +X
            np.array([1, 0, 0]),   # -X
            np.array([0,-1, 0]),   # +Y
            np.array([0, 1, 0]),   # -Y
            np.array([0, 0, 1]),   # +Z
            np.array([0, 0,-1])    # -Z
        ]

        ups = [
            np.array([0, 1, 0]),    # +X 
            np.array([0, 1, 0]),    # -X 
            np.array([0, 0, 1]),    # +Y
            np.array([0, 0,-1]),    # -Y
            np.array([0, 1, 0]),    # +Z
            np.array([0, 1, 0])     # -Z
        ]

        _projection : Matrix44 = matrix44.create_perspective_projection_matrix( 
            fovy    = 90, 
            aspect  = 1.0, 
            near    = 0.1, 
            far     = 1000
        )

        for i in range(6):
            _view = matrix44.create_look_at( np.zeros(3), targets[i], ups[i] )

            glFramebufferTexture2D( GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                                   GL_TEXTURE_CUBE_MAP_POSITIVE_X + i,
                                   cubemap, 0 )

            status = glCheckFramebufferStatus( GL_FRAMEBUFFER )
            if status != GL_FRAMEBUFFER_COMPLETE:
                print( "Framebuffer error:", hex( status ) )
                return

            glViewport( 0, 0, self.procedural_cubemap_size, self.procedural_cubemap_size )
            glDisable( GL_DEPTH_TEST )

            self._draw_procedural( 
                scene, 
                _view, 
                _projection, 
                extract_cubemap = True
            )

        # reset renderer
        if _current_shader:
            self.renderer.use_shader( _current_shader )

        if _current_fbo:
            self.renderer.bind_fbo( _current_fbo )

        self.renderer.setup_projection_matrix()
 
        # Update Gui preview
        if self.context.gui.initialized:
            self.context.gui.scene_settings.test_cubemap_update = True

    def create_procedural_cubemap( self, scene : "SceneManager.Scene" = None ) -> int:
        """Create the procedural cubemap Texture:GL_TEXTURE_CUBE_MAP and FBO, then extract
        
        :param scene: The scene data
        :type scene: Scene
        :return: The index of the texture array in  modules.Cubemap.cubemaps[]
        :rtype: int
        """
        if scene is None:
            scene = self.scene.getCurrentScene()

        # Create textures
        if self.procedural_cubemap is None:
            self.procedural_cubemap = self.context.cubemaps._num_cubemaps

            size = self.procedural_cubemap_size

            cubemap = self.context.cubemaps.cubemap[self.procedural_cubemap]

            glBindTexture( GL_TEXTURE_CUBE_MAP, cubemap )
 
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

            self.context.cubemaps._num_cubemaps += 1

        # Create FBO
        if self.procedural_cubemap_fbo is None:
            self.procedural_cubemap_fbo = glGenFramebuffers(1)
        
        # Depth renderbuffer (not required)
        #depth_rb = glGenRenderbuffers(1)
        #glBindRenderbuffer(GL_RENDERBUFFER, depth_rb)
        #glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, size, size)
        #glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, depth_rb)

        # Extract to cubemap sides
        self.procedural_cubemap_update = True

        return self.procedural_cubemap

    def __set_mvp( self, view : Matrix44 = None, projection : Matrix44 = None ) -> None:
        """Upload the view an projection matrices to the GPU uniform
        
        :param view: The view matrix, None to use current renderer matrix
        :type view: Matrix44
        :param projection: The projection matrix, None to use current renderer matrix
        :type projection: Matrix44
        """
        if projection is None:
            projection = self.renderer.projection

        if view is None:
            view = self.renderer.view

        glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, projection )
        glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, view )

    def _draw_procedural( self, 
                          scene             : "SceneManager.Scene", 
                          view              : Matrix44 = None, 
                          projection        : Matrix44 = None, 
                          extract_cubemap   : bool = False
        ) -> None:
        """Draw the procedural sky, ether realtime, or to extract a cubemap
        
        :param scene: The scene data
        :type scene: Scene
        :param view: The view matrix, None for auto
        :type view: Matrix44
        :param projection: The projection matrix, None for auto
        :type projection: Matrix44
        :param extract_cubemap: The scene data
        :type extract_cubemap: bool
        """
        if not scene:
            return

        self.renderer.use_shader( self.renderer.skybox_proc )

        self.__set_mvp( view, projection )

        _sun = self.scene.getSun()
        _sun_active = _sun and _sun.hierachyActive()

        if not self.renderer.game_runtime:
            _sun_active = _sun_active and _sun.hierachyVisible()

        light_dir   = _sun.transform.local_position if _sun_active else self.settings.default_light_color
        light_color = _sun.light.light_color        if _sun_active else self.settings.default_ambient_color

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

        # flip the vertex.x handedness for cubemap extraction
        glUniform1i( self.renderer.shader.uniforms['uExtractCubemap'], int(extract_cubemap) )

        self.__render()

    def _draw_skybox( self ):
        """Render a cubemap to the skybox geometry
        
            This can be either a cubemap from assets, or a cubemap extracted from the procedural sky
        """
        self.renderer.use_shader( self.renderer.skybox )

        self.__set_mvp()

        self.context.cubemaps.bind( self.context.environment_map, GL_TEXTURE0, "sEnvironment", 0 )

        self.__render()

    def __render( self ):
        """Issue the glDrawArrays drawcall, then reset"""
        glDisable(GL_DEPTH_TEST);
        glBindVertexArray( self.VAO )

        glBindBuffer( GL_ARRAY_BUFFER, self.VBO );
        glEnableVertexAttribArray( 0 )
        glVertexAttribPointer( 0, 3, GL_FLOAT, GL_FALSE, 3 * self.skyboxVertices.itemsize, None )

        glDrawArrays(GL_TRIANGLES, 0, 36);
         
        # reset 
        glEnable(GL_DEPTH_TEST);
        glBindBuffer( GL_ARRAY_BUFFER, 0 );
        glBindVertexArray( 0 )
        glUseProgram(0);

    def draw( self,  scene : "SceneManager.Scene" ) -> None:
        """Issue render commands to draw the skybox"""
        if not scene:
            return

        _sky_type : Skybox.Type_ = Skybox.Type_( scene["sky_type"] )
        use_procedural : bool = _sky_type == Skybox.Type_.procedural

        # update requested
        if self.procedural_cubemap_update:
            if use_procedural:
                self.extract_procedural_cubemap()

                # update Gui preview
                if self.context.gui.initialized:
                    self.context.gui.scene_settings.test_cubemap_update = True


            self.procedural_cubemap_update = False

        if use_procedural and self.realtime:
            self._draw_procedural( scene )
        else:
            self._draw_skybox()

        return