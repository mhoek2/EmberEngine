from gameObjects.gameObject import GameObject

class Mesh( GameObject ):
    """Base class for regular gameObjects, with mesh or empty, Derived from GameObject Class"""
    def onStart( self ) -> None:
        """Executes whenever the object is added to scene"""
        if self.model_file:
            self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        """Executes every frame, issuing draw commands"""
        if self.model != -1 and self.visible:
            self.models.draw( self.model, self._createModelMatrix(includeParent=not self.settings.game_running) )     