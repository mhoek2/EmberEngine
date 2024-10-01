import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import math

from modules.jsonHandling import JsonHandler
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

sun = addGameObject( Sun( renderer, 
                         translate=(-2, 0, 0), 
                         color=(0.7, 0.7, 0.0),
                         diffuse=(.0, 1.0, 0.7),
                         ambient=(0.0, 0.2, 0.2),
                         anim_radius=10,
                         anim_speed=2
                   ) )

file = JsonHandler( 'C:/Github-workspace/EmberEngine/json/lang.json' )
json_content = file.getJson();

def JsonToVertices() -> None:
    gameObjects.append( Cube() )

    scale_modifier = 1

    for lang in json_content['languages']:

        coords = lang['coordinates']

        translation = ( coords['x'] * scale_modifier,
                        coords['y'] * scale_modifier,
                        coords['z'] * scale_modifier
        )

        color = (1.0, 1.0, 1.0) 
        radius = 0.02

        if lang['name'] == "Python":
            color = (1.0, 1.0, 0.0) 
            radius = 0.05

        elif lang['name'] == "C++":
            color = (0.0, 1.0, 1.0)
            radius = 0.05


        gameObjects.append( Sphere( 
            translate=translation,
            radius=radius,
            stacks=5,
            slices=10,
            color=color
        ) )

JsonToVertices()

while renderer.running:
    events = pygame.event.get()
    renderer.event_handler( events )

    if not renderer.paused:
        renderer.begin_frame()

        # plane
        glColor4f(1, 1, 1, 1)
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