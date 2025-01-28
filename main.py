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

from modules.scene import SceneManager
from modules.console import Console
from modules.imgui import ImGui
from modules.jsonHandling import JsonHandler
from modules.renderer import Renderer
from modules.settings import Settings
from modules.cubemap import Cubemap
from modules.images import Images
from modules.models import Models
from modules.material import Material

from gameObjects.gameObject import GameObject
from gameObjects.camera import Camera
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.skybox import Skybox

class EmberEngine:
    def __init__( self ) -> None:
        self.settings   : Settings = Settings()
        
        self.asset_scripts : List[Path] = []
        self.findScripts()
        
        self.events     = pygame.event
        self.key        = pygame.key
        self.mouse      = pygame.mouse

        self.console    : Console = Console(self)
        self.scene      : SceneManager = SceneManager( self )
        self.renderer   : Renderer = Renderer( self )
        self.imgui      : ImGui = ImGui( self )
 
        self.gameObjects : List[GameObject] = []

        self.images     : Images = Images( self )
        self.materials  : Material = Material( self )
        self.models     : Models = Models( self )
        self.cubemaps   : Cubemap = Cubemap( self )
        self.skybox     : Skybox = Skybox( self )

        self.sun = -1

        self.light_color     = ( 1.0, 1.0, 1.0, 1.0 )
        self.ambient_color   = ( 0.3, 0.3, 0.3, 1.0 )
        self.roughnessOverride = -1
        self.metallicOverride = -1

        self.defaultMaterial = self.materials.buildMaterial( )

        self.scene.getScenes()
        self.scene.loadScene()

        self.loadDefaultEnvironment()

    def findScripts(self):
        """scan asset folder for .py files.
        perhaps there should be a separate thread for this
        that either updates periodicly, or tracks changes in assets folder
        - currently this is called every time 'Add Script' popup is opened' """
        self.asset_scripts = self.findDynamicScripts( self.settings.assets )

    def findDynamicScripts( self, path : str ) -> List[Path]:
        assets = Path( path ).resolve()
        return [file for file in assets.rglob("*.py")]

    def loadDefaultEnvironment( self ) -> None:
        self.environment_map = self.cubemaps.loadDefaultCubemap()

    def addEmptyGameObject( self ):
        return self.addGameObject( Mesh( self,
            name        = "Empty GameObject",
            material    = self.defaultMaterial,
            translate   = [ 0, 0, 0 ],
            scale       = [ 1, 1, 1 ],
            rotation    = [ 0.0, 0.0, 0.0 ]
        ) )

    def addDefaultCube( self ):
        return self.addGameObject( Mesh( self,
            name        = "Default cube",
            model_file  = f"{self.settings.engineAssets}models\\cube\\model.obj",
            material    = self.defaultMaterial,
            translate   = [ 0, 1, 0 ],
            scale       = [ 1, 1, 1 ],
            rotation    = [ 0.0, 0.0, 0.0 ]
        ) )

    def addDefaultCamera( self ):
        return self.addGameObject( Camera( self,
                        name        = "Camera",
                        model_file  = f"{self.settings.engineAssets}models\\camera\\model.fbx",
                        material    = self.defaultMaterial,
                        translate   = [ 0, 5, -10 ],
                        scale       = [ 1, 1, 1 ],
                        rotation    = [ -0.4, 0.0, 0.0 ],
                        scripts     = [ Path(f"{self.settings.assets}\\camera.py") ]
                    ) )

    def addDefaultLight( self ) -> None:
        return self.addGameObject( Light( self,
                        name        = "light",
                        model_file  = f"{self.settings.engineAssets}models\\sphere\\model.obj",
                        translate   = [1, -1, 1],
                        scale       = [ 0.5, 0.5, 0.5 ],
                        rotation    = [ 0.0, 0.0, 80.0 ]
                    ) )

    def addGameObject( self, object : GameObject ) -> int:
        index = len( self.gameObjects )
        self.gameObjects.append( object )

        return index

    def removeGameObject( self, obj : GameObject ):
        try:
            # we cant directly remove and rebuild the gameObject array.
            # so mark it removed, and do not store it on save.
            #self.gameObjects.remove( object )
            obj._removed = True
            obj.visible = False

            if isinstance( obj, Camera ) and obj is self.scene.getCamera():
                self.scene.setCamera( -1 )

        except:
            print("gameobject doesnt exist..")

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
            self.renderer.event_handler()

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

                # environment
                self.cubemaps.bind( self.environment_map, GL_TEXTURE4, "sEnvironment", 4 )

                # brdf lut
                self.images.bind( self.cubemaps.brdf_lut, GL_TEXTURE5, "sBRDF", 5 )

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
                light_dir = self.gameObjects[self.sun].translate if self.sun != -1 else (0.0, 0.0, 1.0)
                glUniform4f( self.renderer.shader.uniforms['in_lightdir'], light_dir[0], light_dir[1], light_dir[2], 0.0 )
                glUniform4f( self.renderer.shader.uniforms['in_lightcolor'], self.light_color[0], self.light_color[1], self.light_color[2], 1.0 )
                glUniform4f( self.renderer.shader.uniforms['in_ambientcolor'], self.ambient_color[0], self.ambient_color[1], self.ambient_color[2], 1.0 )

                glUniform1f( self.renderer.shader.uniforms['in_roughnessOverride'], self.roughnessOverride  )
                glUniform1f( self.renderer.shader.uniforms['in_metallicOverride'], self.metallicOverride )
                
                if self.settings.game_start:
                    self.console.clear()

                # trigger update function in registered gameObjects
                for gameObject in self.gameObjects:
                    gameObject.onUpdate();  # editor update

                    # scene
                    if self.settings.game_start:
                        gameObject.onStartScripts();
     
                    if self.settings.game_running:
                        gameObject.onUpdateScripts();

                if self.settings.game_start:
                    self.settings.game_start = False

                self.renderer.end_frame()

        self.renderer.shutdown()

if __name__ == '__main__':
    app = EmberEngine()
    app.run()