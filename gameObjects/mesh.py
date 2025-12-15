from gameObjects.gameObject import GameObject

from OpenGL.GL import *

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
        
        # debug draw collision geometry
        if not self.renderer.game_runtime and self.physic_link is not None:
            _current_shader = self.renderer.shader

            self.renderer.use_shader( self.renderer.color )

            _color = ( 0.83, 0.34, 0.0, 1.0 )
            glUniform4f( self.renderer.shader.uniforms['uColor'],  _color[0],  _color[1], _color[2], 0.7 )

            glEnable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            glLineWidth(5)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)

            _collision_model = self.physic_link.collision.model or self.context.models.default_cube

            self.models.draw(
                _collision_model,
                self.physic_link.collision.transform._getModelMatrix()
            )

            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glLineWidth(1)

            if _current_shader:
                self.renderer.use_shader( _current_shader )

        # render the model geometry
        if self.model != -1 and is_visible:
            self.models.draw( self.model, self.transform._getModelMatrix() ) 

