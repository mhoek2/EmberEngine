class ScriptBehaivior:
    def __init__( self, context, gameObject ):
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

