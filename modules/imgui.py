from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

import imgui

from modules.renderer import Renderer

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.sun import Sun

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

    def draw_menu_bar( self, frame_time, fps ) -> None:
        if imgui.begin_main_menu_bar():

            viewport = imgui.get_main_viewport()
            x, y = viewport.pos
            w, h = viewport.size  

            if imgui.begin_menu("File", True):

                clicked_quit, selected_quit = imgui.menu_item(
                    "Quit", 'Cmd+Q', False, True
                )

                if clicked_quit:
                    self.renderer.running = False

                imgui.end_menu()

            imgui.same_line( w - 400.0 )
            state = "enabled" if not self.renderer.ImGuiInput else "disabled"
            imgui.text( f"[F1] Input { state }" );

            imgui.same_line( w - 200.0 )
            imgui.text( f"{frame_time:.3f} ms/frame ({fps:.1f} FPS)" )

            imgui.end_main_menu_bar()

    def draw_viewport( self ) -> None:
        imgui.set_next_window_size( 915, 640 )
        imgui.begin( "Viewport" )

        glBindTexture(GL_TEXTURE_2D, self.renderer.main_fbo["texture"])
        imgui.image( self.renderer.main_fbo["texture"], 900, 600, uv0=(0, 1), uv1=(1, 0) )

        imgui.end()

    def draw_hierarchy( self ) -> None:
        imgui.begin( "Hierarchy" )

        for gameObject in self.context.gameObjects:
            if isinstance( gameObject, GameObject ):     # link class name
                imgui.text( f"{ gameObject.name }" );

        imgui.end()
        return

    def draw_assets( self ) -> None:
        imgui.begin( "Assets" )

        for model_path in self.context.modelAssets:
            if imgui.button( model_path ):
                self.context.addGameObject( 
                        Mesh( self.context,
                        model_file  = model_path,
                        #material    = self.context.defaultMaterial,
                        translate   = [ 0, 0, 0 ],
                        scale       = [ 1, 1, 1 ],
                        rotation    = [ 0.0, 0.0, 0.0 ]
            ) )

        imgui.end()
        return

    def draw_settings( self ) -> None:
        imgui.begin( "Settings" )
        changed, self.drawWireframe = imgui.checkbox( "Wireframe", self.drawWireframe )
        imgui.end()
        return


    def render( self ):
        # imgui draw
        
        # global
        frame_time = 1000.0 / self.io.framerate
        fps = self.io.framerate

        self.docking_space('docking_space')
        
        self.draw_menu_bar( frame_time, fps )

        # windows
        self.draw_viewport()
        self.draw_assets()
        self.draw_hierarchy()
        self.draw_settings()

        #if imgui.button("Click me!"):
        #    print("Button pressed!")
