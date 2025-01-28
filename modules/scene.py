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
        name        : str
        gameObjects : List["_GameObject"]
        camera      : int

    class _GameObject(TypedDict):
        instance    : str
        visible     : bool
        name        : str
        model_file  : str
        material    : int
        translate   : List[int]
        rotation    : List[int]
        scale       : List[int]
        scripts     : List[str]
        instance_data : Dict # additional instance data

    def __init__( self, context ) -> None:
        """scene manager"""
        self.context    : 'EmberEngine' = context
        self.settings   : Settings = context.settings
        self.console    : Console = context.console

        self.scenes     : List[SceneManager.Scene] = []

        self.current_scene : int = -1
        self._window_is_open    : bool = False # imgui state

    def toggleWindow( self ):
        self._window_is_open = not self._window_is_open

    def setCamera( self, camera_id : int, scene_id = False):
        from gameObjects.camera import Camera

        _scene_id = scene_id if scene_id != False else self.current_scene

        self.scenes[_scene_id]["camera"] = camera_id

        # mark camera as default/start scene camera
        for i, obj in enumerate(self.context.gameObjects):
            if isinstance(obj, Camera) and i == camera_id:
                obj.is_default_camera = True

    def getCamera( self ):
        try:
            _scene_camera_id = self.scenes[self.current_scene]["camera"]

            if _scene_camera_id == -1:
                raise IndexError("invalid camera")

            return self.context.gameObjects[_scene_camera_id]
        except IndexError:
            return False

    def saveScene( self ):
        """Save a scene, only serialize things actually needed"""
        from gameObjects.camera import Camera

        # todo:
        # store path from root dir, not system path

        _scene_filename = f"{self.settings.assets}\\main.scene"

        scene : SceneManager.Scene = SceneManager.Scene()
        scene["name"] = "main scene"

        _gameObjects : List[SceneManager._GameObject] = []
        for obj in self.context.gameObjects:
            if obj._removed:
                continue

            buffer : SceneManager._GameObject = {
                "instance"      : type(obj).__name__,
                "visible"       : obj.visible,
                "name"          : obj.name,
                "model_file"    : obj.model_file,
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

    def getScene( self, _scene_filename ):
        try:
            with open(_scene_filename, 'r') as buffer:
                scene = json.load(buffer)
                self.scenes.append( scene )

        except Exception as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e )
            
    def getScenes( self ):
        # search assets for .scene files
        path = Path(self.settings.assets)

        if any(path.glob("*")):
            for file in path.glob("*"):
                if file.is_file() and file.suffix == ".scene":
                    self.getScene( file )


    def loadScene( self, is_default = False ):
        from gameObjects.mesh import Mesh
        from gameObjects.camera import Camera
        from gameObjects.light import Light

        for i, scene in enumerate(self.scenes):
            try:
                self.setCamera( -1, scene_id = i ) # default to None, find default camera when adding gameObjects

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
                exc_type, exc_value, exc_tb = sys.exc_info()
                self.console.addEntry( self.console.ENTRY_TYPE_ERROR, traceback.format_tb(exc_tb), e )
            
            else:
                self.current_scene =  i
                return

        # load default scene
        if self.current_scene < 0 and not is_default:
            self.getScene( self.settings.default_scene )
            self.loadScene( is_default=True )
        print("save")