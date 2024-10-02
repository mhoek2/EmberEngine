from _pytest.monkeypatch import V
import pygame
from pygame.locals import *
from pyrr import matrix44, Vector3

from OpenGL.GL import *
from OpenGL.GLU import *

import math

from modules.jsonHandling import JsonHandler
from modules.renderer import Renderer

from gameObjects.cube import Cube
from gameObjects.sphere import Sphere
from gameObjects.mesh import Mesh
from gameObjects.sun import Sun
from gameObjects.fullcube import FullCube

from modules.TextureLoader import load_texture_pygame as load_texture

class EmberEngine:
    def __init__( self ) -> None:  
        self.renderer = Renderer()
        self.renderer.setup_projection()

        self.gameObjects = []

        self.textures = glGenTextures(3)
        load_texture( "C:/Github-workspace/EmberEngine/assets/textures/cube.png", self.textures[0] )

        self.addGameObject( FullCube( self,
                                    translate=(-2, 0, 0),
                        ) )

        self.addGameObject( FullCube( self,
                                    translate=(2, 0, 0),
                                    scale=( 0.5, 0.5, 0.5 ),
                                    rotation=( 0.5, 0.0, 0.0 )
                        ) )

        # bind projection matrix
        glUniformMatrix4fv( self.renderer.uPMatrix, 1, GL_FALSE, self.renderer.projection )

    def addGameObject( self, object ) -> int:
        index = len( self.gameObjects )
        self.gameObjects.append( object )

        return index

    def run( self ) -> None:
        while self.renderer.running:
            events = pygame.event.get()
            self.renderer.event_handler( events )

            if not self.renderer.paused:
                self.renderer.begin_frame()

                # trigger update function in registered gameObjects
                for gameObject in self.gameObjects:
                    gameObject.onUpdate();

                self.renderer.end_frame()
        pygame.quit()

if __name__ == '__main__':
    app = EmberEngine()
    app.run()