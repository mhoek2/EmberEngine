import math
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

from gameObjects.gameObject import GameObject

class Sun( GameObject ):
    def onStart( self ) -> None:
        mat = self.materials.buildMaterial( 
            albedo  = f"{self.settings.engine_texture_path}sun\\albedo.jpg",
            r       = f"{self.settings.engine_texture_path}sun\\roughness.jpg",
        )

        self.model = self.models.loadOrFind( self.model_file, mat )

        self.angle          = 1.0
        self.anim_speed     = 2.0
        self.anim_radius    = 8.0

    def onUpdate( self ) -> None:
        #glUseProgram( self.renderer.shader.program )

        if self.renderer.animSun:
            self.angle += self.renderer.deltaTime * self.anim_speed 

            self.translate[1] = self.anim_radius * math.cos( self.angle )  # Update x position
            self.translate[2] = self.anim_radius * math.sin( self.angle )

        # environment should be none, or whiteimage..
        self.cubemaps.bind( self.context.environment_map, GL_TEXTURE4, "sEnvironment", 4 )

        # brdf lut
        self.images.bind( self.context.cubemaps.brdf_lut, GL_TEXTURE5, "sBRDF", 5 )

        # create and bind model matrix
        glUniformMatrix4fv( self.renderer.shader.uniforms['uMMatrix'], 1, GL_FALSE, self._createModelMatrix() )
        
        self.models.draw( self.model ) 