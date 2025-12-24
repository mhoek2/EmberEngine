
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, TypedDict, Optional, Union
import json
import re
import sys

from modules.context import Context
from modules.console import Console
from modules.settings import Settings
from modules.script import Script

from gameObjects.gameObject import GameObject
from gameObjects.camera import Camera
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.skybox import Skybox
from modules.transform import Transform

if TYPE_CHECKING:
    from main import EmberEngine
    from modules.models import Models, Model
    from modules.material import Materials
    from gameObjects.attachables.physic import Physic
    from gameObjects.attachables.physicLink import PhysicLink

import traceback

import uuid as uid

class World( Context ):
    def __init__( self, context ) -> None:
        """Project manager

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )
        self.materials  : "Materials" = context.materials
        self.models     : "Models" = context.models

        self.gameObjects    : Dict[uid.UUID, GameObject] = {}
        self.transforms     : Dict[uid.UUID, Transform] = {}
        self.models         : Dict[uid.UUID, "Model"] = {}
        self.material       : Dict[uid.UUID, int] = {}
        self.physics        : Dict[uid.UUID, Physic] = {}
        self.physic_links   : Dict[uid.UUID, PhysicLink] = {}
        self.lights         : Dict[uid.UUID, Light] = {}

    def destroyAllGameObjects( self ) -> None:
        self.gameObjects.clear()

    def addGameObject( self, obj : GameObject ) -> int:
        self.gameObjects[obj.uuid] = obj
        return obj

    def addEmptyGameObject( self ):
        return self.addGameObject( Mesh( self.context,
            name        = "Empty GameObject",
            material    = self.materials.defaultMaterial,
            translate   = [ 0, 0, 0 ],
            scale       = [ 1, 1, 1 ],
            rotation    = [ 0.0, 0.0, 0.0 ]
        ) )

    def addDefaultCube( self ):
        return self.addGameObject( Mesh( self.context,
            name        = "Default cube",
            model_file  = self.models.default_cube_path,
            material    = self.materials.defaultMaterial,
            translate   = [ 0, 1, 0 ],
            scale       = [ 1, 1, 1 ],
            rotation    = [ 0.0, 0.0, 0.0 ]
        ) )

    def addDefaultCamera( self ):
        return self.addGameObject( Camera( self.context,
                        name        = "Camera",
                        model_file  = f"{self.settings.engineAssets}models\\camera\\model.fbx",
                        material    = self.materials.defaultMaterial,
                        translate   = [ 0, 5, -10 ],
                        scale       = [ 1, 1, 1 ],
                        rotation    = [ -0.4, 0.0, 0.0 ],
                        scripts     = [ Script( 
                                context = self.context,
                                path    = Path(f"{self.settings.assets}\\camera.py"),
                                active  = True
                        ) ]
                    ) )

    def addDefaultLight( self ) -> None:
        return self.addGameObject( Light( self.context,
                        name        = "light",
                        model_file  = self.models.default_sphere_path,
                        translate   = [1, -1, 1],
                        scale       = [ 0.5, 0.5, 0.5 ],
                        rotation    = [ 0.0, 0.0, 80.0 ]
                    ) )

    def removeGameObject( self, obj : GameObject ):
        try:
            # we cant directly remove and rebuild the gameObject array.
            # so mark it removed, and do not store it on save.
            #self.gameObjects.remove( object )
            obj._removed = True
            obj._visible = False
            obj._active = False
            obj._mark_dirty()

            if isinstance( obj, Camera ) and obj is self.scene.getCamera():
                self.scene.setCamera( None )

            if isinstance( obj, Light ) and obj is self.scene.getSun():
                self.scene.setSun( None )

            reparent_children = list(obj.children) # prevent mutation during iteration
            for child in reparent_children:
                child.setParent( obj.parent )

        except Exception as e:
            print( e )
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.error( e, traceback.format_tb(exc_tb) )

    def findGameObject( self, identifier : Optional[Union[uid.UUID, int, str]] = None ) -> GameObject:
        """Try to find a gameObject by its uuid
        
        :param identifier: This is a identifier of a gameObject that is looked for, datatype int : _uuid_gui, uid.UUID : uuid or str : name
        :type identifier: Optional[Union[uid.UUID, int, str]
        :return: A GameObject object or None
        :rtype: GameObject | None
        """
        if identifier is None:
            return None

        if isinstance(identifier, uid.UUID) and identifier in self.gameObjects:
            return self.gameObjects[identifier]

        for obj in self.gameObjects.values():
            if isinstance(identifier, int) and obj._uuid_gui == identifier:
                return obj

            if isinstance(identifier, str) and obj.name == identifier:
                return obj

        return None