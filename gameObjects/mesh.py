from gameObjects.gameObject import GameObject

from OpenGL.GL import *

class Mesh( GameObject ):
    """Base class for regular gameObjects, with mesh or empty, Derived from GameObject Class"""
    def onStart( self ) -> None:
        super().onStart()

    def onUpdate( self ) -> None:
        """Executes every frame, issuing draw commands"""
        super().onUpdate()

