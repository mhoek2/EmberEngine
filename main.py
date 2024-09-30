import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import math

from modules.renderer import Renderer

renderer = Renderer()
renderer.setup_frustum_mvp()
sphere = gluNewQuadric() 
renderer.setup_lighting()


def draw_cube():
    """Draws a wireframe cube with colored axes."""
    # Define the vertices of the cube
    vertices = [
        (1, 1, -1),  # Top right front
        (1, -1, -1), # Bottom right front
        (-1, -1, -1),# Bottom left front
        (-1, 1, -1), # Top left front
        (1, 1, 1),   # Top right back
        (1, -1, 1),  # Bottom right back
        (-1, -1, 1), # Bottom left back
        (-1, 1, 1),  # Top left back
    ]

    # Define the edges connecting the vertices
    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),  # Front face
        (4, 5), (5, 6), (6, 7), (7, 4),  # Back face
        (0, 4), (1, 5), (2, 6), (3, 7)   # Connect front and back
    ]

    # Draw the edges of the cube
    glBegin(GL_LINES)
    for edge in edges:
        for vertex in edge:
            glColor3f(1.0, 1.0, 1.0)  # White color for cube edges
            glVertex3fv(vertices[vertex])
    glEnd()

    # Draw colored axes
    # X-axis (Red)
    glBegin(GL_LINES)
    glColor3f(1.0, 0.0, 0.0)  # Red color
    glVertex3f(-2, 0, 0)  # Start point of X-axis
    glVertex3f(2, 0, 0)   # End point of X-axis
    glEnd()

    # Y-axis (Green)
    glBegin(GL_LINES)
    glColor3f(0.0, 1.0, 0.0)  # Green color
    glVertex3f(0, -2, 0)  # Start point of Y-axis
    glVertex3f(0, 2, 0)   # End point of Y-axis
    glEnd()

    # Z-axis (Blue)
    glBegin(GL_LINES)
    glColor3f(0.0, 0.0, 1.0)  # Blue color
    glVertex3f(0, 0, -2)  # Start point of Z-axis
    glVertex3f(0, 0, 2)   # End point of Z-axis
    glEnd()


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

        draw_cube()

        # sphere
        glTranslatef (3, 0, 2 )
        glColor4f( 0.9, 0.9, 0.9, 1 )
        gluSphere( sphere, 1.0, 32, 16 ) 

        # sphere
        glTranslatef( -3, 0, -2 )
        glColor4f( 0.9, 0.9, 0.0, 1 )
        gluSphere( sphere, 1.0, 32, 16 ) 

        renderer.end_frame()
pygame.quit()