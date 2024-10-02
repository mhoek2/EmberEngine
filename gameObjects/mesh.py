import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

from modules.files import FileHandler
from gameObjects.gameObject import GameObject

import pathlib
from objloader import *

class Mesh( GameObject ):
    def __init__( self, translate=( 0.0, 0.0, 0.0 ), rotation=( 0.0, 0.0, 0.0, 0.0 ), filename="" ) -> None:
        self.translate = translate
        self.rotation = rotation
        self.filename = filename;

        self.vertices = []
        self.loadMesh()
        
        return
    
    def loadMesh( self ) -> None:
        self.file = FileHandler( self.filename )
        obj_file = pathlib.Path( self.filename )
        
        with obj_file.open('r') as file:
            for line in file:
                if line.startswith( 'v ' ):  # Vertex line
                    parts = line.split()  # Split the line into parts
                    self.vertices.append( ( float(parts[1]), float(parts[2]), float(parts[3]) ) )
    

        # transition to glTranslatef please
        #self.translated_vertices = [
        #    (vertex[0] + self.position[0], 
        #     vertex[1] + self.position[1], 
        #     vertex[2] + self.position[2])
        #    for vertex in self.vertices
        #]

        return

    def update( self ) -> None:
        return

    def draw( self ) -> None:
        glPushMatrix()
        glRotatef( self.rotation[0], self.rotation[1], self.rotation[2], self.rotation[3] ); 
        glTranslatef( self.translate[0], self.translate[1], self.translate[2] ); 

        glBegin( GL_TRIANGLES )
        for vertex in self.vertices:
            glColor3f( 1.0, 1.0, 1.0 )
            glVertex3f( vertex[0], vertex[1], vertex[2] )
        glEnd()

        glPopMatrix()
        return