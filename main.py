from pathlib import Path
from typing import List, Optional, Union

#import site
#print(site.getsitepackages())

import pygame
from pygame.locals import *
from pyrr import matrix44, Vector3

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np
import re
import sys
import uuid as uid

from modules.settings import Settings

from modules.project import ProjectManager
from modules.scene import SceneManager
from modules.console import Console
from modules.userInterface import UserInterface, CustomEvent
from modules.jsonHandling import JsonHandler
from modules.renderer import Renderer
from modules.camera import Camera as CameraHandler
from modules.cubemap import Cubemap
from modules.images import Images
from modules.models import Models
from modules.material import Materials

from gameObjects.gameObject import GameObject
from gameObjects.camera import Camera
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.skybox import Skybox

class EmberEngine:
    def __init__( self ) -> None:
        """The main context of 'EmberEngine', 
        initializes required modules like:
        renderer, console, image loaders, materials, scene manager, pygame events"""
        self.settings   : Settings = Settings()
        
        self.asset_scripts : List[Path] = []
        self.findScripts()
        
        self.events     = pygame.event
        self.key        = pygame.key
        self.mouse      = pygame.mouse
        self.cevent     : CustomEvent = CustomEvent()

        self.console    : Console           = Console(self)
        self.project    : ProjectManager    = ProjectManager(self)
        self.scene      : SceneManager      = SceneManager( self )
        self.camera     : CameraHandler     = CameraHandler( self )
        self.renderer   : Renderer          = Renderer( self )
        self.gui        : UserInterface     = UserInterface( self )
 
        self.gameObjects : List[GameObject] = []

        self.images     : Images            = Images( self )
        self.materials  : Materials         = Materials( self )
        self.models     : Models            = Models( self )
        self.cubemaps   : Cubemap           = Cubemap( self )
        self.skybox     : Skybox            = Skybox( self )

        self.sun = -1
        self.roughnessOverride = -1.0
        self.metallicOverride = -1.0

        self.defaultMaterial = self.materials.buildMaterial()
        self.scene.getScene( self.settings.default_scene )

        self.scene.getScenes()
        if not self.scene.loadScene( self.project.meta["default_scene"]):
            self.scene.loadDefaultScene()

        self.loadDefaultEnvironment()
 
    def sanitize_filename( self, string : str ):
        """Sanitize a string for use of a filename, 
        by allowing underscore, hypen, period, numbers and letters (both cases)
        
        :param string: The input string to be sanitized
        :type string: str
        :return: A sanitized string that can be used as filename.
        :rtype: str:
        """
        string = re.sub(r'[^a-zA-Z0-9_\-.]', '', string)
        string = string.replace(' ', '_')
        string = string.lower()

        return string

    def findScripts( self ):
        """scan asset folder for .py files.
        perhaps there should be a separate thread for this
        that either updates periodicly, or tracks changes in assets folder
        - currently this is called every time 'Add Script' popup is opened' """
        _assets = Path( self.settings.assets ).resolve()

        self.asset_scripts = self.findDynamicScripts( _assets )

    def findDynamicScripts( self, folder : Path ) -> List[Path]:
        """Find .py files recursivly in a assets folder, used as dynamic scripts.

        :param folder: This is root folder to scan
        :type folder: Path
        :return: List of Path's containing each .py script
        :rtype: List[Path]
        """
        return [path for path in folder.rglob("*.py")]

    def loadDefaultEnvironment( self ) -> None:
        """Load the default environment cubemap"""
        self.environment_map = self.cubemaps.loadOrFind(self.settings.default_environment)

    ##
    ## Need to move this to dedicated class
    ##
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
            mass        = -1.0,
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
            obj._visible = False

            if isinstance( obj, Camera ) and obj is self.scene.getCamera():
                self.scene.setCamera( -1 )

            reparent_children = list(obj.children) # prevent mutation during iteration
            for child in reparent_children:
                child.setParent( obj.parent )

        except:
            print("gameobject doesnt exist..")


    def findGameObject( self, identifier : Optional[Union[uid.UUID, int, str]] = None ) -> GameObject:
        """Try to find a gameObject by its uuid
        
        :param identifier: This is a identifier of a gameObject that is looked for, datatype int : _uuid_gui, uid.UUID : uuid or str : name
        :type identifier: Optional[Union[uid.UUID, int, str]
        :return: A GameObject object or None
        :rtype: GameObject | None
        """
        if identifier is None:
            return None

        for obj in self.gameObjects:
            if isinstance(identifier, int) and obj._uuid_gui == identifier:
                return obj

            if isinstance(identifier, str) and obj.name == identifier:
                return obj

            if isinstance(identifier, uid.UUID) and obj.uuid == identifier:
                return obj

        return None
    ##
    ## end
    ##

    def draw_grid( self ):
        """Draw the horizontal grid to the framebuffer"""
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

    def draw_axis( self, length : float = 1.0, width : float = 3.0, centered : bool = False ):
        """Draw axis lines. width and length can be adjust, also if axis is centered or half-axis"""
        glLineWidth(width)

        self.renderer.use_shader(self.renderer.color)

        # bind projection matrix
        glUniformMatrix4fv(self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection)
        
        # viewmatrix
        glUniformMatrix4fv(self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view)

        if centered:
            start = -length
            end   = +length
        else:
            start = 0.0
            end   = length

        # X axis : red
        glUniform4f(self.renderer.shader.uniforms['uColor'], 1.0, 0.0, 0.0, 1.0)
        glBegin(GL_LINES)
        glVertex3f(start, 0.0,   0.0)
        glVertex3f(end,   0.0,   0.0)
        glEnd()

        # Y axis : green
        glUniform4f(self.renderer.shader.uniforms['uColor'], 0.0, 1.0, 0.0, 1.0)
        glBegin(GL_LINES)
        glVertex3f(0.0, start,   0.0)
        glVertex3f(0.0, end,     0.0)
        glEnd()

        # Z axis : blue
        glUniform4f(self.renderer.shader.uniforms['uColor'], 0.0, 0.0, 1.0, 1.0)
        glBegin(GL_LINES)
        glVertex3f(0.0,   0.0, start)
        glVertex3f(0.0,   0.0, end)
        glEnd()

        glLineWidth(1.0)

    def renderGameObjectsRecursive(self, 
        parent : GameObject = None,
        objects : List[GameObject] = []
    ):
        if not objects:
            return

        for obj in objects:
            if obj.parent != parent or obj.parent and parent == None:
                continue

            # (re)store states
            if not app.settings.is_exported:
                if self.settings.game_start:
                    obj.onEnable( _on_start=True )

                if self.settings.game_stop:
                    obj.onDisable( _on_stop=True )

            obj.onUpdate();  # engine update

            # render children if any
            if obj.children:
                self.renderGameObjectsRecursive( 
                    obj, 
                    obj.children
                )

    def run( self ) -> None:
        """The main loop of the appliction, remains active as long as 'self.renderer.running'
        is True.
        This handles key, mouse, start, update events and drawing GUI andgameObject"""
        while self.renderer.running:
            self.renderer.event_handler()

            if not self.renderer.paused:
                self.renderer.begin_frame()

                #
                # skybox
                #
                self.skybox.draw()

                #
                # editor viewport
                #
                if not app.settings.is_exported:
                    self.draw_grid()
                    self.draw_axis(100.0, centered=True)

                #
                # general
                #
                self.renderer.use_shader( self.renderer.general )

                # environment
                self.cubemaps.bind( self.environment_map, GL_TEXTURE5, "sEnvironment", 5 )

                # brdf lut
                self.images.bind( self.cubemaps.brdf_lut, GL_TEXTURE6, "sBRDF", 6 )

                glUniform1i( self.renderer.shader.uniforms['in_renderMode'], self.renderer.renderMode )

                # projection matrix can be bound at start
                # bind projection matrix
                glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection )
                
                # viewmatrix
                glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view )
                
                # camera
                glUniform4f( self.renderer.shader.uniforms['u_ViewOrigin'], self.camera.camera_pos[0], self.camera.camera_pos[1], self.camera.camera_pos[2], 0.0 )

                #
                # setup scene
                #
                _scene = self.scene.getCurrentScene()

                # sun direction/position and color
                light_dir = self.gameObjects[self.sun].transform.local_position if self.sun != -1 else (0.0, 0.0, 1.0)
                glUniform4f( self.renderer.shader.uniforms['in_lightdir'], light_dir[0], light_dir[1], light_dir[2], 0.0 )
                glUniform4f( self.renderer.shader.uniforms['in_lightcolor'], _scene["light_color"][0], _scene["light_color"][1], _scene["light_color"][2], 1.0 )
                glUniform4f( self.renderer.shader.uniforms['in_ambientcolor'], _scene["ambient_color"][0], _scene["ambient_color"][1], _scene["ambient_color"][2], 1.0 )

                glUniform1f( self.renderer.shader.uniforms['in_roughnessOverride'], self.roughnessOverride  )
                glUniform1f( self.renderer.shader.uniforms['in_metallicOverride'], self.metallicOverride )
                
                if self.settings.game_start:
                    self.console.clear()

                # trigger update function in registered gameObjects
                self.renderGameObjectsRecursive( 
                    None, 
                    self.gameObjects
                )

                if self.settings.game_start:
                    self.settings.game_start = False

                if self.settings.game_stop:
                    self.settings.game_stop = False

                self.renderer.end_frame()

        self.renderer.shutdown()

if __name__ == '__main__':
    app = EmberEngine()

    # debug
    if getattr(sys, "frozen", False):
        print(sys._MEIPASS)

    # start runtime for exported apps
    if app.settings.is_exported:
        app.settings.game_start = True
        app.settings.game_running = True 

    app.run()
