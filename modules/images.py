from OpenGL.GL import *
from OpenGL.GLU import *

from modules.imageLoader import load_image_pygame as load_image, create_rmo_map
from modules.renderer import Renderer

import os

class Images:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer

        self.images = glGenTextures(300)
        self.images_paths = []

        self._num_images = 0;

        self.basepath = f"{self.context.rootdir}\\textures\\"
        self.defaultImage = self.loadOrFindFullPath( f"{self.context.engineAssets}textures\\default.jpg")
        
        return

    def loadOrFindPhysicalMap( self, roughness_path, metallic_path, ao_path ):
        index = self._num_images

        # load
        if not create_rmo_map( roughness_path, metallic_path, ao_path, self.images[index] ):
            return self.defaultImage

        self._num_images += 1
        return index

    def loadOrFindFullPath( self, uid : str ) -> int:
        """Load or find an image, implement find later"""

        index = self._num_images
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

        self._num_images += 1
        return index

    def bind( self, index : int, texture_index, shader_uniform, shader_index ):
        """Bind texture using OpenGL with image index"""

        glActiveTexture( texture_index )
        glBindTexture( GL_TEXTURE_2D, self.images[index] )
        glUniform1i(glGetUniformLocation( self.renderer.shader.program, shader_uniform ), shader_index)

