import os
from pathlib import Path

#import site
#print(site.getsitepackages())

from gameObjects.skybox import Skybox

import pygame
from pygame.locals import *
from pyrr import matrix44, Vector3

from OpenGL.GL import *
from OpenGL.GLU import *

import math

from modules.jsonHandling import JsonHandler
from modules.renderer import Renderer
from modules.cubemap import Cubemap
from modules.images import Images
from modules.models import Models
from modules.material import Material

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.sun import Sun


class EmberEngine:
    def __init__( self ) -> None:
        self.rootdir = Path.cwd()

        self.engineAssets   = f"{self.rootdir}\\engineAssets\\"
        self.assets         = f"{self.rootdir}\\assets\\"

        self.renderer   = Renderer( self )

        self.gameObjects : GameObject = []

        self.images     = Images( self )
        self.materials  = Material( self )
        self.models     = Models( self )
        self.cubemaps   = Cubemap( self )
        self.skybox     = Skybox( self )
        
        # default material
        self.defaultMaterial = self.materials.buildMaterial( 
            albedo  = f"{self.engineAssets}textures\\default.jpg",
            normal  = f"{self.engineAssets}textures\\default_normal.png",
            rmo     = f"{self.engineAssets}textures\\default_rmo.png"
        )

        #default object
        self.addGameObject( Mesh( self,
                                    material    = self.defaultMaterial,
                                    translate   = [ 0, 1, 0 ],
                                    scale       = [ 1, 1, 1 ],
                                    rotation    = [ 0.0, 0.0, 80.0 ]
                        ) )

        #self.addGameObject( Mesh( self,
        #                            model_file  = f"{self.assets}models\\Tree\\Tree.obj",
        #                            translate   = [0, 0, 0],
        #                            scale       = [ 1, 1, 1 ],
        #                ) )

        #self.addGameObject( Mesh( self,
        #                            model_file="cube/cube.obj",
        #                            translate=[0, 0, 0],
        #                            scale=[ 1, 1, 1 ],
        #                            rotation=[ 0.0, 0.0, 45.0 ]
        #                ) )

        #self.addGameObject( Mesh( self,
        #                            model_file="station/model.obj",
        #                            translate=[0, 0, 0],
        #                            scale=[ 0.05, 0.05, 0.05 ],
        #                            rotation=[ 0.0, 0.0, 0.0 ]
        #                ) )

        
        #self.addGameObject( Mesh( self,
        #                            model_file=f"{self.assets}models\\gun\\model.fbx",
        #                            translate=[0, 0, 0],
        #                            scale=[ 0.05, 0.05, 0.05 ],
        #                            rotation=[ 90.0, 0.0, 0.0 ]
        #                ) )

        #self.addGameObject( Mesh( self,
        #                            model_file="japan/model.fbx",
        #                            translate=[0, 0, 0],
        #                            scale=[ 1, 1, 1 ],
        #                            rotation=[ 90.0, 60.0, 0.0 ]
        #                ) )

        # fix nested models matix
        #self.addGameObject( Mesh( self,
        #                            model_file="rusty-truck/model.fbx",
        #                            translate=[0, 0, 0],
        #                            scale=[ 1, 1, 1 ],
        #                            rotation=[ 0.0, 0.0, 0.0 ]
        #                ) )


        #self.addGameObject( Mesh( self,
        #                            model_file  = f"{self.assets}models\\jerrycan\\model.fbx",
        #                            translate   = [5, 0, 0],
        #                            scale       = [ 0.05, 0.05, 0.05 ],
        #                            rotation    = [ 0.0, 0.0, 0.0 ]
        #                ) )

        #self.addGameObject( Mesh( self,
        #                            model_file="cabinet/model.fbx",
        #                            translate=[-5, 0, 0],
        #                            scale=[ 1, 1, 1 ],
        #                            rotation=[ 0.0, 0.0, 0.0 ]
        #                ) )

        self.setupSun()
        self.loadDefaultEnvironment()

    def loadDefaultEnvironment( self ) -> None:
        self.environment_map = self.cubemaps.loadDefaultCubemap()

    def setupSun( self ) -> None:
        self.sun = self.addGameObject( Sun( self,
                        model_file=f"{self.engineAssets}models\\sphere\\model.obj",
                        translate=[1, -1, 1],
                        scale=[ 1, 1, 1 ],
                        rotation=[ 0.0, 0.0, 80.0 ]
                    ) )

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

                # bind main FBO
                self.renderer.bind_fbo( self.renderer.main_fbo )

                view = self.renderer.cam.get_view_matrix()

                # skybox
                self.renderer.use_shader( self.renderer.skybox )

                # bind projection matrix
                glUniformMatrix4fv( self.renderer.uPMatrix2, 1, GL_FALSE, self.renderer.projection )
                # viewmatrix
                glUniformMatrix4fv( self.renderer.uVMatrix2, 1, GL_FALSE, view )

                self.cubemaps.bind( self.environment_map, GL_TEXTURE0, "sEnvironment", 0 )
                self.skybox.draw()

                
                self.renderer.use_shader( self.renderer.general )

                # projection matrix can be bound at start
                # bind projection matrix
                glUniformMatrix4fv( self.renderer.uPMatrix, 1, GL_FALSE, self.renderer.projection )
                
                # viewmatrix
                glUniformMatrix4fv( self.renderer.uVMatrix, 1, GL_FALSE, view )
                
                # camera
                camera_pos = self.renderer.cam.camera_pos
                glUniform4f( self.renderer.u_ViewOrigin, camera_pos[0], camera_pos[1], camera_pos[2], 0.0 )

                # sun direction/position
                light_dir = self.gameObjects[self.sun].translate
                glUniform4f( self.renderer.in_lightdir, light_dir[0], light_dir[1], light_dir[2], 0.0 )

                # rendermode
                glUniform1i( self.renderer.in_renderMode, self.renderer.renderMode )

                # trigger update function in registered gameObjects
                for gameObject in self.gameObjects:
                    gameObject.onUpdate();

                glUseProgram( 0 )

                # stop rendering to main FBO
                self.renderer.unbind_fbo()

                self.renderer.end_frame()
        pygame.quit()

if __name__ == '__main__':
    app = EmberEngine()
    app.run()