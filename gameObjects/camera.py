from gameObjects.gameObject import GameObject

class Camera( GameObject ):
    def __init__(self, context, *args, **kwargs):
        """Class that handles camera objects, Derived from GameObject Class

        :param context: This is the main context of the application
        :type context: EmberEngine
        :param *args: Additional positional arguments to be passed to the parent class or other parts of the system
        :type *args: tuple
        :param **kwargs: Additional keyword arguments to be passed to the parent class or other parts of the system
        :type **kwargs: dict
        """
        super().__init__(context, *args, **kwargs)

        self.is_default_camera = False

    def onStart( self ) -> None:
        """Executes whenever the object is added to scene"""
        super().onStart()

        self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        """Executes every frame, issuing draw commands"""
        super().onUpdate()

        if not self.settings.game_running:
            self.models.draw( self.model, self.transform._getModelMatrix() )   
