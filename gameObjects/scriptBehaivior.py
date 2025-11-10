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
        self._translate = self.gameObject._translate
        self._rotation   = self.gameObject._rotation
        self.scale      = self.gameObject.scale

    # translate
    @property
    def translate(self):
        return self._translate
    
    @translate.setter
    def translate(self, value):
        self._translate.set(value)

    # rotation
    @property
    def rotation(self):
        return self._rotation
    
    @rotation.setter
    def rotation(self, value):
        self._rotation.set(value)
