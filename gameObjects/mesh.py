import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

from gameObjects.gameObject import GameObject

import pathlib

class Mesh( GameObject ):
    def onStart( self ) -> None:
        self.model = self.models.loadOrFind( self.model_file )
        self.texture = self.images.loadOrFind( self.texture_file )
        self.normals = self.images.loadOrFind( self.normals_file )
        self.physical = self.images.loadOrFind( self.phyiscal_file )

    def onUpdate( self ) -> None:
        #glUseProgram( self.renderer.shader.program )

        # texture
        self.images.bind( self.texture, GL_TEXTURE0, "sTexture", 0 )
        self.images.bind( self.normals, GL_TEXTURE1, "sNormal", 1 )
        self.images.bind( self.physical, GL_TEXTURE2, "sPhyiscal", 2 )

        # environment
        self.cubemaps.bind( self.context.environment_map, GL_TEXTURE3, "sEnvironment", 3 )

        # brdf lut
        self.images.bind( self.context.cubemaps.brdf_lut, GL_TEXTURE4, "sBRDF", 4 )

        # create and bind model matrix
        glUniformMatrix4fv( self.renderer.uMMatrix, 1, GL_FALSE, self._createModelMatrix() )
        
        self.models.draw( self.model )     