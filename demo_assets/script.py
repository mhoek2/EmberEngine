import pygame

class MyScript:
    """Default script template"""
    def onStart( self ) -> None:
        self.camera = self.scene.getCamera()
        pass

    def onUpdate( self ) -> None:
        keypress = self.key.get_pressed()
        velocity = 0.5
        
        if keypress[pygame.K_LCTRL] or keypress[pygame.K_RCTRL]:
            velocity *= 10

        move = self.renderer.deltaTime * velocity

        if keypress[pygame.K_w]:
            self.transform.local_position[2] += move
            self.camera.transform.local_position[2] += move
        if keypress[pygame.K_s]:
            self.transform.local_position[2] -= move
            self.camera.transform.local_position[2] -= move
        if keypress[pygame.K_d]:
            self.transform.local_position[0] -= move
            self.camera.transform.local_position[0] -= move
        if keypress[pygame.K_a]:
            self.transform.local_position[0] += move
            self.camera.transform.local_position[0] += move