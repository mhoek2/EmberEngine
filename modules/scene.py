#from __future__ import annotations

import sys
from pathlib import Path
#import importlib
from typing import TYPE_CHECKING, List, Dict, TypedDict
import json
import uuid as uid

from modules.console import Console
from modules.settings import Settings
from modules.transform import Transform
from modules.script import Script
from gameObjects.scriptBehaivior import ScriptBehaivior

from gameObjects.attachables.physic import Physic
from gameObjects.attachables.physicLink import PhysicLink
from gameObjects.attachables.light import Light

if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject
    from gameObjects.camera import Camera
    from gameObjects.skybox import Skybox

import traceback

class SceneManager:
    class Scene(TypedDict):
        """Typedef for a scene file"""
        uid             : str
        name            : str
        gameObjects     : List["_GameObject"]
        camera          : "Camera"
        sun             : "Light"
        sky_type        : "Skybox.Type_"
        light_color     : List[float]
        ambient_color   : List[float]

        procedural_sky_color        : List[float]
        procedural_horizon_color    : List[float]
        procedural_ground_color     : List[float]
        procedural_sunset_color     : List[float]
        procedural_night_color      : List[float]
        procedural_night_brightness : float

    class _GameObject(TypedDict):
        """Typedef for a gameObjects in a scene file"""
        instance    : str
        visible     : bool
        name        : str
        model_file  : str
        material    : int
        translate   : List[float]
        rotation    : List[float]
        scale       : List[float]
        mass        : float
        scripts     : List[Script]
        transform   : Transform 
        instance_data : Dict # additional instance data
        #children    : Dict
        children    : List["_GameObject"] = []

    def __init__( self, context ) -> None:
        """scene manager

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        self.context    : 'EmberEngine' = context
        self.settings   : Settings = context.settings
        self.console    : Console = context.console

        self.scenes     : List[SceneManager.Scene] = []

        self.current_scene : int = -1

    def getCurrentScene( self ) -> Scene:
        """Get the current active scene

        :return: The current scene object, False if this fails
        :rtype: Scene
        """
        try:
            return self.scenes[self.current_scene]
        except:
            return False

    def getCurrentSceneUID( self ) -> str:
        """Get the current scene UID.
        
        :return: The UID of the current scene, usualy this represents the filename of a .scene
        :rtype: str
        """
        try:
            return self.scenes[self.current_scene]["uid"]
        except:
            return self.settings.default_scene.stem

    def getSceneById( self, scene_id : int ) -> Scene:
        """Get a scene by the index it is in the scenes List
        
        :param scene_id: The index of the scene
        :type scene_id: int
        :return: The scene at that location, False if invalid
        :rtype: Scene or bool
        """
        try:
            return self.scenes[self.current_scene]
        except:
            return False

    def getSceneByUID( self, scene_uid : str ) -> Scene:
        """Get a scene by the UID, which is the filename withouth .scene
        
        :param scene_uid: The name of the .scene file
        :type scene_id: str
        :return: The scene at that location, False if invalid
        :rtype: Scene or bool
        """
        try:
            for scene in self.scenes:
                if scene["uid"] == scene_uid:
                    return scene

            return False
        except:
            return False

    def setCamera( self, uuid : uid.UUID, scene_id = -1):
        """Set the current runtime camera based on gameObject uid

            During game runtime, update the projection matrix a well.

        :param uid: The uid of a Camera gameObject
        :type uid: int
        :param scene_id: The index in scens List of the scene the camera is set on, current scene when empty
        :type scene_id: int, optional
        """
        from gameObjects.camera import Camera

        _scene = scene_id if scene_id >= 0 else self.current_scene
        _editor_camera = None

        obj = self.context.world.findGameObject( uuid )

        if obj is None:
            self.scenes[_scene]["sun"] = None
            _editor_camera = None

        # set default scene/runtime camera
        elif obj and isinstance(obj, Camera):
            obj.is_default_camera = True
            self.scenes[_scene]["camera"] = obj

            # switch scene/camera during runtime
            if self.context.renderer.game_runtime:
                _editor_camera = obj

        # invoke a camera and projection update using the setter
        self.context.camera.camera = _editor_camera

    def getCamera( self ):
        """Get the current default/start camera

        :return: The current scene default/start camera, False if this fails
        :rtype: Camera or bool
        """
        from gameObjects.camera import Camera

        try:
            _scene_camera = self.scenes[self.current_scene]["camera"]

            if not isinstance( _scene_camera, Camera ):
                raise IndexError("invalid camera")

            return _scene_camera

        except Exception as e:
            #print( e )
            #exc_type, exc_value, exc_tb = sys.exc_info()
            #self.console.error( e, traceback.format_tb(exc_tb) )
            return False

    def getSun( self ):
        """Get the current sun

        :return: The current scene sun, False if this fails
        :rtype: Camera or bool
        """
        try:
            obj : GameObject = self.scenes[self.current_scene]["sun"]

            if not obj or not obj.light:
                raise IndexError("invalid sun")

            return obj

        except Exception as e:
            #print( e )
            #exc_type, exc_value, exc_tb = sys.exc_info()
            #self.console.error( e, traceback.format_tb(exc_tb) )
            return False

    def isSun( self, uuid : uid.UUID ) -> bool:
        """If the provided object the current sun
        
        :return: True if the it is the sun, False if not
        :rtype: Camera or bool
        """
        _sun = self.getSun()

        if _sun and _sun.uuid == uuid:
            return True

        return False

    def setSun( self, uuid : uid.UUID, scene_id = -1):
        _scene = scene_id if scene_id >= 0 else self.current_scene

        obj = self.context.world.findGameObject( uuid )

        # here for now
        self.context.skybox.procedural_cubemap_update = True

        if not obj or not obj.light:
            self.scenes[_scene]["sun"] = None
            return

        # set scene sun
        obj.is_sun = True
        self.scenes[_scene]["sun"] = obj

    def newScene( self, name : str ):
        """Creates a new scene based on the engines default empty scene
        
        :param name: The name of the scene, which is also sanitized and use as filename for the .scene file.
        :type name: str
        """
        _scene_uid = self.context.sanitize_filename(name)
        
        #_scene = self.getDefaultScene()
        #if not _scene:
        #    self.console.error( e, f"Couldn't load default scene'" )
        #
        #_current_name = _scene["name"] # temporary store current scene's name
        
        # save current scene
        self.saveScene()

        try:
            with open(self.settings.default_scene, 'r') as buffer:
                scene : SceneManager.Scene = json.load(buffer)
                scene["name"] = name

            _scene_filename = f"{self.settings.assets}\\{_scene_uid}{self.settings.SCENE_EXTENSION}"
            with open(_scene_filename, 'w') as buffer:
                json.dump(scene, buffer, indent=4)

            # reload scenes in assets, will load it into the List
            self.getScenes()

            # load the new scene
            self.clearEditorScene() # clear editor scene first
            self.loadScene( _scene_uid )

        except Exception as e:
            print( e )
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.error( e, traceback.format_tb(exc_tb) )
     
    def saveSceneAs( self, name : str ):
        """Duplicate the current scene under a diffrent filename
        
        :param name: The name of the scene, which is also sanitized and use as filename for the .scene file.
        :type name: str
        """
        _scene_uid = self.context.sanitize_filename(name)
        _scene = self.getCurrentScene()

        _current_name = _scene["name"] # temporary store current scene's name

        _scene["name"] = name
        self.saveScene(_scene_uid)

        _scene["name"] = _current_name # restore current scenes's name

    def serialize_export( self, exported : ScriptBehaivior.Exported ):
        if isinstance(exported.default, uid.UUID):
            return {
                "uuid"  : exported.default.hex,
                #"type"  : exported.type.__name__    # deprecated use case
            }

        return exported.default

    #def resolve_type( self, type_path: str ):
    #    module_name, class_name = type_path.rsplit(".", 1)
    #    module = importlib.import_module(module_name)
    #
    #    return getattr(module, class_name)

    def deserialize_export( self, name, data ):
        #ENGINE_TYPES = {
        #    "Transform": "modules.transform.Transform",
        #    "GameObject": "gameObjects.gameObject.GameObject",
        #}

        # engine type
        if isinstance(data, dict) and "uuid" in data:
            raw_value = uid.UUID(hex=data["uuid"])

            # extract the type from scene, but this is not desired.
            # use type from script class attribute, as it is leading ..
            #type_name = data["type"]
            #if type_name in ENGINE_TYPES:
            #    t = self.resolve_type( ENGINE_TYPES[type_name] )
            #lse:
            #   t = eval( type_name, globals(), locals() )  

            exported = ScriptBehaivior.Exported( raw_value )
            #exported.type = t
            return exported

        # primitive type
        return ScriptBehaivior.Exported( data )

    def saveGameObjectRecursive( self, 
        parent          : "GameObject" = None,
        objects         : Dict[uid.UUID, "GameObject"] = [],
        _gameObjects    : List["SceneManager._GameObject"] = [] 
    ):
        """Recursivly iterate over gameObject and its children"""
        from gameObjects.camera import Camera

        _scene_camera = self.getCamera()
        _scene_sun = self.getSun()

        for obj in objects.values():
            if obj._removed:
                continue

            if obj.parent != parent or obj.parent and parent == None:
                continue

            buffer : SceneManager._GameObject = {
                "uuid"          : obj.uuid.hex,
                "name"          : obj.name,
                "active"        : obj.active,
                "instance"      : type(obj).__name__,
                "visible"       : obj.visible,
                "material"      : obj.material,
                "translate"     : obj.transform.local_position,
                "rotation"      : obj.transform.local_rotation,
                "scale"         : obj.transform.local_scale,
                "scripts": [
                    {
                        "uuid"          : x.uuid.hex,
                        "file"          : str(x.path),
                        "active"        : x.active,
                        "exports"       : { 
                                            k: self.serialize_export( v )
                                                for k, v in x.exports.items() 
                                          }
                    }
                    for x in obj.scripts
                ],
                "instance_data" : {},
                "children"      : []
            }

            if obj.model:
                buffer["model_file"] = str(obj.model_file.relative_to( self.settings.rootdir ))

            # GameObject Types
            if _scene_camera and isinstance( obj, Camera ):
                buffer["instance_data"]["fov"]  = obj.fov
                buffer["instance_data"]["near"] = obj.near
                buffer["instance_data"]["far"]  = obj.far

                if _scene_camera:
                    buffer["instance_data"]["is_default_camera"] = True if obj.uuid == _scene_camera.uuid else False
               
  
            def physicLink( buffer, physic_link ):
                inertia     : PhysicLink.Inertia        = physic_link.inertia
                joint       : PhysicLink.Joint          = physic_link.joint
                collision   : PhysicLink.Collision      = physic_link.collision
                visual      : PhysicLink.Visual         = physic_link.visual

                buffer[ type(physic_link).__name__ ] = {
                    "inertia": {
                        "mass": inertia.mass 
                    },
                    "joint": {
                        "type"          : joint.geom_type,
                    },
                    "collision": {
                        "type"          : collision.geom_type,
                        "translate"     : collision.transform.local_position,
                        "rotation"      : collision.transform.local_rotation,
                        "scale"         : collision.transform.local_scale,

                        "lateral_friction"  : collision.lateral_friction,
                        "rolling_friction"  : collision.rolling_friction,
                        "spinning_friction" : collision.spinning_friction,
                        "restitution"       : collision.restitution,
                        "stiffness"         : collision.stiffness,
                        "damping"           : collision.damping
      
                    },
                    "visual": {
                        "translate"     : visual.transform.local_position,
                        "rotation"      : visual.transform.local_rotation,
                        "scale"         : visual.transform.local_scale
                    }
                }

            # gameObject attachables
            physic : Physic = obj.getAttachable(Physic)
            if physic:
                buffer[ type(Physic).__name__ ] = { 
                    "base_mass"     : float(physic.base_mass)
                }
                physicLink( buffer, physic )

            physic_link : PhysicLink = obj.getAttachable(PhysicLink)
            # if self.physic_link, but explicitly use the designed method for this
            if physic_link:
                physicLink( buffer, physic_link )

            light : Light = obj.getAttachable(Light)
            if light:
                buffer["Light"] = {
                    "light_type"   : light.light_type,
                    "light_color"  : list(light.light_color),
                    "radius"       : light.radius,
                    "intensity"    : light.intensity,
                    "is_sun"       : True if (_scene_sun and obj.uuid == _scene_sun.uuid) else False
                }

            if obj.children:
                self.saveGameObjectRecursive( 
                    obj, 
                    obj.children, 
                    buffer["children"]
                )

            _gameObjects.append( buffer )
        pass

    def saveScene( self, scene_uid : str = False ):
        """Save a scene, only serialize things actually needed
        
        :param scene_uid: The name the scene is saved under, meaning the filename of .scene file. Use current scene name if this is empty
        :type scene_uid: str, optional
        """

        # todo:
        # store path from root dir, not system path
        _scene_uid = scene_uid if scene_uid != False else self.getCurrentSceneUID()

        if _scene_uid == self.settings.default_scene.stem:
            self.console.warn( "Cannot overwrite engine's default empty scene" )
            return
        
        _scene_filename = f"{self.settings.assets}\\{_scene_uid}{self.settings.SCENE_EXTENSION}"
        _scene = self.getCurrentScene()

        scene : SceneManager.Scene = SceneManager.Scene()
        scene["name"]           = _scene["name"]
        scene["ambient_color"]  = list(_scene["ambient_color"])
        scene["sky_type"]       = _scene["sky_type"]

        # procedural sky settings
        scene["procedural_sky_color"]       = _scene["procedural_sky_color"]
        scene["procedural_horizon_color"]   = _scene["procedural_horizon_color"]
        scene["procedural_ground_color"]    = _scene["procedural_ground_color"]
        scene["procedural_sunset_color"]    = _scene["procedural_sunset_color"]
        scene["procedural_night_color"]     = _scene["procedural_night_color"]
        scene["procedural_night_brightness"]     = _scene["procedural_night_brightness"]

        _gameObjects : List[SceneManager._GameObject] = []

        self.saveGameObjectRecursive( 
            None,
            self.context.world.gameObjects, 
            _gameObjects
        )

        scene["gameObjects"] = _gameObjects

        with open(_scene_filename, 'w') as buffer:
            json.dump(scene, buffer, indent=4)

        self.console.note( f"Save scene: {_scene_uid}" )

    def getScene( self, scene_filename : Path ):
        """Load and decode JSON from a scene file

        :param scene_filename: The filename of a .scene
        :type scene_filename: Path
        """
        try:
            with open(scene_filename, 'r') as buffer:
                scene : SceneManager.Scene = json.load(buffer)
                scene["uid"] = scene_filename.stem
                if not any(existing_scene["uid"] == scene["uid"] for existing_scene in self.scenes):
                    self.scenes.append( scene )

        except Exception as e:
            print( e )
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.error( e, traceback.format_tb(exc_tb) )
            
    def getScenes( self ):
        """search assets for .scene files, and calls the getScene to decode them"""
        path = Path(self.settings.assets)

        if any(path.glob("*")):
            for file in path.glob("*"):
                if file.is_file() and file.suffix == self.settings.SCENE_EXTENSION:
                    self.getScene( file )

    def clearEditorScene( self ):
        """Clear the scene in the editor, prepares loading a new scene
        This removes gameObjects, clears editor GUI state, resets camera index.
        """
        self.setCamera( None )
        self.setSun( None )
        self.context.gui.set_selected_object()
        self.context.world.destroyAllGameObjects()
        self.current_scene = -1

        self.console.note( f"Clear current scene in editor" )

    def updateScriptonGameObjects( self, path : Path ) -> None:
        """Re-initialize specific script on GameObjects

        :param path: The path to a .py script file
        :type path: Path
        """
        for obj in self.context.world.gameObjects.values():
            for script in obj.scripts:
                if path != script.path:
                    continue

                # (re)init
                script.init_instance( obj )

    def loadGameObjectsRecursive( self,
        parent          : "GameObject" = None,
        objects         : List["_GameObject"] = [],
        scene_id        : int = -1
    ):
        from gameObjects.mesh import Mesh
        from gameObjects.camera import Camera

        for obj in objects:
            # todo:
            # replace ternary with; .get(key, default)
            model = (self.settings.rootdir / obj["model_file"]).resolve() if "model_file" in obj else False

            # temporary
            if obj["instance"] == "Light":
                obj["instance"] = "Mesh"

            gameObject = self.context.world.addGameObject( eval(obj["instance"])( self.context,
                    uuid        = uid.UUID(hex=obj["uuid"]) if "uuid"       in obj else None, 
                    name        = obj["name"]               if "name"       in obj else "Unknown",
                    model_file  = model,
                    material    = obj["material"]           if "material"   in obj else -1,
                    translate   = obj["translate"]          if "translate"  in obj else [ 0.0, 0.0, 0.0 ],
                    scale       = obj["scale"]              if "scale"      in obj else [ 0.0, 0.0, 0.0 ],
                    rotation    = obj["rotation"]           if "rotation"   in obj else [ 0.0, 0.0, 0.0 ],
                    scripts     = [
                        Script(
                            context     = self.context,
                            uuid        = uid.UUID(hex=x["uuid"]) if "uuid" in x else None,
                            path        = Path(self.settings.rootdir / x["file"]).resolve(),
                            active      = bool(x.get("active", True)),
                            exports     = { 
                                            k: self.deserialize_export( k, v )
                                                for k, v in x.get("exports", {}).items() 
                                          }
                        )
                        for x in obj["scripts"]
                    ]
                )
            )

            if model:
                self.console.log( f"Load model: {model.relative_to(self.settings.rootdir)}" )

            # todo:
            # implement scene settings, so a camera or sun can be assigned
            _instance_data = obj.get("instance_data", {})

            if isinstance( gameObject, Camera ):
                if _instance_data:
                    if "fov"    in _instance_data: gameObject._fov   = _instance_data.get("fov")
                    if "near"   in _instance_data: gameObject._near  = _instance_data.get("near")
                    if "far"    in _instance_data: gameObject._far   = _instance_data.get("far")

                    # set this is current scene/runtime camera
                    if _instance_data.get("is_default_camera", False):
                        self.setCamera( gameObject.uuid, scene_id = scene_id )

            if "active" in obj:
                gameObject.active = obj["active"]

            if "visible" in obj:
                gameObject.visible = obj["visible"]

            if parent:
                gameObject.setParent( parent, update=False )

            #
            # attachables
            #
            if "Light" in obj:
                _light = obj["Light"]
                light_kwargs = {}

                if "light_type"     in _light : light_kwargs["light_type"]  = _light["light_type"]
                if "light_color"    in _light : light_kwargs["light_color"] = list(_light["light_color"])
                if "radius"         in _light : light_kwargs["radius"]      = _light["radius"]
                if "intensity"      in _light : light_kwargs["intensity"]   = _light["intensity"]

                gameObject.addAttachable( Light, Light( 
                    self.context, gameObject, **light_kwargs 
                ) )

                # set this is current scene sun
                if _light.get("is_sun", False):
                    self.setSun( gameObject.uuid, scene_id = scene_id )

            def physicLink( _link : dict, physic_link : PhysicLink | Physic ):
                _inertia        = _link.get("inertia")
                _joint          = _link.get("joint")
                _collision      = _link.get("collision")
                _visual         = _link.get("visual")

                if _inertia:
                    inertia : PhysicLink.Inertia = physic_link.inertia
                    inertia.mass = float(_inertia["mass"])

                if _joint:
                    joint : PhysicLink.Joint = physic_link.joint

                    joint.geom_type = PhysicLink.Joint.Type_( _joint.get( "type", 0 ) )

                if _collision:
                    collision : PhysicLink.Collision = physic_link.collision

                    collision.geom_type    = PhysicLink.GeometryType_( _collision.get( "type", 0 ) )

                    collision.transform.local_position      = tuple(_collision.get( "translate", ( 0.0, 0.0, 0.0 ) ) )
                    collision.transform.local_rotation      = tuple(_collision.get( "rotation",  ( 0.0, 0.0, 0.0 ) ) )
                    collision.transform.local_scale         = tuple(_collision.get( "scale",     ( 1.0, 1.0, 1.0 ) ) )

                    collision.transform.is_physic_shape = True
                    collision._update_transform()
                    
                    # contact
                    collision.lateral_friction  = float(_collision.get("lateral_friction", 0.8 ) )
                    collision.rolling_friction  = float(_collision.get("rolling_friction", 0.0 ) )
                    collision.spinning_friction = float(_collision.get("spinning_friction", 0.0 ) )
                    collision.restitution       = float(_collision.get("restitution", 0.0 ) )
                    collision.stiffness         = float(_collision.get("stiffness", -1.0 ) )
                    collision.damping           = float(_collision.get("damping", -1.0 ) )

                if _visual:
                    visual : PhysicLink.Visual = physic_link.visual

                    visual.transform.local_position      = tuple(_visual.get( "translate", ( 0.0, 0.0, 0.0 ) ) )
                    visual.transform.local_rotation      = tuple(_visual.get( "rotation",  ( 0.0, 0.0, 0.0 ) ) )
                    visual.transform.local_scale         = tuple(_visual.get( "scale",     ( 1.0, 1.0, 1.0 ) ) )

                    visual.transform.is_physic_shape = True
                    visual._update_transform()

            if "Physic" in obj:
                _physic = obj["Physic"]

                gameObject.addAttachable( Physic, Physic( self.context, gameObject ) )
                gameObject.physic.base_mass = _physic.get("base_mass", -1.0)

                physicLink( _physic, gameObject.physic )

            if "PhysicLink" in obj:
                _physic_link    = obj["PhysicLink"]

                gameObject.addAttachable( PhysicLink, PhysicLink( self.context, gameObject ) )
                physicLink( _physic_link, gameObject.physic_link )

            if "children" in obj:
                self.loadGameObjectsRecursive( 
                    gameObject, 
                    obj["children"], 
                    scene_id=scene_id
                )

        pass


    def loadScene( self, scene_uid : str ) -> bool:
        """Load scene (does not work with multiple scenes yet), if this return false, the engine will proceed to load the default scene.
        
        :param scene_uid: The name the scene is saved under, meaning the filename of .scene file.
        :type scene_uid: str
        :return: True of the scene loaded succesfully, False if was not found or errors occured
        :rtype: bool
        """

        for i, scene in enumerate(self.scenes):
            if scene["uid"] != scene_uid:
                continue

            self.console.note( f"Loading scene: {scene_uid}" )

            try:
                self.setCamera( None, scene_id = i ) # default to None, find default camera when adding gameObjects
                self.setSun( None, scene_id = i ) # default to None, find sun when adding gameObjects
                    
                scene["name"]           = scene.get("name", "default scene")
                scene["ambient_color"]  = scene.get("ambient_color",    self.settings.default_ambient_color )
                scene["sky_type"]       = scene.get("sky_type",         self.settings.default_sky_type )

                # procedural sky settings
                scene["procedural_sky_color"]       = scene.get("procedural_sky_color",     self.settings.default_procedural_sky_color )
                scene["procedural_horizon_color"]   = scene.get("procedural_horizon_color", self.settings.default_procedural_horizon_color )
                scene["procedural_ground_color"]    = scene.get("procedural_ground_color",  self.settings.default_procedural_ground_color )
                scene["procedural_sunset_color"]    = scene.get("procedural_sunset_color",  self.settings.default_procedural_sunset_color )
                scene["procedural_night_color"]     = scene.get("procedural_night_color",   self.settings.default_procedural_night_color )
                scene["procedural_night_brightness"]     = scene.get("procedural_night_brightness",   self.settings.default_procedural_night_brightness )

                if "gameObjects" in scene: 
                    self.loadGameObjectsRecursive( 
                        None, 
                        scene["gameObjects"], 
                        scene_id=i
                    )

            except Exception as e:
                print( e )
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.error( e, traceback.format_tb(exc_tb) ) 
            else:
                self.current_scene =  i
                self.console.note( f"Scene {scene_uid} loaded successfully" )

                self.postLoadScene()
                return True

        # load default scene
        if self.current_scene < 0:
            self.console.error( f"Could not find scene: {scene_uid}" )

            self.postLoadScene()
            return False

    def postLoadScene( self ) -> None:
        self.context.renderer.ubo_materials._dirty = True

    def loadDefaultScene( self ):
        """Load the default scene, meaing the engine empty scene"""
        self.loadScene( self.settings.default_scene.stem )

    def getDefaultScene( self ) -> Scene:
        """Get reference to the default engine empty scene
        
        :return: reference to scene
        :rtype: Scene
        """
        return self.getSceneByUID( self.settings.default_scene.stem )
