from OpenGL.GL import *
from OpenGL.GLU import *

from modules.imageLoader import load_image_pygame as load_image, create_rmo_map
from modules.renderer import Renderer

import os

class Images:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer

        self.images = []
        self.images_paths = []

        self.basepath = f"{self.context.rootdir}\\textures\\"
        self.defaultImage = self.loadOrFindFullPath( f"{self.context.engineAssets}textures\\default.jpg")
        self.defaultRMO = self.loadOrFindFullPath( f"{self.context.engineAssets}textures\\default_rmo.png")
        self.defaultNormal = self.loadOrFindFullPath( f"{self.context.engineAssets}textures\\default_normal.png")
        self.whiteImage = self.loadOrFindFullPath( f"{self.context.engineAssets}textures\\whiteimage.jpg")
        self.blackImage = self.loadOrFindFullPath( f"{self.context.engineAssets}textures\\blackimage.jpg")

        return

    def loadOrFindPhysicalMap( self, roughness_path, metallic_path, ao_path ):
        # load
        texture_id = glGenTextures( 1 ) 
        if not create_rmo_map( roughness_path, metallic_path, ao_path, texture_id ):
            return self.defaultImage

        # todo: hash combined r, m and o path name for "images_paths" lookup table.
        # to prevent loading the same rmo map multiple times
        self.images_paths.append( f"rmomap_placeholder_{texture_id}" )
        self.images.append( texture_id )

        return texture_id

    def loadOrFindFullPath( self, uid : str, flip_x: bool = False, flip_y: bool = True ) -> int:
        """Load or find an image, implement find later"""

        _path = uid

        #default image
        if not os.path.isfile( _path ):
            return self.defaultImage

        # find
        for i, path in enumerate(self.images_paths):
            if _path == path:
                return self.images[i]

        # load
        texture_id = glGenTextures( 1 ) 
        load_image( _path, texture_id, flip_x, flip_y )
        self.images_paths.append( _path )
        self.images.append( texture_id )

        return texture_id

    def bind( self, texture_id : int, texture_index, shader_uniform, shader_index ):
        """Bind texture using OpenGL with image index"""

        glActiveTexture( texture_index )
        glBindTexture( GL_TEXTURE_2D, texture_id )
        glUniform1i(glGetUniformLocation( self.renderer.shader.program, shader_uniform ), shader_index)

