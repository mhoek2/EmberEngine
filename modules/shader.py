from typing import TYPE_CHECKING

import math
from OpenGL.constant import IntConstant
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

from modules.settings import Settings
from modules.files import FileHandler

import textwrap

if TYPE_CHECKING:
    from main import EmberEngine

class Shader:
    def __init__( self, context, uid : str ):
        """Load and parse GLSL shaders from .vert and .frag files
        
        :param context: This is the main context of the application
        :type context: EmberEngine
        :param uid: The unique idenifier of the shader being initialized
        :type uid: str
        """
        self.context    : 'EmberEngine' = context
        self.settings   : Settings = context.settings

        # fix path to use root..
        basepath = self.settings.shader_path
        vert_shader = textwrap.dedent(FileHandler(f"{basepath}{uid}.vert").getContent())
        frag_shader = textwrap.dedent(FileHandler(f"{basepath}{uid}.frag").getContent())

        self.program = self.load_program( vert_shader, frag_shader )
        
        self.uniforms = {}
        self.parse_uniforms( vert_shader )
        self.parse_uniforms( frag_shader )

        self.bind_uniforms()
        return

    def printOpenGLError( self ):
        """Print any raised errors during GLSL parsing"""
        err = glGetError() # pylint: disable=E1111
        if (err != GL_NO_ERROR):
            print('GLERROR: ', gluErrorString(err)) # pylint: disable=E1101

    def bind_uniforms( self ) -> None:
        """Bind the found uniforms to the this shader program"""
        for uniform in self.uniforms:
            self.uniforms[uniform] = glGetUniformLocation( self.program, uniform )

    def parse_uniforms( self, shader : str ) -> None:
        """Dynamicly find and parse uniforms required by the shader
        
        :param shader: The content if a GLSL shader as string
        :type shader: str
        """
        for line in shader.split('\n'):
            if not line.startswith('uniform'):
                continue

            uniform = line.removeprefix('uniform').strip().split(' ')
            _data_type = uniform[0]
            _keyword = uniform[-1].replace(';', '')

            if _keyword not in self.uniforms:
                self.uniforms[_keyword] = False

    def load_program( self, in_vert : str, in_frag : str ) -> int:
        """Build and create the shader program from .vert and .frag shader
        
        :param in_vert: The content of a vertex shader
        :type in_vert: str
        :param in_vert: The content of a fragment shader
        :type in_vert: str
        :return: The index to a valid shader program in GPU memory
        :rtype: int
        """
        vert = self.load_shader( GL_VERTEX_SHADER, in_vert )
        if vert == 0:
            return 0

        frag = self.load_shader( GL_FRAGMENT_SHADER, in_frag )
        if frag == 0:
            return 0

        program = glCreateProgram()

        if program == 0:
            return 0

        glAttachShader( program, vert )
        glAttachShader( program, frag )
        self.printOpenGLError()

        glLinkProgram( program )

        if(GL_TRUE!=glGetProgramiv(program, GL_LINK_STATUS)):
            err =  glGetShaderInfoLog(frag) 
            raise Exception(err)          
        self.printOpenGLError()
        if glGetProgramiv( program, GL_LINK_STATUS, None ) == GL_FALSE:
            glDeleteProgram( program )
            return 0

        return program

    def load_shader( self, shader_type : IntConstant, source : str ):
        """Compile shader from string
        
        :param shader_type: The type of the shader: GL_VERTEX_SHADER or GL_FRAGMENT_SHADER
        :type shader_type:  OpenGL.constant.IntConstant
        :param source: The content of a shader file
        :type source: str
        """
        shader = glCreateShader( shader_type )

        if shader == 0:
            return 0

        glShaderSource(shader, source)
        glCompileShader(shader)

        if glGetShaderiv( shader, GL_COMPILE_STATUS, None) == GL_FALSE:
            info_log = glGetShaderInfoLog( shader )
            print( info_log )
            glDeleteProgram( shader )
            return 0

        return shader