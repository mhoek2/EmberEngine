class ScriptBehaivior:
    def __init__( self, context, gameObject ):
        """Base class for dynamic loaded scripts, 
        setting up references to context, events and the gameObject itself
        
        :param context: This is the main context of the application
        :type context: EmberEngine
        :param gameObject: A reference to the gameObject the script is attached to
        :type gameObject: GameObject
        """
        self.context    = context
        self.settings   = context.settings
        self.renderer   = context.renderer
        self.scene      = context.scene
        self.console    = context.console

        self.events     = context.events
        self.key        = context.key
        self.mouse      = context.mouse

        self.gameObject = gameObject
        self.transform  = self.gameObject.transform

    def onStart( self ):
        """Implemented by script"""
        pass

    def onUpdate( self ):
        """Implemented by script"""
        pass

    def onEnable( self ):
        """Implemented by script"""
        pass

    def onDisable( self ):
        """Implemented by script"""
        pass

    #
    # export class attributes
    #
    class Exported:
        def __init__( self, default=None ):
            self.default    = default
            self.type       = type(default)  # validated in __set_name__
            self.active     = True

        def default_for_annotation_type( self, t ):
            if t is int:
                return 0
            if t is float:
                return 0.0
            if t is bool:
                return False
            if t is str:
                return ""

            # get value for default datatypes
            try:
                return t()

            except Exception:
                return None

        def __set_name__( self, owner, name ):
            """Allows to set a custom datatype, compare default value type with the annotated (: str) type
            Mark as disabled when it does not match.
            """
            annotated_type = None

            if hasattr(owner, '__annotations__'):
                annotated_type = owner.__annotations__.get(name)

            if annotated_type:
                self.type = annotated_type # override manual datatype

                # no default value, just initialize to 0 or "" or False based on requrested type
                if not self.default:
                    self.default = self.default_for_annotation_type( annotated_type )
                    return

                # must match default value, just throw and error for now
                # or .. we can do same as above?
                if self.default is not None and not isinstance(self.default, annotated_type):
                    self.default = None
                    self.active = False

                    print(
                        f"Exported attribute '{name}' expected type "
                        f"{annotated_type.__name__}, got {type(self.default).__name__}"
                    )

        def get( self ):
            return self.default

        def set( self, value ):
            if not isinstance(value, self.type):
                print("type mismatch")
                return

            self.default = value

    def export( default=None ):
        return ScriptBehaivior.Exported( default )
