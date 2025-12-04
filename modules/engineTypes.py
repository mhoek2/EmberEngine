class EngineTypes:
    _registry = None

    class EngineTypeInfo:
        def __init__( self, _class ):
            self._name    = _class.__name__
            self._class   = _class              

    @staticmethod
    def registry():
        if EngineTypes._registry is None:
            from gameObjects.gameObject import GameObject
            from modules.transform import Transform

            EngineTypes._registry = {
                Transform: EngineTypes.EngineTypeInfo( Transform ),
                GameObject: EngineTypes.EngineTypeInfo( GameObject ),
            }

        return EngineTypes._registry

    @staticmethod
    def is_engine_type( t ) -> bool:
        # first idea was to create a list of just the names of the engine types ..
        #return type(obj).__name__ in ("Transform", "GameObject")
        # or
        #return t.__name__ in ("Transform", "GameObject")

        # use a registry dictionary instead
        return t in EngineTypes.registry()

    @staticmethod
    def get_engine_type( t ) -> bool:
        if not EngineTypes.is_engine_type( t ):
            return None

        return EngineTypes.registry()[t]

    @staticmethod
    def is_primitive_type( t ) -> bool:
        """Wheter a type is of primitive type.

        :param t: Type to check
        :return: True if t is int, float, bool, or str
        """
        return t in (int, float, bool, str)

