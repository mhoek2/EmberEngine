class MyScript:
    """Default script template"""
    def onStart( self ) -> None:
        print( f"gameobjects scale: {self.gameObject.scale}")

    def onUpdate( self ) -> None:
        print( f"gameobjects scale: {self.gameObject.scale}")
        pass