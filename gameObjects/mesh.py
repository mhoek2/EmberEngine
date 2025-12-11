from gameObjects.gameObject import GameObject

class Mesh( GameObject ):
    """Base class for regular gameObjects, with mesh or empty, Derived from GameObject Class"""
    def onStart( self ) -> None:
        super().onStart()

        """Executes whenever the object is added to scene"""
        if self.model_file:
            self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        """Executes every frame, issuing draw commands"""
        super().onUpdate()

        if not self.hierachyActive():
            return

        is_visible : bool = True if self.renderer.game_runtime else self.hierachyVisible()
        
        if self.model != -1 and is_visible:
            self.models.draw( self.model, self.transform._getModelMatrix() ) 
