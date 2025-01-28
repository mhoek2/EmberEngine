from gameObjects.gameObject import GameObject

class Camera( GameObject ):
    def onStart( self ) -> None:
        self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        if not self.settings.game_running:
            self.models.draw( self.model, self._createModelMatrix() )   
