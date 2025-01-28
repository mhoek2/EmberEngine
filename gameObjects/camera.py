from gameObjects.gameObject import GameObject

class Camera( GameObject ):
    def __init__(self, context, *args, **kwargs):
        super().__init__(context, *args, **kwargs)

        self.is_default_camera = False

    def onStart( self ) -> None:
        self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        if not self.settings.game_running:
            self.models.draw( self.model, self._createModelMatrix() )   
