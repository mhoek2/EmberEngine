import pygame

class MyScript:
    value : int = export(10)

    """Default script template"""
    def onStart( self ) -> None:
        self.camera = self.scene.getCamera()

    def onUpdate( self ) -> None:
        keypress = self.key.get_pressed()
        velocity = 0.5
        
        if keypress[pygame.K_LCTRL] or keypress[pygame.K_RCTRL]:
            velocity *= 10

        move = self.renderer.deltaTime * velocity

        if keypress[pygame.K_w]:
            self.translate[2] += move
            self.camera.translate[2] += move
        if keypress[pygame.K_s]:
            self.translate[2] -= move
            self.camera.translate[2] -= move
        if keypress[pygame.K_d]:
            self.translate[0] -= move
            self.camera.translate[0] -= move
        if keypress[pygame.K_a]:
            self.translate[0] += move
            self.camera.translate[0] += move