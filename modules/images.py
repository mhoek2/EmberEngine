from OpenGL.GL import *
from OpenGL.GLU import *

from modules.imageLoader import load_image_pygame as load_image

class Images:
    def __init__( self ):
        self.images = glGenTextures(30)
        self._images_size = 0;

        self.basepath = "C:/Github-workspace/EmberEngine/assets/textures/"
        return

    def loadOrFind( self, uid : str ) -> int:
        # add find later

        index = self._images_size
        load_image( f"{self.basepath}{uid}", self.images[index] )

        self._images_size += 1
        return index

    def bind( self, index : int ):
        glBindTexture(GL_TEXTURE_2D, self.images[index] )