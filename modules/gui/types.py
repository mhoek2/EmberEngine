from typing import TypedDict, Any
from modules.context import Context

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.camera import Camera
from gameObjects.skybox import Skybox

import enum

class RotationMode_(enum.IntEnum):
    """Modes to visualize rotation angles"""
    radians = enum.auto()
    degrees = enum.auto()

class RadioStruct(TypedDict):
    name    : str
    icon    : str
    flag    : int

class ToggleStruct(TypedDict):
    name    : str
    icon    : str

class CustomEvent( Context ):
    def __init__(self):
        self._queue : list = []

    def add(self, name: str, data=None):
        self._queue.append((name, data))

    def has(self, name: str) -> bool:
        """Return True if queue has given entry, Fales if not"""
        return any(event[0] == name for event in self._queue)

    def clear(self, name: str = None):
        """Clear given entry by rebuilding and excluding, no argument will clear entire queue"""
        if name is None: 
            self._queue.clear()

        else:
            self._queue = [e for e in self._queue if e[0] != name]

    def handle(self, name: str, func):
        """Call the given function if the event exists, then clear it automatically."""
        if self.has(name):
            func()
            self.clear(name)

class DragAndDropPayload:
    class Type_(enum.StrEnum):
        """Explicit source or acceptance types"""
        hierarchy   = enum.auto()
        asset       = enum.auto()

    def __init__(self, 
                    type_id : str = None, 
                    data_id : int = None,
                    data : Any = None ):
        """Wrapper to store additional drag and drop payload data"""
        self.type_id    = type_id
        self.data_id    = data_id
        self.data       = data

    def set_payload( self, type_id : str, data_id : int, data : Any ):
        self.type_id    = type_id
        self.data_id    = data_id
        self.data       = data

        imgui.set_drag_drop_payload_py_id( type=self.type_id, data_id=self.data_id)

    def get_payload_type(self) -> str:
        return self.type_id

    def get_payload_data_id(self) -> int:
        return self.data_id

    def get_payload_data(self):
        return self.data

class GameObjectTypes:
    """Bind meta data to gameObject types, currently only used for the UserInterface
        
    Whenever this finds use in a global scope, move this to: modules.gameObjectTypes.py
    """
    _registry = None

    class Meta:
        """Structure that hold meta data per gameObject type"""
        def __init__( self, _class : type, _icon : str = "" ):
            self._name      = _class.__name__
            self._class     = _class
            self._icon      = _icon

    @staticmethod
    def registry():
        """Singleton registry of the gameObject types (inherting GameObject).

            _registry is stored as a class variable, meaniung:

            - initialized only once per Python process
            - shared across all imports and all scripts

        :return: Map of gameObject type classes to Meta
        :rtype: dict
        """
        if GameObjectTypes._registry is None:
            GameObjectTypes._registry = {
                Camera: GameObjectTypes.Meta( 
                    _class  = Camera, 
                    _icon   = fa.ICON_FA_CAMERA
                ),
                Mesh: GameObjectTypes.Meta( 
                    _class  = Mesh, 
                    _icon   = fa.ICON_FA_CUBE
                ),
                Light: GameObjectTypes.Meta( 
                    _class  = Light, 
                    _icon   = fa.ICON_FA_LIGHTBULB
                ),

                # baseclass
                GameObject: GameObjectTypes.Meta( 
                    _class  = GameObject, 
                    _icon   = fa.ICON_FA_CIRCLE_DOT
                ),
            }

        return GameObjectTypes._registry

    @staticmethod
    def is_gameobject_type( t : type ) -> bool:
        """Check wheter a type is registered as gameObject type
        
        :param t: The type of a variable, e.g., type(variable)
        :type t: type
        :return: True if t is a registered gameObject type
        :rtype: bool
        """
        return t in GameObjectTypes.registry()

    @staticmethod
    def get_gameobject_type( t : type ) -> Meta:
        """Get the gameObject type meta

        :param t: The type of a variable, e.g., type(variable)
        :type t: type
        :return: Meta object if t is a registered gameObject type, None if not
        :rtype: Meta
        """
        if not GameObjectTypes.is_gameobject_type( t ):
            return None

        return GameObjectTypes.registry()[t]

class TransformMask:
    position    :int = 0
    rotation    :int = 1
    scale       :int = 2

    _keys = [
        "position", 
        "rotation", 
        "scale"
    ]

    def __init__( self, values=None ):
        if values is None:
            values = [1, 1, 1]

        self._values = list( values[:3] )

    def __getitem__( self, index ):
        return self._values[index]

    def __setitem__( self, index, value ):
        self._values[index] = value

    def _resolve_idx( self, key ):
        if isinstance( key, int ):
            return key

        elif isinstance( key, str ):
            return self._keys.index(key)

    def is_visible( self, key ):
        return self._values[ self._resolve_idx( key ) ] != 0

    def is_enabled( self, key ):
        return self._values[ self._resolve_idx( key ) ] == 1