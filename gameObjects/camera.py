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

        self._fov    : float = 45.0
        self._near   : float = 0.1
        self._far    : float = 1000.0

    def update_renderer_camera( self ):
        """If this camera is the current active one, update the projection matrix"""
        if self.context.camera.camera != self:
            return

        self.context.camera.camera = self

    @property
    def fov( self ) -> float:
        """Get the 'field-of-view' parameter"""
        return self._fov

    @fov.setter
    def fov( self, data ) -> None:
        """Set the 'field-of-view' parameter and update projection matrix if camera is current"""
        self._fov = data
        self.update_renderer_camera()

    @property
    def near( self ) -> float:
        """Get the 'near' parameter"""
        return self._near

    @near.setter
    def near( self, data ) -> None:
        """Set the 'near' parameter and update projection matrix if camera is current"""
        self._near = data
        self.update_renderer_camera()

    @property
    def far( self ) -> float:
        """Get the 'far' parameter"""
        return self._far

    @far.setter
    def far( self, data ) -> None:
        """Set the 'far' parameter and update projection matrix if camera is current"""
        self._far = data
        self.update_renderer_camera()

    def onStart( self ) -> None:
        """Executes whenever the object is added to scene"""
        super().onStart()

        self.model = self.models.loadOrFind( self.model_file, self.material )

    def onUpdate( self ) -> None:
        """Executes every frame, issuing draw commands"""
        super().onUpdate()

        if not self.renderer.game_runtime:
            self.models.draw( self.model, self.transform._getModelMatrix() )   
