
import os

import site

from gameObjects.skybox import Skybox
print(site.getsitepackages())

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
        self.renderer = Renderer()
        self.renderer.setup_projection()

        self.gameObjects : GameObject = []

        self.images = Images( self )
        self.materials = Material( self )
        self.models = Models( self )
        self.cubemaps = Cubemap( self )
        self.skybox = Skybox( self )
        
        # default opbject
        #self.addGameObject( Mesh( self,
        #                            translate=[0, 1, 0],
        #                            scale=[ 1, 1, 1 ],
        #                            rotation=[ 0.0, 0.0, 80.0 ]
        #                ) )


        #self.addGameObject( Mesh( self,
        #                            model_file="cube/cube.obj",
        #                            texture_file="wall_inset.jpg",
        #                            normals_file="wall_inset_nh.tga",
        #                            phyiscal_file="wall_inset_rmo.tga",
        #                            translate=[0, 0, 0],
        #                            scale=[ 5, 0.01, 5 ],
        #                ) )

        #self.addGameObject( Mesh( self,
        #                            model_file="cube/cube.obj",
        #                            texture_file="pipesnwall.jpg",
        #                            normals_file="pipesnwall_n.tga",
        #                            phyiscal_file="pipesnwall_rmo.png",
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

        
        self.addGameObject( Mesh( self,
                                    model_file="gun/model.fbx",
                                    translate=[0, 0, 0],
                                    scale=[ 0.05, 0.05, 0.05 ],
                                    rotation=[ 90.0, 0.0, 0.0 ]
                        ) )

        self.setupSun()
        self.loadEnvironment()

    def loadEnvironment( self ) -> None:
        self.environment_map = self.cubemaps.loadOrFind( "bespin_day" )

    def setupSun( self ) -> None:
        self.sun = self.addGameObject( Sun( self,
                        model_file="Sphere/sphere.obj",
                        texture_file="sun.jpg",
                        normals_file="sun_n.tga",
                        phyiscal_file="sun_rmo.tga",
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
                view = self.renderer.cam.get_view_matrix()


                # skybox
                #glDepthMask(GL_LEQUAL);

                self.renderer.use_shader( self.renderer.skybox )

                # bind projection matrix
                glUniformMatrix4fv( self.renderer.uPMatrix2, 1, GL_FALSE, self.renderer.projection )
                # viewmatrix
                glUniformMatrix4fv( self.renderer.uVMatrix2, 1, GL_FALSE, view )

                self.cubemaps.bind( self.environment_map, GL_TEXTURE0, "sEnvironment", 0 )
                self.skybox.draw()
                #glDepthMask(GL_LESS);

                
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

                self.renderer.end_frame()
        pygame.quit()

if __name__ == '__main__':
    app = EmberEngine()
    app.run()