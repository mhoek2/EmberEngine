import sys
from pathlib import Path
from typing import List


from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.ARB.bindless_texture import *

from modules.render.image import ImageUpload, upload_image
from modules.render.types import ImageMeta
from modules.context import Context

import traceback

from dataclasses import dataclass, field
import queue

import pygame
import numpy as np
import io

class Images( Context ):
    @dataclass(slots=True)
    class Queue:
        image_index     : int  = field( default=-1 )
        flip_x          : bool = field( default=False )
        flip_y          : bool = field( default=True )
        base            : "Images.ImageUpload" = field( default=None )

    @staticmethod
    def create_white_image( size ):
        white_surface = pygame.Surface(size)
        white_surface.fill((255, 255, 255, 255))
        return white_surface

    @staticmethod
    def create_black_image( size ):
        white_surface = pygame.Surface(size)
        white_surface.fill((0, 0, 0, 255))
        return white_surface

    @staticmethod
    def create_grey_image( size ):
        white_surface = pygame.Surface(size)
        white_surface.fill((127, 127, 127, 255))
        return white_surface

    def image_upload_queue_flush( self ) -> None:
        while not self.upload_queue.empty():
            item = self.upload_queue.get()
            image_index = item.image_index

            texture_id = glGenTextures( 1 ) 

            upload_image( texture_id, item.base )

            # check if texture is valid
            # ..later

            self.images[image_index] = texture_id

            _path = str(item.base.path)
            print(f"load: {_path}")
            self.image_meta[image_index].path       = _path
            self.image_meta[image_index].dimension  = (item.base.width, item.base.height)
            #self.image_meta[image_index].size       = item.base.width * item.base.height * 4
            self.image_meta[image_index].size       = len(item.base.buffer)

            handle = self.make_bindless( image_index, texture_id )
            self.context.renderer.ubo.ubo_materials._dirty = True

    def __init__( self, context ):
        """Setup image buffers that store the GPU texture uid's and paths for fast loading
        Also create the defaul, white, black and PBR textures

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )

        self._num_images = 0

        # lookup table containing GPU texture ids
        self.images = [None] * 300

        # store meta data, eg: path, size
        self.image_meta : List[ImageMeta] = [ImageMeta() for _ in range(300) ]

        # The actual GPU upload is using a queue, this allows for model load threading optimization
        # because the OpenGL context is not shared across threads.
        # this also means, when an image is loaded, it will not be available until the next frame.
        # for that frame, default texture is used.
        self.upload_queue = queue.Queue()

        # bindless texture mapping
        self.texture_to_bindless : dict = {}

        self.defaultImage   = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}default.jpg") )
        # deprecated (12-01-2026)
        # generate physical texture on applictation init, 
        # this allows to change format more easily. 
        # alternative is to use GPU swizzle (overhead)
        #self.defaultRMO     = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}default_rmo_deprecated.png") )
        self.defaultRMO     = self.create_default_physical_image() 
        self.defaultNormal  = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}default_normal.png") )
        self.whiteImage     = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}whiteimage.jpg") )
        self.blackImage     = self.loadOrFindFullPath( Path(f"{self.settings.engine_texture_path}blackimage.jpg") )

    def get_by_path( self, path : Path ):
        for i, meta in enumerate(self.image_meta):
            if str(path) == meta.path:
                return i

        return None

    def tex_to_bindless( self, index ):
        if index in self.texture_to_bindless:
            handle = self.texture_to_bindless[index]

            # todomeh, fix this. init to 0
            return handle if handle is not None else 0
        else:
            self.texture_to_bindless[self.defaultImage]

    def get_gl_texture( self, image_index ):
        """Get the GPU uid of a texture

        :param image_index: the image index point to image list containing the texture uid in GPU memory
        :type image_index: int
        :param: the texture uid in GPU memory
        :rtype: uint32/uintc
        """
        return self.images[image_index] if self.images[image_index] else self.images[self.defaultImage]

    def make_bindless( self, image_index : int, texture_id ):
        """Create a bindless handle for a texture an map it"""
        handle = 0
        #texture_id = self.images[image_index]

        if self.context.renderer.USE_BINDLESS_TEXTURES:
            handle = glGetTextureHandleARB(texture_id)
            glMakeTextureHandleResidentARB(handle)
            #self.bindless_handles.append( handle )

        self.texture_to_bindless[image_index] = handle
        return handle

    def create_default_physical_image( self ) -> int:
        """Create a 256x256 texture where each channel represents a phyisical kind, occlusion, roughness, metallic
        Current map format is ORM (occlusion, roughness, metallic )"""
        size = 256
        image_size = (size, size)

        roughness = Images.create_grey_image( image_size )
        metallic = Images.create_black_image( image_size )
        ambient = Images.create_white_image( image_size )

        combined_image = pygame.Surface(image_size)
        roughness.lock()
        metallic.lock()
        ambient.lock()
        combined_image.lock()

        roughness_array = pygame.surfarray.array3d(roughness).astype(np.float32) / 255.0
        metallic_array = pygame.surfarray.array3d(metallic).astype(np.float32) / 255.0
        ambient_occlusion_array = pygame.surfarray.array3d(ambient).astype(np.float32) / 255.0

        # you may need to transpose based on your orientation.
        combined_array = np.zeros((size, size, 4), dtype=np.float32)

        # RMO
        #combined_array[..., 0] = roughness_array[..., 0]                            # Roughness from R channel
        #combined_array[..., 1] = metallic_array[..., 1]                             # Metallic from G channel
        #combined_array[..., 2] = ambient_occlusion_array[..., 2]                    # AO from B channel

        # ORM
        combined_array[..., 0] = ambient_occlusion_array[..., 2]                    # AO from B channel
        combined_array[..., 1] = roughness_array[..., 0]                            # Roughness from R channel
        combined_array[..., 2] = metallic_array[..., 1]                             # Metallic from G channel

        combined_array[..., 3] = 1.0
        combined_array = np.rot90(combined_array, k=1)

        return self.queue_upload( 
            upload_data = ImageUpload(
                path                = "*physicalmap_default",
                width               = size,
                height              = size,
                buffer              = combined_array.tobytes(),
                _internal_format    = GL_RGBA16F,
                _format             = GL_FLOAT,
                mipmap              = True
            )
        )

    def loadOrFindPhysicalMap( self, roughness_path : Path, metallic_path : Path, ao_path : Path ) -> int:
        """Load/Create/Combine a physical RMO texture.
        Find from cache is not implemented yet.

        :param roughness_path: 
        :type roughness_path: Path
        :param metallic_path: 
        :type metallic_path: Path
        :param ao_path: 
        :type ao_path: Path
        :return: the image index point to image list containing the texture uid in GPU memory
        :rtype: int
        """
        index = self._num_images

        try:
            size = (-1, -1)

            # Load images and get highest dimension
            # TODO: fix missing file issue..
            if roughness_path:
                roughness = pygame.image.load( roughness_path )
                if size < roughness.get_size() : size = roughness.get_size()

            if metallic_path:
                metallic = pygame.image.load( metallic_path )
                if size < metallic.get_size() : size = metallic.get_size()

            if ao_path:
                ambient_occlusion = pygame.image.load( ao_path )
                if size < ambient_occlusion.get_size() : size = ambient_occlusion.get_size()

            if size == (-1, -1):
                raise ValueError("No map found!")

            # fill empty channels
            if not roughness_path:
                roughness = Images.create_grey_image( size )

            if not metallic_path:
                metallic = Images.create_black_image( size )

            if not ao_path:
                ambient_occlusion = Images.create_white_image( size )

            # Ensure all images are the same size
            # todo: should probably auto-scale to highest dimension ..
            if roughness.get_size() != metallic.get_size() or roughness.get_size() != ambient_occlusion.get_size():
                raise ValueError("All images must be the same size!")

            # Get image dimensions
            image_width, image_height = roughness.get_size()

            # Create a new surface to hold combined image data
            combined_image = pygame.Surface((image_width, image_height))

            # Lock surfaces to access pixel data
            roughness.lock()
            metallic.lock()
            ambient_occlusion.lock()
            combined_image.lock()

            roughness_array = pygame.surfarray.array3d(roughness).astype(np.float32) / 255.0
            metallic_array = pygame.surfarray.array3d(metallic).astype(np.float32) / 255.0
            ambient_occlusion_array = pygame.surfarray.array3d(ambient_occlusion).astype(np.float32) / 255.0

            combined_array = np.zeros((image_width, image_height, 4), dtype=np.float32)
            # RMO
            #combined_array[..., 0] = roughness_array[..., 0]                            # Roughness from R channel
            #combined_array[..., 1] = metallic_array[..., 1]                             # Metallic from G channel
            #combined_array[..., 2] = ambient_occlusion_array[..., 2]                    # AO from B channel

            # ORM
            combined_array[..., 0] = ambient_occlusion_array[..., 2]                    # AO from B channel
            combined_array[..., 1] = roughness_array[..., 0]                            # Roughness from R channel
            combined_array[..., 2] = metallic_array[..., 1]                             # Metallic from G channel


            combined_array[..., 3] = 1.0
            combined_array = np.rot90(combined_array, k=1)

            # Unlock surfaces
            roughness.unlock()
            metallic.unlock()
            ambient_occlusion.unlock()
            combined_image.unlock()

            base : ImageUpload = ImageUpload(
                path                = f"rmomap_placeholder_{index}",
                width               = image_width,
                height              = image_height,
                buffer              = combined_array.tobytes(),
                _internal_format    = GL_RGBA16F,
                _format             = GL_FLOAT,
                mipmap              = True
            )

            self.upload_queue.put(Images.Queue(
                image_index     = index,
                base            = base,
            ))

        except Exception as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            self.console.error( e, traceback.format_tb(exc_tb) )

            return self.defaultImage

        self._num_images += 1
        return index

    def queue_upload( self, upload_data : ImageUpload ) -> int:
        index = self._num_images

        self.upload_queue.put(Images.Queue(
            image_index = index,
            base        = upload_data
        ))

        self._num_images += 1
        return index

    def pixelsToImage( self, data, path : Path = None ):
        exists = self.get_by_path( path )
        if path is not None:
            if exists:
                return None, None, None

        byte_stream = io.BytesIO(data)
        base_buffer = pygame.image.load(byte_stream)

        base_buffer = pygame.transform.flip(base_buffer, False, True)
        width, height = base_buffer.get_rect().size
        buffer = pygame.image.tostring(base_buffer, "RGBA")

        return width, height, buffer

    def loadFromPixels( self, width, height, buffer, path : Path = None ):
        """Submit image data to the upload queue, Path is optional"""

        # find
        if path is not None:
            exists = self.get_by_path( path )
            if exists:
                return exists

        return self.queue_upload( 
            upload_data = ImageUpload(
                    path                = path,
                    width               = width,
                    height              = height,
                    buffer              = buffer,
                    _format             = GL_UNSIGNED_BYTE,
                    _internal_format    = GL_RGBA
                )
            )

    def loadOrFindFullPath( self, path : Path, flip_x: bool = False, flip_y: bool = True ) -> int:
        """Load or find existing texture

        :param path: The path to the texture
        :type path: Path
        :return: the image index point to image list containing the texture uid in GPU memory
        :rtype: int
        """

        # not found
        if not path or not path.is_file():
            return self.defaultImage

        # find
        exists = self.get_by_path( path )
        if exists:
            return exists

        # load and queue GPU upload
        base_buffer = pygame.transform.flip( pygame.image.load( path ), flip_x, flip_y )
        width, height = base_buffer.get_rect().size
        buffer = pygame.image.tostring( base_buffer, "RGBA" )

        return self.loadFromPixels( width, height, buffer, path )

    def bind_gl( self, texture_id : int, texture_index, shader_uniform : str, shader_index : int ):
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

    def bind( self, image_index : int, texture_index, shader_uniform : str, shader_index : int ):
        """Bind texture using OpenGL with image index

        :param image_index: the image index point to image list containing the texture uid in GPU memory
        :type image_index: int
        :param texture_index: The texture unit index in GLSL (eg. GL_TEXTURE0-GL_TEXTURE31)
        :type texture_index: uint32/uintc
        :param shader_uniform: The varaible name of the GLSL uniform sampler
        :type shader_uniform: str
        :param shader_index: Represent the number also indicated with 'texture_index'. revisit this?
        :type shader_index: int
        """
        texture_id = self.get_gl_texture(image_index)
        
        glActiveTexture( texture_index )
        glBindTexture( GL_TEXTURE_2D, texture_id )
        glUniform1i(glGetUniformLocation( self.renderer.shader.program, shader_uniform ), shader_index)