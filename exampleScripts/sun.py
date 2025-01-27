import pygame
import math

class Sun:
    """Default script template"""
    def onStart( self ) -> None:
        self.angle          = 1.0
        self.anim_speed     = 2.0
        self.anim_radius    = 8.0   

    def onUpdate( self ) -> None:
        keypress = self.key.get_pressed()

        if keypress[pygame.K_o]:
            self.angle += self.renderer.deltaTime * self.anim_speed 

            self.translate[1] = self.anim_radius * math.cos( self.angle )  # Update x position
            self.translate[2] = self.anim_radius * math.sin( self.angle )