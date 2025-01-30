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
        self.translate  = self.gameObject.translate
        self.rotation   = self.gameObject.rotation
        self.scale      = self.gameObject.scale

