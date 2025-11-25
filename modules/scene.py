#from __future__ import annotations

from pyexpat import model
import sys
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, TypedDict
import json
import uuid as uid

from modules.console import Console
from modules.settings import Settings


if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject
    from gameObjects.camera import Camera

import traceback

class SceneManager:
    class Scene(TypedDict):
        """Typedef for a scene file"""
        uid             : str
        name            : str
        gameObjects     : List["_GameObject"]
        camera          : int
        light_color     : List[float]
        ambient_color   : List[float]

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
        scripts     : List["GameObject.Script"]
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

    def setCamera( self, uid : int, scene_id = -1):
        """Set the current camera based on gameObject uid

        :param uid: The uid of a Camera gameObject
        :type uid: int
        :param scene_id: The index in scens List of the scene the camera is set on, current scene when empty
        :type scene_id: int, optional
        """
        from gameObjects.camera import Camera

        scene = scene_id if scene_id >= 0 else self.current_scene

        self.scenes[scene]["camera"] = uid

        # mark camera as default/start scene camera
        for i, obj in enumerate(self.context.gameObjects):
            if isinstance(obj, Camera) and i == uid:
                obj.is_default_camera = True

    def getCamera( self ):
        """Get the current default/start camera

        :return: The current scene default/start camera, False if this fails
        :rtype: Camera or bool
        """
        try:
            _scene_camera_id = self.scenes[self.current_scene]["camera"]

            if _scene_camera_id == -1:
                raise IndexError("invalid camera")

            return self.context.gameObjects[_scene_camera_id]
        except Exception as e:
            #print( e )
            #exc_type, exc_value, exc_tb = sys.exc_info()
            #self.console.error( e, traceback.format_tb(exc_tb) )
            return False

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

            _scene_filename = f"{self.settings.assets}\\{_scene_uid}.scene"
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

    def saveGameObjectRecursive( self, 
        parent          : "GameObject" = None,
        objects         : List["GameObject"] = [],
        _gameObjects    : List["SceneManager._GameObject"] = [] 
    ):
        """Recursivly iterate over gameObject and its children"""
        from gameObjects.camera import Camera

        for obj in objects:
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
                "model_file"    : str(obj.model_file.relative_to(self.settings.rootdir)),
                "material"      : obj.material,
                "translate"     : obj.transform.local_position,
                "rotation"      : obj.transform.local_rotation,
                "scale"         : obj.transform.local_scale,
                "mass"          : obj.mass,
                #"scripts"       : [str(x["path"]) for x in obj.scripts],
                "scripts": [
                    {
                        "file": str(x["path"]),
                        "active": x["active"],
                        #"class_name": x["class_name"],
                        "exports": { k: v.default for k, v in x["exports"].items() }
                    }
                    for x in obj.scripts
                ],
                "instance_data" : {},
                "children"      : []
            }

            if isinstance( obj, Camera ):
                buffer["instance_data"]["is_default_camera"] = obj.is_default_camera

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
        
        _scene_filename = f"{self.settings.assets}\\{_scene_uid}.scene"
        _scene = self.getCurrentScene()

        scene : SceneManager.Scene = SceneManager.Scene()
        scene["name"]           = _scene["name"]
        scene["light_color"]    = _scene["light_color"]
        scene["ambient_color"]  = _scene["ambient_color"]

        _gameObjects : List[SceneManager._GameObject] = []

        self.saveGameObjectRecursive( 
            None,
            self.context.gameObjects, 
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
                if file.is_file() and file.suffix == ".scene":
                    self.getScene( file )

    def clearEditorScene( self ):
        """Clear the scene in the editor, prepares loading a new scene
        This removes gameObjects, clears editor GUI state, resets camera index.
        """
        self.context.sun = -1
        self.setCamera( -1 )
        self.context.gui.set_selected_object()
        self.context.gameObjects.clear()
        self.current_scene = -1

        self.console.note( f"Clear current scene in editor" )

    def updateScriptonGameObjects( self, path : Path ) -> None:
        """Re-initialize specific script on GameObjects

        :param path: The path to a .py script file
        :type path: Path
        """
        for obj in self.context.gameObjects:
            for script in obj.scripts:
                if path != script["path"]:
                    continue

                # reload
                try:
                    obj.init_external_script( script )

                except Exception as e:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    self.console.error( e, traceback.format_tb(exc_tb) )

    def loadGameObjectsRecursive( self,
        parent          : "GameObject" = None,
        objects         : List["_GameObject"] = [],
        scene_id        : int = -1
    ):
        from gameObjects.mesh import Mesh
        from gameObjects.camera import Camera
        from gameObjects.light import Light

        for obj in objects:
            # todo:
            # replace ternary with; .get(key, default)
            model = (self.settings.rootdir / obj["model_file"]).resolve() if "model_file" in obj else False

            index = self.context.addGameObject( eval(obj["instance"])( self.context,
                    uuid        = uid.UUID(hex=obj["uuid"]) if "uuid"       in obj else None, 
                    name        = obj["name"]               if "name"       in obj else "Unknown",
                    #visible     = obj["visible"]            if "visible"    in obj else True,
                    model_file  = model,
                    material    = obj["material"]           if "material"   in obj else -1,
                    translate   = obj["translate"]          if "translate"  in obj else [ 0.0, 0.0, 0.0 ],
                    scale       = obj["scale"]              if "scale"      in obj else [ 0.0, 0.0, 0.0 ],
                    rotation    = obj["rotation"]           if "rotation"   in obj else [ 0.0, 0.0, 0.0 ],
                    mass        = obj["mass"]               if "mass"       in obj else -1.0,
                    #scripts     = [Path((self.settings.rootdir / x).resolve()) for x in obj["scripts"]]
                    scripts     = [
                        {
                            "path": (self.settings.rootdir / x["file"]).resolve(),
                            "active": bool(x.get("active", True)),
                            "exports": x.get("exports", {})
                        }
                        for x in obj["scripts"]
                    ]
                )
            )

            if model:
                self.console.log( f"Load model: {model.relative_to(self.settings.rootdir)}" )

            # reference added gameObject
            gameObject = self.context.gameObjects[index]

            # todo:
            # implement scene settings, so a camera or sun can be assigned
            if isinstance( gameObject, Light ):
                self.context.sun = index

            if isinstance( gameObject, Camera ):
                if obj.get("instance_data", {}).get("is_default_camera", False):
                    self.setCamera( index, scene_id = scene_id )

            if "active" in obj:
                gameObject.active = obj["active"]

            if "visible" in obj:
                gameObject.visible = obj["visible"]

            if parent:
                gameObject.setParent( parent, update=False )

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
                self.setCamera( -1, scene_id = i ) # default to None, find default camera when adding gameObjects
                    
                scene["name"]    = scene.get("name", "default scene")

                scene["light_color"]    = scene.get("light_color",      self.settings.default_light_color)
                scene["ambient_color"]  = scene.get("ambient_color",    self.settings.default_ambient_color)

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
                return True

        # load default scene
        if self.current_scene < 0:
            self.console.error( f"Could not find scene: {scene_uid}" )
            return False

    def loadDefaultScene( self ):
        """Load the default scene, meaing the engine empty scene"""
        self.loadScene( self.settings.default_scene.stem )

    def getDefaultScene( self ) -> Scene:
        """Get reference to the default engine empty scene
        
        :return: reference to scene
        :rtype: Scene
        """
        return self.getSceneByUID( self.settings.default_scene.stem )
