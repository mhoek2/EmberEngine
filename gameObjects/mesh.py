from gameObjects.gameObject import GameObject

class Mesh( GameObject ):
    def onStart( self ) -> None:
        self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        self.models.draw( self.model, self._createModelMatrix() )     