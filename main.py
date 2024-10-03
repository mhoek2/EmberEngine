from _pytest.monkeypatch import V
import pygame
from pygame.locals import *
from pyrr import matrix44, Vector3

from OpenGL.GL import *
from OpenGL.GLU import *

import math

from modules.jsonHandling import JsonHandler
from modules.renderer import Renderer
from modules.images import Images
from modules.models import Models

from gameObjects.cube import Cube
from gameObjects.sphere import Sphere
from gameObjects.mesh import Mesh
from gameObjects.sun import Sun
from gameObjects.fullcube import FullCube

class EmberEngine:
    def __init__( self ) -> None:  
        self.renderer = Renderer()
        self.renderer.setup_projection()

        self.gameObjects = []

        self.models = Models( self )
        self.images = Images( self )

        self.addGameObject( Mesh( self,
                                    translate=(0, 1, 0),
                                    scale=( 1, 1, 1 ),
                                    rotation=( 0.0, 0.0, 80.0 )
                        ) )

        self.addGameObject( Mesh( self,
                                    translate=(3, 1, 0),
                                    scale=( 1, 1, 1 ),
                                    rotation=( 0.0, 0.0, 80.0 )
                        ) )

        self.addGameObject( FullCube( self,
                                    translate=(0, 0, 0),
                                    scale=( 5, 0.01, 5 )
                       ) )

        self.addGameObject( FullCube( self,
                                    translate=(0, 0, 0),
                                    scale=( 1, 1, 1 )
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

                view = self.renderer.cam.get_view_matrix()
                glUniformMatrix4fv( self.renderer.uVMatrix, 1, GL_FALSE, view )

                camera_pos = self.renderer.cam.camera_pos
                glUniform4f( self.renderer.u_ViewOrigin, camera_pos[0], camera_pos[1], camera_pos[2], 0.0 )

                light_dir = (1.0, 0.0, 1.0, 1.0)
                glUniform4f( self.renderer.u_ViewOrigin, light_dir[0], light_dir[1], light_dir[2], light_dir[3] )

                # trigger update function in registered gameObjects
                for gameObject in self.gameObjects:
                    gameObject.onUpdate();

                self.renderer.end_frame()
        pygame.quit()

if __name__ == '__main__':
    app = EmberEngine()
    app.run()