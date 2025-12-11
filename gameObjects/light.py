from gameObjects.gameObject import GameObject
import enum

class Light( GameObject ):
    # IntFlag is bitwise  (1 << index)
    # IntEnum is seqential
    class Type_(enum.IntEnum):
        direct  = 0             # (= 0)
        spot    = enum.auto()   # (= 1)
        area    = enum.auto()   # (= 2)

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

        self.is_sun = False

        # not implemented
        #self.light_type = kwargs.get('light_type', 1.0)
        self.light_type     : Light.Type_ = self.Type_.direct
        self.light_color    : list[float] = [ 0.98, 1.0, 0.69 ]
        self.radius         : float = 12.0
        self.intensity      : float = 1.0

    def onStart( self ) -> None:
        """Executes whenever the object is added to scene"""
        super().onStart()

        if self.model_file:
            self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        """Executes every frame, issuing draw commands"""

        if self._dirty and self.scene.isSun( self.uuid ):
            self.context.skybox.procedural_cubemap_update = True

        super().onUpdate()

        if self.model != -1 and self.visible:
            self.models.draw( self.model, self.transform._getModelMatrix() )     