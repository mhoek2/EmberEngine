from gameObjects.gameObject import GameObject

class Light( GameObject ):

    def __init__(self, context, *args, **kwargs):
        super().__init__(context, *args, **kwargs)

        self.LIGHT_TYPE_DIRECTIONAL = 0
        self.LIGHT_TYPE_SPOT = 1
        self.LIGHT_TYPE_AREA = 2

        #self.light_type = kwargs.get('light_type', 1.0)
        self.light_type = self.LIGHT_TYPE_DIRECTIONAL

    def onStart( self ) -> None:
        if self.model_file:
            self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        if self.model != -1 and self.visible:
            self.models.draw( self.model, self._createModelMatrix() )     