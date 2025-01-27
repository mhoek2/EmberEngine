from gameObjects.gameObject import GameObject

class Mesh( GameObject ):
    def onStart( self ) -> None:
        if self.model_file:
            self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        if self.model != -1:
            self.models.draw( self.model, self._createModelMatrix() )     