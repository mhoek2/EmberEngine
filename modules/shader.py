import math
import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import textwrap

class Shader:
    def __init__( self ):
        self.vert_tmpl = textwrap.dedent("""\
            uniform mat4 uMMatrix;
            uniform mat4 uVMatrix;
            uniform mat4 uPMatrix;
       
            attribute vec3 aVertex;
            attribute vec3 aNormal;
            attribute vec2 aTexCoord;
    
            varying vec2 vTexCoord;
    
            void main(){
                vTexCoord = aTexCoord;
                // Make GL think we are actually using the normal
                aNormal;
                gl_Position = (uPMatrix * uVMatrix * uMMatrix) * vec4(aVertex, 1.0);
            }
        """)

        self.frag_tmpl = textwrap.dedent("""\
            uniform sampler2D sTexture;
            varying vec2 vTexCoord;

            void main(){
                //gl_FragColor = texture2D(sTexture, vTexCoord);
                gl_FragColor = vec4(1.0);
            }
        """)  

        self.program = self.load_program( self.vert_tmpl, 
                                          self.frag_tmpl 
                                        )
        return

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

        glLinkProgram( program )

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