from OpenGL.GL import *
from OpenGL.GLU import *

from modules.imageLoader import load_image_pygame as load_image
from modules.renderer import Renderer

import os

class Images:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer

        self.images = glGenTextures(30)
        self.images_paths = []

        self._images_size = 0;

        self.basepath = "C:/Github-workspace/EmberEngine/assets/textures/"
        self.defaultImage = self.loadOrFindFullPath( f"{self.basepath}default.jpg")
        return

    def loadOrFindFullPath( self, uid : str ) -> int:
        """Load or find an image, implement find later"""

        index = self._images_size
        _path = uid

        #default image
        if not os.path.isfile( _path ):
            return self.defaultImage

        # find
        for i, path in enumerate(self.images_paths):
            if _path == path:
                return i

        # load
        
        load_image( _path, self.images[index] )
        self.images_paths.append( _path )

        self._images_size += 1
        return index

    def loadOrFind( self, uid : str ) -> int:
        """Load or find an image, implement find later"""

        index = self._images_size

        _path = f"{self.basepath}{uid}"

        #default image
        if not os.path.isfile( _path ):
            return self.defaultImage

        # find
        for i, path in enumerate(self.images_paths):
            if _path == path:
                return i

        # load
        load_image( _path, self.images[index] )
        self.images_paths.append( _path )

        self._images_size += 1
        return index

    def bind( self, index : int, texture_index, shader_uniform, shader_index ):
        """Bind texture using OpenGL with image index"""

        glActiveTexture( texture_index )
        glBindTexture( GL_TEXTURE_2D, self.images[index] )
        glUniform1i(glGetUniformLocation( self.renderer.shader.program, shader_uniform ), shader_index)

