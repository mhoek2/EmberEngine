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

    def onUpdate( self ) -> None:
        #glUseProgram( self.renderer.shader.program )

        # texture
        self.images.bind( self.texture, GL_TEXTURE0, "sTexture", 0 )
        self.images.bind( self.normals, GL_TEXTURE1, "sNormal", 1 )

        # create and bind model matrix
        glUniformMatrix4fv( self.renderer.uMMatrix, 1, GL_FALSE, self._createModelMatrix() )
        
        self.models.draw( self.model )     