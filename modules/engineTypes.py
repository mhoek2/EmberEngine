class EngineTypes:
    _registry = None

    class Meta:
        """Structure that hold meta data per engine type, name and class reference"""
        def __init__( self, _class ):
            self._name    = _class.__name__
            self._class   = _class              

    @staticmethod
    def registry():
        """Singleton registry of the exportable engine types (components).

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

            EngineTypes._registry = {
                Transform: EngineTypes.Meta( Transform ),
                GameObject: EngineTypes.Meta( GameObject ),
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

