import os
from pathlib import Path
from typing import List

#import site
#print(site.getsitepackages())



import pygame
from pygame.locals import *
from pyrr import matrix44, Vector3

from OpenGL.GL import *
from OpenGL.GLU import *

import math
import numpy as np

from modules.imgui import ImGui
from modules.jsonHandling import JsonHandler
from modules.renderer import Renderer
from modules.settings import Settings
from modules.cubemap import Cubemap
from modules.images import Images
from modules.models import Models
from modules.material import Material

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.sun import Sun
from gameObjects.skybox import Skybox

class EmberEngine:
    def __init__( self ) -> None:
        self.settings   : Settings = Settings()

        self.renderer   : Renderer = Renderer( self )
        self.imgui      : ImGui = ImGui( self )

        self.gameObjects : List[GameObject] = []

        self.images     : Images = Images( self )
        self.materials  : Material = Material( self )
        self.models     : Models = Models( self )
        self.cubemaps   : Cubemap = Cubemap( self )
        self.skybox     : Skybox = Skybox( self )
        
        # default material
        self.defaultMaterial = self.materials.buildMaterial( )

        #default object
        self.addGameObject( Mesh( self,
                        name        = "Default cube",
                        material    = self.defaultMaterial,
                        translate   = [ 0, 1, 0 ],
                        scale       = [ 1, 1, 1 ],
                        rotation    = [ 0.0, 0.0, 80.0 ]
                    ) )

        self.setupSun()

        self.light_color     = ( 1.0, 1.0, 1.0, 1.0 )
        self.ambient_color   = ( 0.3, 0.3, 0.3, 1.0 )

        self.loadDefaultEnvironment()

    def loadDefaultEnvironment( self ) -> None:
        self.environment_map = self.cubemaps.loadDefaultCubemap()

    def setupSun( self ) -> None:
        self.sun = self.addGameObject( Sun( self,
                        name        = "sun",
                        model_file  = f"{self.settings.engineAssets}models\\sphere\\model.obj",
                        translate   = [1, -1, 1],
                        scale       = [ 0.5, 0.5, 0.5 ],
                        rotation    = [ 0.0, 0.0, 80.0 ]
                    ) )

    def addGameObject( self, object : GameObject ) -> int:
        index = len( self.gameObjects )
        self.gameObjects.append( object )

        return index

    def draw_grid( self ):
        self.renderer.use_shader( self.renderer.color )
        # bind projection matrix
        glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection )

        # viewmatrix
        glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view )

        # color
        grid_color = self.settings.grid_color
        glUniform4f( self.renderer.shader.uniforms['uColor'],  grid_color[0],  grid_color[1], grid_color[2], 1.0 )
                
        size = self.settings.grid_size
        spacing = self.settings.grid_spacing

        # Draw the grid lines on the XZ plane
        for i in np.arange(-size, size + spacing, spacing):
            # Draw lines parallel to Z axis
            glBegin(GL_LINES)
            glVertex3f(i, 0, -size)
            glVertex3f(i, 0, size)
            glEnd()

            # Draw lines parallel to X axis
            glBegin(GL_LINES)
            glVertex3f(-size, 0, i)
            glVertex3f(size, 0, i)
            glEnd()

    def run( self ) -> None:
        while self.renderer.running:
            events = pygame.event.get()
            self.renderer.event_handler( events )

            if not self.renderer.paused:
                self.renderer.begin_frame()

                #
                # skybox
                #
                self.skybox.draw()

                #
                # grid
                #
                self.draw_grid()
                
                #
                # general
                #
                self.renderer.use_shader( self.renderer.general )
                glUniform1i( self.renderer.shader.uniforms['in_renderMode'], self.renderer.renderMode )

                # projection matrix can be bound at start
                # bind projection matrix
                glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection )
                
                # viewmatrix
                glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view )
                
                # camera
                camera_pos = self.renderer.cam.camera_pos
                glUniform4f( self.renderer.shader.uniforms['u_ViewOrigin'], camera_pos[0], camera_pos[1], camera_pos[2], 0.0 )

                # sun direction/position and color
                light_dir = self.gameObjects[self.sun].translate
                glUniform4f( self.renderer.shader.uniforms['in_lightdir'], light_dir[0], light_dir[1], light_dir[2], 0.0 )
                glUniform4f( self.renderer.shader.uniforms['in_lightcolor'], self.light_color[0], self.light_color[1], self.light_color[2], 1.0 )
                glUniform4f( self.renderer.shader.uniforms['in_ambientcolor'], self.ambient_color[0], self.ambient_color[1], self.ambient_color[2], 1.0 )

                # trigger update function in registered gameObjects
                for gameObject in self.gameObjects:
                    gameObject.onUpdate();

                self.renderer.end_frame()

        self.renderer.shutdown()

if __name__ == '__main__':
    app = EmberEngine()
    app.run()