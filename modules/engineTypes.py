from typing import Any

class EngineTypes:
    _registry = None

    class Meta:
        """Structure that hold meta data per engine type, name and class reference"""
        def __init__( self, _class, attachable ):
            self._name      : str       = _class.__name__
            self._class     : type[Any] = _class   
            self.attachable : bool      = attachable

    @staticmethod
    def registry():
        """Singleton registry of the exportable engine types and engine attachables.

            _registry is stored as a class variable, meaniung:

            - initialized only once per Python process
            - shared across all imports and all scripts

        :return: Map of engine type classes to Meta
        :rtype: dict
        """
        if EngineTypes._registry is None:
            # initialize the registry
            from gameObjects.gameObject import GameObject
            from modules.transform import Transform
            from gameObjects.attachables.light import Light
            from gameObjects.attachables.physic import Physic
            from gameObjects.attachables.physicLink import PhysicLink
            from gameObjects.attachables.model import Model

            EngineTypes._registry = {
                Transform   : EngineTypes.Meta( Transform,    attachable=False ),
                GameObject  : EngineTypes.Meta( GameObject,   attachable=False ),
                Light       : EngineTypes.Meta( Light,        attachable=True ),
                Physic      : EngineTypes.Meta( Physic,       attachable=True ),
                Model       : EngineTypes.Meta( Model,        attachable=True ),
            }

        return EngineTypes._registry

    @staticmethod
    def is_engine_type( t : type ) -> bool:
        """Check wheter a type is registered as engine type
        
        :param t: The type of a variable, e.g., type(variable)
        :type t: type
        :return: True if t is a registered engine type
        :rtype: bool
        """
        return t in EngineTypes.registry()

    @staticmethod
    def get_engine_type( t : type ) -> Meta:
        """Get the engine type meta

        :param t: The type of a variable, e.g., type(variable)
        :type t: type
        :return: Meta object if t is a registered engine type, None if not
        :rtype: Meta
        """
        if not EngineTypes.is_engine_type( t ):
            return None

        return EngineTypes.registry()[t]

    @staticmethod
    def is_primitive_type( t : type ) -> bool:
        """Wheter a type is a primitive type.

        :param t: Type to check
        :type t: type
        :return: True if t is int, float, bool, or str
        :rtype: bool
        """
        return t in (int, float, bool, str)

    def getAttachables() -> list:
        return [
            meta
            for _class, meta in EngineTypes.registry().items()
                if meta.attachable
        ]

    def is_attachable() -> bool:
        meta = EngineTypes.get_engine_type(t)
        return meta.attachable if meta else False
