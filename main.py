import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import math

from modules.renderer import Renderer
from gameObjects.cube import Cube
from gameObjects.sphere import Sphere
from gameObjects.mesh import Mesh
from gameObjects.sun import Sun

renderer = Renderer()
renderer.setup_frustum_mvp()

gameObjects = []

def addGameObject( object ) -> int:
    index = len(gameObjects)
    gameObjects.append( object )
    return index

sun = addGameObject( Sun( renderer, translate=(-2, 0, 0) ) )

addGameObject( Cube( translate=(0, 0, 0), rotation=(45, 1, 1, 1) ) )
addGameObject( Sphere( translate=(-4, 0, 0) ) )
addGameObject( Sphere( translate=(0, 0, 0) ) )
addGameObject( Sphere( translate=(-2, 0, 0) ) )
addGameObject( Mesh( translate=(-16, 0, 0), filename="C:/Github-workspace/EmberEngine/assets/models/Tree/tree.obj" ) )

while renderer.running:
    events = pygame.event.get()
    renderer.event_handler( events )

    if not renderer.paused:
        renderer.begin_frame()

        # plane
        glColor4f(0.7, 0.0, 0.3, 1)
        glBegin(GL_QUADS)
        glVertex3f( -10, -10, -2 )
        glVertex3f( 10, -10, -2 )
        glVertex3f( 10, 10, -2 )
        glVertex3f( -10, 10, -2 )
        glEnd()

        for gameObject in gameObjects:
            gameObject.update();

        for gameObject in gameObjects:
            gameObject.draw();

        renderer.end_frame()
pygame.quit()