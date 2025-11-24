class ScriptBehaivior:
    def __init__( self, context, gameObject ):
        """Base class for dynamic loaded scripts, 
        setting up references to context, events and the gameObject itself
        
        :param context: This is the main context of the application
        :type context: EmberEngine
        :param gameObject: A reference to the gameObject the script is attached to
        :type gameObject: GameObject
        """
        self.context = context
        self.settings = context.settings
        self.renderer = context.renderer
        self.scene = context.scene

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
            self.set(default)

        def get( self ):
            return self.default

        def set( self, value ):
            self.default = value
            self.type = type(value)

    def export( default=None ):
        return ScriptBehaivior.Exported( default )
