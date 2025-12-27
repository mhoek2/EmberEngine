from pathlib import Path
from typing import List, Dict, Optional, Union

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
import traceback

from modules.settings import Settings

from modules.project import ProjectManager
from modules.scene import SceneManager
from modules.console import Console
from modules.userInterface import UserInterface
from modules.jsonHandling import JsonHandler
from modules.renderer import Renderer
from modules.camera import Camera as CameraHandler
from modules.cubemap import Cubemap
from modules.images import Images
from modules.models import Models
from modules.material import Materials
from modules.world import World

from gameObjects.gameObject import GameObject
from gameObjects.camera import Camera
from gameObjects.mesh import Mesh
from gameObjects.skybox import Skybox

from modules.gui.types import CustomEvent

import uuid as uid

from queue import Queue
from threading import Thread

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
 
        self.images     : Images            = Images( self )
        self.materials  : Materials         = Materials( self )
        self.models     : Models            = Models( self )
        self.cubemaps   : Cubemap           = Cubemap( self )
        self.skybox     : Skybox            = Skybox( self )

        self.world      : World             = World( self )

        self.renderer.create_shaders()
        self.renderer.create_buffers()
        self.renderer.create_editor_vaos()

        self.roughnessOverride = -1.0
        self.metallicOverride = -1.0

        self.scene.getScene( self.settings.default_scene )
        self.scene.getScenes()
        if not self.scene.loadScene( self.project.meta["default_scene"]):
            self.scene.loadDefaultScene()

        self.loadDefaultEnvironment()

        Thread(
            target = self.models.model_loader_thread, 
            daemon = True
        ).start()
 
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
        return [path for path in folder.rglob( f"*{self.settings.SCRIPT_EXTENSION}" )]

    def loadDefaultEnvironment( self ) -> None:
        """Load the default environment cubemap"""
        _scene = self.scene.getCurrentScene()

        if _scene["sky_type"] == Skybox.Type_.skybox:
            self.environment_map = self.cubemaps.loadOrFind( self.settings.default_environment )

        elif _scene["sky_type"] == Skybox.Type_.procedural:
            self.environment_map = self.skybox.create_procedural_cubemap( _scene )

    def prepare_gameObjects(self, 
        parent : GameObject = None,
        objects : Dict[uid.UUID, GameObject] = {}
    ):
        """
        Recursively prepare and update GameObjects in a parent–child nested hierarchy.

        This method traverses the GameObject tree starting from the given parent

            Depending on the application state, it handles:
            - Enabling objects when the game starts
            - Disabling objects when the game stops
            - Running per-frame update logic
            - Processing child GameObjects recursively

        :param parent: The parent GameObject whose children are processed.
                       Use None to start traversal from root-level objects.
        :type parent: GameObject or None
        :param objects: A mapping of GameObject UUIDs to GameObject instances
                        representing the current level of the hierarchy.
        :type objects: Dict[uuid.UUID, GameObject]
        """
        if not objects:
            return

        for obj in objects.values():
            if obj.parent != parent or obj.parent and parent == None:
                continue

            # (re)store states
            if not app.settings.is_exported:
                if self.renderer.game_start:
                    obj.onEnable( _on_start=True )

                if self.renderer.game_stop:
                    obj.onDisable( _on_stop=True )

            # start exported application
            else:
                if self.renderer.game_start:
                    obj.onEnable( _on_start=True )

            obj.onUpdate();  # engine update

            # render children if any
            if obj.children:
                self.prepare_gameObjects( obj, obj.children )

    def _upload_material_ubo( self ) -> None:
        """Build a UBO of materials and upload to GPU, rebuild when material list is marked dirty"""
        if self.renderer.ubo_materials._dirty:
            materials : list[Renderer.MaterialUBO.Material] = []

            for i, mat in enumerate(self.materials.materials):
                materials.append( Renderer.MaterialUBO.Material(
                    # bindless
                    albedo          = self.images.texture_to_bindless[ mat.get( "albedo",     self.images.defaultImage)     ],       
                    normal          = self.images.texture_to_bindless[ mat.get( "normal",     self.images.defaultNormal)    ],       
                    phyiscal        = self.images.texture_to_bindless[ mat.get( "phyiscal",   self.images.defaultRMO)       ],       
                    emissive        = self.images.texture_to_bindless[ mat.get( "emissive",   self.images.blackImage)       ],       
                    opacity         = self.images.texture_to_bindless[ mat.get( "opacity",    self.images.whiteImage)       ],
                        
                    # both bindless and non-bindless paths
                    hasNormalMap    = mat.get( "hasNormalMap", 0 ),
                )
            )

            self.renderer.ubo_materials.update( materials )

        self.renderer.ubo_materials.bind()

    def _upload_lights_ubo( self, sun : GameObject ) -> None:
        """Build a UBO of lights, rebuilds every frame (currently)
        
        :param sun: The sun GameObject, light is excluded from UBO
        :type sun: GameObject
        """
        lights : list[Renderer.LightUBO.Light] = []

        for uuid in self.world.lights.keys():
            obj : GameObject = self.world.gameObjects[uuid]

            if not obj.hierachyActive() or obj is sun:
                continue

            if not self.renderer.game_runtime and not obj.hierachyVisible():
                continue

            lights.append( Renderer.LightUBO.Light(
                origin      = obj.transform.position,
                rotation    = obj.transform.rotation,


                color       = obj.light.light_color,
                radius      = obj.light.radius,
                intensity   = obj.light.intensity,
                t           = obj.light.light_type
            ) )

        self.renderer.ubo_lights.update( lights )
        self.renderer.ubo_lights.bind()

    def run( self ) -> None: 
        """The main loop of the appliction, remains active as long as 'self.renderer.running'
        is True.
        This handles key, mouse, start, update events and drawing GUI and gameObjects"""
        while self.renderer.running:
            self.renderer.event_handler()

            if not self.renderer.paused:
                self.renderer.begin_frame()

                _scene = self.scene.getCurrentScene()

                #
                # lazy model loading, flush loaded models set ready from thread
                #
                self.models.model_loader_thread_flush()

                #
                # skybox
                #
                self.skybox.draw( _scene )

                #
                # general
                #
                self.renderer.use_shader( self.renderer.general )
                # bind the projection and view  matrix beginning (until shader switch)
                glUniformMatrix4fv( self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection )
                glUniformMatrix4fv( self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view )

                # static textures
                self.cubemaps.bind( self.environment_map, GL_TEXTURE5, "sEnvironment", 5 )
                self.images.bind( self.cubemaps.brdf_lut, GL_TEXTURE6, "sBRDF", 6 )

                # editor uniforms
                glUniform1i( self.renderer.shader.uniforms['in_renderMode'], self.renderer.renderMode )
                glUniform1f( self.renderer.shader.uniforms['in_roughnessOverride'], self.roughnessOverride  )
                glUniform1f( self.renderer.shader.uniforms['in_metallicOverride'], self.metallicOverride )

                #
                # setup scene
                #
                # camera origin
                glUniform4f( self.renderer.shader.uniforms['u_ViewOrigin'], self.camera.camera_pos[0], self.camera.camera_pos[1], self.camera.camera_pos[2], 0.0 )

                # sun direction, position and color
                _sun : GameObject = self.scene.getSun()
                _sun_active = _sun and _sun.hierachyActive()

                if not self.renderer.game_runtime:
                    _sun_active = _sun_active and _sun.hierachyVisible()

                light_dir   = _sun.transform.local_position if _sun_active else self.settings.default_light_color
                light_color = _sun.light.light_color        if _sun_active else self.settings.default_ambient_color

                glUniform4f( self.renderer.shader.uniforms['in_lightdir'], light_dir[0], light_dir[1], light_dir[2], 0.0 )
                glUniform4f( self.renderer.shader.uniforms['in_lightcolor'], light_color[0], light_color[1], light_color[2], 1.0 )
                glUniform4f( self.renderer.shader.uniforms['in_ambientcolor'], _scene["ambient_color"][0], _scene["ambient_color"][1], _scene["ambient_color"][2], 1.0 )

                # lights
                self._upload_lights_ubo( _sun )

                # materials
                self._upload_material_ubo()

                if self.renderer.game_start:
                    self.console.clear()

                # triggers update systems in the registered gameObjects
                # handles onEnable, onDisable, onStart, onUpdate and _dirty flags
                self.prepare_gameObjects( None, self.world.gameObjects )

                # collect active model meshes (build the draw list, unsorted/batched)
                for uuid in self.world.models.keys():
                    obj : GameObject = self.world.gameObjects[uuid]

                    if isinstance(obj, Camera) and self.renderer.game_runtime:
                        continue

                    obj.onRender()

                # dispatch world draw calls
                self.renderer.dispatch_drawcalls()

                # dispatch editor visuals
                # eg: grid, axis, colliders (instant drawing, not indirect)
                if not app.settings.is_exported and not app.renderer.game_runtime:
                    self.renderer.draw_grid()
                    self.renderer.draw_axis( 2.0 )

                if self.settings.drawColliders:
                    self.renderer.use_shader( self.renderer.color )

                    # bind projection matrix
                    glUniformMatrix4fv(self.renderer.shader.uniforms['uPMatrix'], 1, GL_FALSE, self.renderer.projection)
        
                    # viewmatrix
                    glUniformMatrix4fv(self.renderer.shader.uniforms['uVMatrix'], 1, GL_FALSE, self.renderer.view)

                    for uuid in self.world.physics.keys():
                        self.world.gameObjects[uuid].onRenderColliders()

                    for uuid in self.world.physic_links.keys():
                        self.world.gameObjects[uuid].onRenderColliders()

                #
                # cleanup _removed objects
                #
                #for obj in filter(lambda x: x._removed == True, self.world.gameObjects):
                #    if obj.children:
                #        print("Cannot remove: obj has children")
                #        continue
                #
                #    self.world.gameObjects.remove( obj )

                self.renderer.end_frame()

        self.renderer.shutdown()

if __name__ == '__main__':
    app = EmberEngine()

    # debug
    if getattr(sys, "frozen", False):
        print(sys._MEIPASS)

    # start runtime for exported apps
    if app.settings.is_exported:
        app.renderer.game_state = app.renderer.GameState_.running 

    app.run()