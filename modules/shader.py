import math
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

from modules.files import FileHandler
import textwrap

class Shader:
    def __init__( self, context, uid : str ):
        self.context = context

        # fix path to use root..
        self.basepath = f"{self.context.rootdir}\\shaders\\"
        vert_shader = textwrap.dedent(FileHandler(f"{self.basepath}{uid}.vert").getContent())
        frag_shader = textwrap.dedent(FileHandler(f"{self.basepath}{uid}.frag").getContent())

        self.program = self.load_program( vert_shader, frag_shader )
        return

    def printOpenGLError( self ):
        err = glGetError() # pylint: disable=E1111
        if (err != GL_NO_ERROR):
            print('GLERROR: ', gluErrorString(err)) # pylint: disable=E1101


    def load_program( self, in_vert, in_frag ):
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

    def load_shader( self, shader_type, source ):
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