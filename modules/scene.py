from pyexpat import model
import sys
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, TypedDict
import json

from modules.console import Console
from modules.settings import Settings

if TYPE_CHECKING:
    from main import EmberEngine

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
        scripts     : List[str]
        instance_data : Dict # additional instance data

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
        self._window_is_open    : bool = False # imgui window state

    def toggleWindow( self ):
        """Toggle imgui window state"""
        self._window_is_open = not self._window_is_open

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
        try:
            return self.scenes[self.current_scene]["uid"]
        except:
            return self.settings.default_scene.stem

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
            #self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e )
            return False

    def saveScene( self ):
        """Save a scene, only serialize things actually needed"""
        from gameObjects.camera import Camera

        # todo:
        # store path from root dir, not system path

        _scene_filename = f"{self.settings.assets}\\main.scene"
        _scene = self.getCurrentScene()

        scene : SceneManager.Scene = SceneManager.Scene()
        scene["name"]           = "main scene"
        scene["light_color"]    = _scene["light_color"]
        scene["ambient_color"]  = _scene["ambient_color"]

        _gameObjects : List[SceneManager._GameObject] = []
        for obj in self.context.gameObjects:
            if obj._removed:
                continue

            buffer : SceneManager._GameObject = {
                "instance"      : type(obj).__name__,
                "visible"       : obj.visible,
                "name"          : obj.name,
                "model_file"    : str(obj.model_file),
                "material"      : obj.material,
                "translate"     : obj.translate,
                "scale"         : obj.scale,
                "rotation"      : obj.rotation,
                "scripts"       : [str(x["file"]) for x in obj.scripts],
                "instance_data" : {}
            }

            if isinstance( obj, Camera ):
                buffer["instance_data"]["is_default_camera"] = obj.is_default_camera

            _gameObjects.append( buffer )

        scene["gameObjects"] = _gameObjects

        with open(_scene_filename, 'w') as buffer:
            json.dump(scene, buffer, indent=4)

        print("save")

    def getScene( self, scene_filename : Path ):
        """Load and decode JSON from a scene file

        :param scene_filename: The filename of a .scene
        :type scene_filename: Path
        """
        try:
            with open(scene_filename, 'r') as buffer:
                scene : SceneManager.Scene = json.load(buffer)
                scene["uid"] = scene_filename.stem
                self.scenes.append( scene )

        except Exception as e:
            print( e )
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e )
            
    def getScenes( self ):
        """search assets for .scene files, and calls the getScene to decode them"""
        path = Path(self.settings.assets)

        if any(path.glob("*")):
            for file in path.glob("*"):
                if file.is_file() and file.suffix == ".scene":
                    self.getScene( file )

    def loadScene( self, scene_uid : str ) -> bool:
        """Load scene (does not work with multiple scenes yet), if this return false, the engine will proceed to load the default scene."""
        from gameObjects.mesh import Mesh
        from gameObjects.camera import Camera
        from gameObjects.light import Light

        for i, scene in enumerate(self.scenes):
            if scene["uid"] != scene_uid:
                continue

            try:
                self.setCamera( -1, scene_id = i ) # default to None, find default camera when adding gameObjects
                
                scene["light_color"]    = scene.get("light_color",      self.settings.default_light_color)
                scene["ambient_color"]  = scene.get("ambient_color",    self.settings.default_ambient_color)

                if "gameObjects" in scene: 
                    for obj in scene["gameObjects"]:
                        # todo:
                        # replace ternary with; .get(key, default)
                        index = self.context.addGameObject( eval(obj["instance"])( self.context,
                                name        = obj["name"]       if "name"       in obj else "Unknown",
                                visible     = obj["visible"]    if "visible"    in obj else True,
                                model_file  = obj["model_file"] if "model_file" in obj else False,
                                material    = obj["material"]   if "material"   in obj else -1,
                                translate   = obj["translate"]  if "translate"  in obj else [ 0.0, 0.0, 0.0 ],
                                scale       = obj["scale"]      if "scale"      in obj else [ 0.0, 0.0, 0.0 ],
                                rotation    = obj["rotation"]   if "rotation"   in obj else [ 0.0, 0.0, 0.0 ],
                                scripts     = [Path(x) for x in obj["scripts"]]
                            )
                        )

                        # todo:
                        # implement scene settings, so a camera or sun can be assigned
                        if isinstance( self.context.gameObjects[index], Light ):
                            self.context.sun = index

                        if isinstance( self.context.gameObjects[index], Camera ):
                            if obj.get("instance_data", {}).get("is_default_camera", False):
                                self.setCamera( index, scene_id = i )

            except Exception as e:
                print( e )
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e ) 
            else:
                self.current_scene =  i
                return True

        # load default scene
        if self.current_scene < 0:
            return False

    def loadDefaultScene( self ):
        self.loadScene( self.settings.default_scene.stem )
