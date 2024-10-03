from OpenGL.GL import *
from OpenGL.GLU import *

from modules.objLoader import ObjLoader
from modules.renderer import Renderer

class Models:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer

        self.num_models = 0
        self.indices = list(range(30))
        self.buffer = list(range(30))
        #self.VAO = glGenVertexArrays(30)

        self.VBO = glGenBuffers(30)
        self.IBO  = glGenBuffers(30)   

        self.basepath = "C:/Github-workspace/EmberEngine/assets/models/"
        return

    def loadOrFind( self, uid : str ) -> int:
        """Load or find an model, implement find later"""
        index = self.num_models

        self.indices[index], self.buffer[index] = ObjLoader.load_model(f"{self.basepath}{uid}")

        self.upload( index )

        self.num_models+=1
        return index

    def upload( self, index : int ) -> None :
        #glBindVertexArray( self.VAO[index] )
        glBindBuffer( GL_ELEMENT_ARRAY_BUFFER, self.VBO[index] )
        glBufferData( GL_ELEMENT_ARRAY_BUFFER, self.buffer[index].nbytes, self.buffer[index], GL_STATIC_DRAW )

        glBindBuffer( GL_ELEMENT_ARRAY_BUFFER, self.IBO[index] )
        glBufferData( GL_ELEMENT_ARRAY_BUFFER, self.indices[index].nbytes, self.indices[index],GL_STATIC_DRAW )

    def bind( self, index : int  ) -> None:
        #glBindVertexArray( self.VAO[index] )
        glBindBuffer( GL_ARRAY_BUFFER, self.VBO[index] )

        # vertex
        glEnableVertexAttribArray( 0 )
        glVertexAttribPointer( 0, 3, GL_FLOAT, GL_FALSE, self.buffer[index].itemsize * 8, ctypes.c_void_p(0) )
       
        # uv
        glEnableVertexAttribArray( 1 )
        glVertexAttribPointer( 1, 2, GL_FLOAT, GL_FALSE, self.buffer[index].itemsize * 8, ctypes.c_void_p(12) )

        # normals
        glEnableVertexAttribArray( 2 )
        glVertexAttribPointer( 2, 3, GL_FLOAT, GL_FALSE, self.buffer[index].itemsize * 8, ctypes.c_void_p(20) )

        #glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.IBO[index] )

    def draw( self, index : int ) -> None:
        glDrawArrays( GL_TRIANGLES, 0, len(self.indices[index]))
        
        #glDrawElements(
        #    GL_TRIANGLES,      # mode
        #    len(self.indices[index]),    #// count
        #    GL_UNSIGNED_SHORT, #  // type
        #    None          #// element array buffer offset
        #)		
        #glDisableVertexAttribArray(0)
        #glDisableVertexAttribArray(1)
        #glDisableVertexAttribArray(1)

        glBindVertexArray(0)  # Optionally unbind VAO
        glBindBuffer( GL_ARRAY_BUFFER, 0)  # Optionally unbind VAO