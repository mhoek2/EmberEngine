import pygame

class MyScript:
    """Default script template"""
    def onStart( self ) -> None:
        self.camera = self.context.gameObjects[self.context.camera_object]

        pass

    def onUpdate( self ) -> None:
        keypress = self.key.get_pressed()
        velocity = 0.5
        
        #time = velocity / 0
        asasas
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