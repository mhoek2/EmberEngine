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
        self.model = self.models.loadOrFind( "cube/cube.obj" )
        self.texture = self.images.loadOrFind( "cube.png" )

    def onUpdate( self ) -> None:
        #glVertexAttribPointer( self.renderer.aVertex, 3, GL_FLOAT, GL_FALSE, 0, self.vertices )
        #glVertexAttribPointer( self.renderer.aNormal, 3, GL_FLOAT, GL_FALSE, 0, self.normals )
        #glVertexAttribPointer( self.renderer.aTexCoord, 2, GL_FLOAT, GL_FALSE, 0, self.texcoords )
        
        # model
        #self.models.bind( self.model )
        #self.models.bind2( self.model )

        # texture
        #self.images.bind( self.texture )

        # create and bind view matrix
        #view = self.renderer.cam.get_view_matrix()
        #glUniformMatrix4fv( self.renderer.uVMatrix, 1, GL_FALSE, view )

        # create and bind model matrix
        #glUniformMatrix4fv( self.renderer.uMMatrix, 1, GL_FALSE, self._createModelMatrix() )

        self.models.bind2( self.model )
        self.images.bind( self.texture )
        glUniformMatrix4fv( self.renderer.uMMatrix, 1, GL_FALSE, self._createModelMatrix() )
        self.models.drawArrays( self.model )     