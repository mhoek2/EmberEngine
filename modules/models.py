from OpenGL.GL import *
from OpenGL.GLU import *

from modules.objLoader import ObjLoader
from modules.renderer import Renderer

class Models:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer

        self.size = 0
        self.indices = list(range(30))
        self.buffer = list(range(30))
        self.VAO = glGenVertexArrays(30)
        self.VBO = glGenBuffers(30)

        self.basepath = "C:/Github-workspace/EmberEngine/assets/models/"
        return

    def loadOrFind( self, uid : str ) -> int:
        """Load or find an model, implement find later"""
        index = self.size
        self.indices[index], self.buffer[index] = ObjLoader.load_model("C:/Users/Admin/Desktop/example2/meshes/cube.obj")

        self.bind(index)

        self.size+=1
        return index
        #load_image( f"{self.basepath}{uid}", self.images[index] )

    def bind( self, index : int ) -> None :
        glBindVertexArray( self.VAO[index] )
        glBindBuffer( GL_ARRAY_BUFFER, self.VBO[index] )
        glBufferData( GL_ARRAY_BUFFER, self.buffer[index].nbytes, self.buffer[index], GL_STATIC_DRAW )

        #glVertexAttribPointer( self.renderer.aVertex, 3, GL_FLOAT, GL_FALSE, self.buffer[index].itemsize * 8, ctypes.c_void_p(0))
        #glVertexAttribPointer( self.renderer.aTexCoord, 2, GL_FLOAT, GL_FALSE, self.buffer[index].itemsize * 8, ctypes.c_void_p(12))
        #glVertexAttribPointer( self.renderer.aNormal, 3, GL_FLOAT, GL_FALSE, self.buffer[index].itemsize * 8, ctypes.c_void_p(20))
        #glBindVertexArray(0)

    def bind2( self, index : int  ) -> None:
        glBindVertexArray( self.VAO[index] )
        glBindBuffer( GL_ARRAY_BUFFER, self.VBO[index] )
        glUseProgram( self.renderer.shader.program )

        glEnableVertexAttribArray( self.renderer.aVertex )
        glVertexAttribPointer( self.renderer.aVertex, 3, GL_FLOAT, GL_FALSE, self.buffer[index].itemsize * 8, ctypes.c_void_p(0))
        glEnableVertexAttribArray( self.renderer.aTexCoord )
        glVertexAttribPointer( self.renderer.aTexCoord, 2, GL_FLOAT, GL_FALSE, self.buffer[index].itemsize * 8, ctypes.c_void_p(12))
        glEnableVertexAttribArray( self.renderer.aNormal )
        glVertexAttribPointer( self.renderer.aNormal, 3, GL_FLOAT, GL_FALSE, self.buffer[index].itemsize * 8, ctypes.c_void_p(20))

    def drawArrays( self, index : int ) -> None:
        glDrawArrays( GL_TRIANGLES, 0, len(self.indices[index]))
        glBindVertexArray(0)  # Optionally unbind VAO
        glBindBuffer( GL_ARRAY_BUFFER, 0)  # Optionally unbind VAO