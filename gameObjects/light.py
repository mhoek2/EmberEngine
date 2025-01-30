from gameObjects.gameObject import GameObject

class Light( GameObject ):

    def __init__(self, context, *args, **kwargs):
        """Base class for Light gameObjects, holds the various light types

        :param context: This is the main context of the application
        :type context: EmberEngine
        :param *args: Additional positional arguments to be passed to the parent class or other parts of the system
        :type *args: tuple
        :param **kwargs: Additional keyword arguments to be passed to the parent class or other parts of the system
        :type **kwargs: dict
        """
        super().__init__(context, *args, **kwargs)

        self.LIGHT_TYPE_DIRECTIONAL = 0
        self.LIGHT_TYPE_SPOT = 1
        self.LIGHT_TYPE_AREA = 2

        #self.light_type = kwargs.get('light_type', 1.0)
        self.light_type = self.LIGHT_TYPE_DIRECTIONAL

    def onStart( self ) -> None:
        """Executes whenever the object is added to scene"""
        if self.model_file:
            self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        """Executes every frame, issuing draw commands"""
        if self.model != -1 and self.visible:
            self.models.draw( self.model, self._createModelMatrix() )     