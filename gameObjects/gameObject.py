import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np

class GameObject:
    def __init__( self, context, translate=( 0.0, 0.0, 0.0 ), rotation=( 0.0, 0.0, 0.0 ), scale=( 1.0, 1.0, 1.0 ) ) -> None:
        self.context = context
        self.renderer = context.renderer
        self.textures = context.textures
        
        # https://github.com/adamlwgriffiths/Pyrr
        self.translate = translate
        self.rotation = rotation
        self.scale = scale

        self.onStart()
        return

    def onStart( self ) -> None:
        return

    def onUpdate( self ) -> None:
        return
    