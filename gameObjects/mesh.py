import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

from gameObjects.gameObject import GameObject
from modules.objLoader import ObjLoader

import pathlib

class Mesh( GameObject ):
    def onStart( self ) -> None:
        self.model = self.models.loadOrFind( "cottage/cottage.obj" )
        self.texture = self.images.loadOrFind( "cube.png" )

    def onUpdate( self ) -> None:
        self.models.bind( self.model )

        glUseProgram( self.renderer.shader.program )

        # texture
        self.images.bind( self.texture )

        # create and bind model matrix
        glUniformMatrix4fv( self.renderer.uMMatrix, 1, GL_FALSE, self._createModelMatrix() )
        
        self.models.drawArrays( self.model )     