from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

import imgui

from modules.renderer import Renderer

class ImGui:
    def __init__( self, context ):
        self.context = context
        self.renderer   : Renderer = context.renderer
        self.io = imgui.get_io()

    def draw_viewport( self ) -> None:
        imgui.set_next_window_size( 600, 440 )
        imgui.begin( "Viewport" )
        glBindTexture(GL_TEXTURE_2D, self.renderer.main_fbo["texture"])
        imgui.image( self.renderer.main_fbo["texture"], 600, 400 )
        imgui.end()

    def render( self ):
        # imgui draw
        
        # global
        frame_time = 1000.0 / self.io.framerate
        fps = self.io.framerate
        state = "enabled" if not self.renderer.ImGuiInput else "disabled"

        # windows
        self.draw_viewport()

        imgui.begin( "Window" )
        imgui.text( f"[F1] Input { state }" );
        imgui.text(f"{frame_time:.3f} ms/frame ({fps:.1f} FPS)")

        if imgui.button("Click me!"):
            print("Button pressed!")
        imgui.end()

