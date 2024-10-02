from OpenGL.GL import *
from OpenGL.GLU import *

from modules.imageLoader import load_image_pygame as load_image
from modules.renderer import Renderer

class Images:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer

        self.images = glGenTextures(30)
        self._images_size = 0;

        self.basepath = "C:/Github-workspace/EmberEngine/assets/textures/"
        return

    def loadOrFind( self, uid : str ) -> int:
        """Load or find an image, implement find later"""

        index = self._images_size
        load_image( f"{self.basepath}{uid}", self.images[index] )

        self._images_size += 1
        return index

    def bind( self, index : int ):
        """Bind texture using OpenGL with image index"""
        glBindTexture(GL_TEXTURE_2D, self.images[index] )