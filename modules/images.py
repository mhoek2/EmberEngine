from pathlib import Path
from typing import List


from OpenGL.GL import *
from OpenGL.GLU import *

from modules.imageLoader import load_image_pygame as load_image, create_rmo_map
from modules.context import Context

class Images( Context ):
    def __init__( self, context ):
        """Setup image buffers that store the GPU texture uid's and paths for fast loading
        Also create the defaul, white, black and PBR textures

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )

        self.images = []
        self.images_paths : List[str] = []

        self.defaultImage   = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}default.jpg") )
        self.defaultRMO     = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}default_rmo.png") )
        self.defaultNormal  = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}default_normal.png") )
        self.whiteImage     = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}whiteimage.jpg") )
        self.blackImage     = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}blackimage.jpg") )

    def loadOrFindPhysicalMap( self, roughness_path : Path, metallic_path : Path, ao_path : Path ):
        """Load/Create/Combine a physical RMO texture.
        Find from cache is not implemented yet.

        :param roughness_path: 
        :type roughness_path: Path
        :param metallic_path: 
        :type metallic_path: Path
        :param ao_path: 
        :type ao_path: Path
        :return: the texture uid in GPU memory
        :rtype: uint32/uintc
        """
        texture_id = glGenTextures( 1 ) 
        if not create_rmo_map( roughness_path, metallic_path, ao_path, texture_id ):
            return self.defaultImage

        # todo: hash combined r, m and o path name for "images_paths" lookup table.
        # to prevent loading the same rmo map multiple times
        self.images_paths.append( f"rmomap_placeholder_{texture_id}" )
        self.images.append( texture_id )

        return texture_id

    def loadOrFindFullPath( self, path : Path, flip_x: bool = False, flip_y: bool = True ):
        """Load or find existing texture

        :param path: The path to the texture
        :type path: Path
        :return: the texture uid in GPU memory
        :rtype: uint32/uintc
        """
        # not found
        if not path or not path.is_file():
            return self.defaultImage

        # find
        for i, _path in enumerate(self.images_paths):
            if str(path) == _path:
                return self.images[i]

        # load
        texture_id = glGenTextures( 1 ) 
        load_image( path, texture_id, flip_x, flip_y )
        self.images_paths.append( str(path) )
        self.images.append( texture_id )

        return texture_id

    def bind( self, texture_id, texture_index, shader_uniform : str, shader_index : int ):
        """Bind texture using OpenGL with image index

        :param texture_id: the texture uid in GPU memory
        :type texture_id: uint32/uintc
        :param texture_index: The texture unit index in GLSL (eg. GL_TEXTURE0-GL_TEXTURE31)
        :type texture_index: uint32/uintc
        :param shader_uniform: The varaible name of the GLSL uniform sampler
        :type shader_uniform: str
        :param shader_index: Represent the number also indicated with 'texture_index'. revisit this?
        :type shader_index: int
        """
        glActiveTexture( texture_index )
        glBindTexture( GL_TEXTURE_2D, texture_id )
        glUniform1i(glGetUniformLocation( self.renderer.shader.program, shader_uniform ), shader_index)