from OpenGL.GL import *
from OpenGL.GLU import *

from modules.imageLoader import load_cubemap_pygame as load_cubemap
from modules.renderer import Renderer

class Cubemap:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer

        self.cubemap = glGenTextures(30)
        self._num_cubemaps = 0;

        self.basepath = "C:/Github-workspace/EmberEngine/assets/cubemaps/"
        return

    def loadOrFind( self, uid : str ) -> int:
        """Load or find an image, implement find later"""

        index = self._num_cubemaps
        load_cubemap( f"{self.basepath}{uid}", ".jpg", self.cubemap[index] )

        self._num_cubemaps += 1
        return index

    def bind( self, index : int, texture_index, shader_uniform, shader_index ):
        """Bind texture using OpenGL with image index"""
        
        glActiveTexture( texture_index )
        glBindTexture( GL_TEXTURE_CUBE_MAP, self.cubemap[index] )
        glUniform1i(glGetUniformLocation( self.renderer.shader.program, shader_uniform ), shader_index)

