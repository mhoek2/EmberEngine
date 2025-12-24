
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
from gameObjects.skybox import Skybox
from modules.transform import Transform

from gameObjects.attachables.physic import Physic
from gameObjects.attachables.physicLink import PhysicLink
from gameObjects.attachables.light import Light
from gameObjects.attachables.model import Model

if TYPE_CHECKING:
    from main import EmberEngine
    from modules.models import Models
    from modules.material import Materials

import traceback

import uuid as uid

class World( Context ):
    def __init__( self, context ) -> None:
        """Project manager

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )

        self.gameObjects    : Dict[uid.UUID, GameObject] = {}
        self.transforms     : Dict[uid.UUID, Transform] = {}
        self.lights         : Dict[uid.UUID, Light] = {}
        self.models         : Dict[uid.UUID, "Model"] = {}
        self.material       : Dict[uid.UUID, int] = {}
        self.physics        : Dict[uid.UUID, Physic] = {}
        self.physic_links   : Dict[uid.UUID, PhysicLink] = {}

        self.trash          : List[uid.UUID] = []

    def destroyAllGameObjects( self ) -> None:
        self.gameObjects.clear()
        self.transforms.clear()
        self.lights.clear()
        self.models.clear()
        self.material.clear()
        self.physics.clear()
        self.physic_links.clear()

    def addGameObject( self, obj : GameObject ) -> int:
        self.gameObjects[obj.uuid] = obj
        return obj

    def addEmptyGameObject( self ):
        return self.addGameObject( Mesh( self.context,
            name        = "Empty GameObject",
            material    = self.context.materials.defaultMaterial,
            translate   = [ 0, 0, 0 ],
            scale       = [ 1, 1, 1 ],
            rotation    = [ 0.0, 0.0, 0.0 ]
        ) )

    def addDefaultCube( self ):
        gameObject : GameObject = self.addGameObject( Mesh( self.context,
            name        = "Default cube",
            material    = self.context.materials.defaultMaterial,
            translate   = [ 0, 1, 0 ],
            scale       = [ 1, 1, 1 ],
            rotation    = [ 0.0, 0.0, 0.0 ]
        ) )

        gameObject.addAttachable( Model, Model( 
            self.context, gameObject,
            handle      = self.context.models.loadOrFind( Path( self.context.models.default_cube_path ), gameObject.material ),
            path        = Path( self.context.models.default_cube_path )
        ) )

    def addDefaultCamera( self ):
        gameObject : GameObject = self.addGameObject( Camera( self.context,
            name        = "Camera",
            material    = self.context.materials.defaultMaterial,
            translate   = [ 0, 5, -10 ],
            scale       = [ 1, 1, 1 ],
            rotation    = [ -0.4, 0.0, 0.0 ],
            scripts     = [ Script( 
                    context = self.context,
                    path    = Path(f"{self.settings.assets}\\camera.py"),
                    active  = True
            ) ]
        ) )

        gameObject.addAttachable( Model, Model( 
            self.context, gameObject,
            handle      = self.context.models.loadOrFind( Path( f"{self.settings.engineAssets}models\\camera\\model.fbx" ), gameObject.material ),
            path        = Path( f"{self.settings.engineAssets}models\\camera\\model.fbx" )
        ) )

    def addDefaultLight( self ) -> None:
        gameObject : GameObject = self.addGameObject( Mesh( self.context,
            name        = "light",
            material    = self.context.materials.defaultMaterial,
            translate   = [ 0.0, 1.0, 0.0 ],
            scale       = [ 0.5, 0.5, 0.5 ],
            rotation    = [ 0.0, 0.0, 80.0 ]
        ) )

        gameObject.addAttachable( Light, Light( self.context, gameObject ) )
        gameObject.addAttachable( Model, Model( self.context, gameObject,
            handle      = self.context.models.loadOrFind( Path( self.context.models.default_sphere_path ), gameObject.material ),
            path        = Path( self.context.models.default_sphere_path )
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
                
            light : Light = obj.getAttachable(Light)
            if light is self.scene.getSun():
                self.scene.setSun( None )

            reparent_children = list(obj.children) # prevent mutation during iteration
            for child in reparent_children:
                child.setParent( obj.parent )

            # not implemented
            self.trash.append( obj.uuid )

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