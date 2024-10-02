import pygame
import pyrr

from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

from gameObjects.gameObject import GameObject

class FullCube( GameObject ):
    def onStart( self ) -> None:
        self._loadModel()

    def _loadModel( self ) -> None:
        _vertices = [
            ( 1.000000, -1.000000, -1.000000),
            ( 1.000000, -1.000000,  1.000000),
            (-1.000000, -1.000000,  1.000000),
            (-1.000000, -1.000000, -1.000000),
            ( 1.000000,  1.000000, -0.999999),
            ( 0.999999,  1.000000,  1.000001),
            (-1.000000,  1.000000,  1.000000),
            (-1.000000,  1.000000, -1.000000),
        ]
        _normals = [
            ( 0.000000, -1.000000,  0.000000),
            ( 0.000000,  1.000000,  0.000000),
            ( 1.000000,  0.000000,  0.000000),
            (-0.000000,  0.000000,  1.000000),
            (-1.000000, -0.000000, -0.000000),
            ( 0.000000,  0.000000, -1.000000),
        ]


        _texcoords = [
            (0.250043, 0.749957),
            (0.250043, 0.500000),
            (0.500000, 0.500000),
            (0.500000, 0.250043),
            (0.250043, 0.250043),
            (0.250044, 0.000087),
            (0.500000, 0.999913),
            (0.250043, 0.999913),
            (0.000087, 0.749956),
            (0.000087, 0.500000),
            (0.500000, 0.749957),
            (0.749957, 0.500000),
            (0.500000, 0.000087),
            (0.749957, 0.749957),
        ]
        _vertex_triangles = [
            (1, 2, 3),
            (7, 6, 5),
            (4, 5, 1),
            (5, 6, 2),
            (2, 6, 7),
            (0, 3, 7),
            (0, 1, 3),
            (4, 7, 5),
            (0, 4, 1),
            (1, 5, 2),
            (3, 2, 7),
            (4, 0, 7),
        ]

        _texture_triangles = [
            ( 0,  1,  2),
            ( 3,  4,  5),
            ( 6,  7,  0),
            ( 8,  9,  1),
            ( 1,  4,  3),
            (10,  2, 11),
            (10,  0,  2),
            (12,  3,  5),
            (10,  6,  0),
            ( 0,  8,  1),
            ( 2,  1,  3),
            (13, 10, 11),
        ]

        _normal_triangles = [
            (0, 0, 0),
            (1, 1, 1),
            (2, 2, 2),
            (3, 3, 3),
            (4, 4, 4),
            (5, 5, 5),
            (0, 0, 0),
            (1, 1, 1),
            (2, 2, 2),
            (3, 3, 3),
            (4, 4, 4),
            (5, 5, 5),
        ]

        self.vertices = np.array([
            _vertices[index]
            for indices in _vertex_triangles
            for index in indices
        ])

        self.normals = np.array([
            _normals[index]
            for indices in _normal_triangles
            for index in indices
        ])

        self.texcoords = np.array([
            _texcoords[index]
            for indices in _texture_triangles
            for index in indices
        ])

    def _createModelMatrix( self ):
        """Create model matrix with translation, rotation and scale vectors"""
        model = pyrr.Matrix44.identity()
        model = model * pyrr.Matrix44.from_translation( pyrr.Vector3( [self.translate[0], self.translate[1], self.translate[2]] ) )
        model = model * pyrr.Matrix44.from_eulers(pyrr.Vector3([self.rotation[0], self.rotation[1], self.rotation[2]]))
        return model * pyrr.Matrix44.from_scale( pyrr.Vector3( [self.scale[0], self.scale[1], self.scale[2]] ) )

    def onUpdate( self ) -> None:
        glVertexAttribPointer( self.renderer.aVertex, 3, GL_FLOAT, GL_FALSE, 0, self.vertices )
        glVertexAttribPointer( self.renderer.aNormal, 3, GL_FLOAT, GL_FALSE, 0, self.normals )
        glVertexAttribPointer( self.renderer.aTexCoord, 2, GL_FLOAT, GL_FALSE, 0, self.texcoords )
        
        # create view matrix
        view = self.renderer.cam.get_view_matrix()
        glUniformMatrix4fv( self.renderer.uVMatrix, 1, GL_FALSE, view )

        # create model matrix
        glUniformMatrix4fv( self.renderer.uMMatrix, 1, GL_FALSE, self._createModelMatrix() )

        glDrawArrays( GL_TRIANGLES, 0, len(self.vertices)) 
        