from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

import imgui

from modules.renderer import Renderer

class ImGui:
    def __init__( self, context ):
        self.context = context
        self.renderer   : Renderer = context.renderer
        self.io = imgui.get_io()

        self.drawWireframe = False

    # https://github.com/pyimgui/pyimgui/blob/9adcc0511c5ce869c39ced7a2b423aa641f3e7c6/doc/examples/integrations_glfw3_docking.py#L10
    def docking_space( self, name: str ):
        flags = (imgui.WINDOW_MENU_BAR 
        | imgui.WINDOW_NO_DOCKING 
        # | imgui.WINDOW_NO_BACKGROUND
        | imgui.WINDOW_NO_TITLE_BAR
        | imgui.WINDOW_NO_COLLAPSE
        | imgui.WINDOW_NO_RESIZE
        | imgui.WINDOW_NO_MOVE
        | imgui.WINDOW_NO_BRING_TO_FRONT_ON_FOCUS
        | imgui.WINDOW_NO_NAV_FOCUS
        )

        viewport = imgui.get_main_viewport()
        x, y = viewport.pos
        w, h = viewport.size
        imgui.set_next_window_position(x, y)
        imgui.set_next_window_size(w, h)
        # imgui.set_next_window_viewport(viewport.id)
        imgui.push_style_var(imgui.STYLE_WINDOW_BORDERSIZE, 0.0)
        imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 0.0)

        # When using ImGuiDockNodeFlags_PassthruCentralNode, DockSpace() will render our background and handle the pass-thru hole, so we ask Begin() to not render a background.
        # local window_flags = self.window_flags
        # if bit.band(self.dockspace_flags, ) ~= 0 then
        #     window_flags = bit.bor(window_flags, const.ImGuiWindowFlags_.NoBackground)
        # end

        # Important: note that we proceed even if Begin() returns false (aka window is collapsed).
        # This is because we want to keep our DockSpace() active. If a DockSpace() is inactive,
        # all active windows docked into it will lose their parent and become undocked.
        # We cannot preserve the docking relationship between an active window and an inactive docking, otherwise
        # any change of dockspace/settings would lead to windows being stuck in limbo and never being visible.
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (0, 0))
        imgui.begin(name, None, flags)
        imgui.pop_style_var()
        imgui.pop_style_var(2)

        # DockSpace
        dockspace_id = imgui.get_id(name)
        imgui.dockspace(dockspace_id, (0, 0), imgui.DOCKNODE_PASSTHRU_CENTRAL_NODE)

        imgui.end()

    def draw_viewport( self ) -> None:
        imgui.set_next_window_size( 915, 640 )
        imgui.begin( "Viewport" )

        glBindTexture(GL_TEXTURE_2D, self.renderer.main_fbo["texture"])
        imgui.image( self.renderer.main_fbo["texture"], 900, 600, uv0=(0, 1), uv1=(1, 0) )

        imgui.end()

    def render( self ):
        # imgui draw
        
        # global
        frame_time = 1000.0 / self.io.framerate
        fps = self.io.framerate
        state = "enabled" if not self.renderer.ImGuiInput else "disabled"

        self.docking_space('docking_space')
        
        # windows
        self.draw_viewport()

        imgui.begin( "Window" )
        imgui.text( f"[F1] Input { state }" );
        imgui.text(f"{frame_time:.3f} ms/frame ({fps:.1f} FPS)")

        changed, self.drawWireframe = imgui.checkbox( "Wireframe", self.drawWireframe )

        if imgui.button("Click me!"):
            print("Button pressed!")


        imgui.end()