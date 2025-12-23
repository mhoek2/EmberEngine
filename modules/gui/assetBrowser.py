from typing import TYPE_CHECKING

from modules.context import Context

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.camera import Camera
from gameObjects.skybox import Skybox

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

from pathlib import Path
import textwrap

class AssetBrowser( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper

        self._file_browser_dir = self.get_rootpath()
        self._icon_dim = imgui.ImVec2(75.0, 75.0)  

    def open_file( self, path ) -> None:
        # model
        if path.suffix in self.settings.MODEL_EXTENSION:
            game_object_name = path.name.replace(path.suffix, "")
            self.context.world.addGameObject( 
                    Mesh( self.context,
                    name        = game_object_name,
                    model_file  = str( path ),
                    translate   = [ 0, 0, 0 ],
                    scale       = [ 1, 1, 1 ],
                    rotation    = [ 0.0, 0.0, 0.0 ]
            ) )

        # scene
        if path.suffix == self.settings.SCENE_EXTENSION:
            self.scene.clearEditorScene()
            self.scene.loadScene( path.stem )

        # script
        if path.suffix == self.settings.SCRIPT_EXTENSION:
            self.gui.text_editor.open_file( path )

    def get_rootpath( self ) -> Path:
        return Path( self.settings.assets ).resolve()

    def get_icon( self, path ) -> imgui.ImTextureRef:
        _icons = self.gui.icons

        icon = _icons['.unknown']

        if path.is_file() and path.suffix in _icons:
            icon = _icons[path.suffix]

        if path.is_dir() and ".folder" in _icons:
            icon = _icons['.folder']

        return imgui.ImTextureRef( icon )

    def set_path( self, path ) -> None:
        self._file_browser_dir = path

    def back( self ) -> None:
        path = self._file_browser_dir.parent
        self.set_path( path )

    def render_item( self, path ):
        imgui.push_style_color(imgui.Col_.button,          imgui.ImVec4(1.0, 1.0, 1.0, 0.0) ) 
        imgui.push_style_color(imgui.Col_.button_hovered,  imgui.ImVec4(1.0, 1.0, 1.0, 0.1) ) 
        imgui.push_style_color(imgui.Col_.button_active,   imgui.ImVec4(1.0, 1.0, 1.0, 0.2) ) 
               
        if imgui.image_button( f"file##{path}", self.get_icon( path ), self._icon_dim, imgui.ImVec2(0,0)):
            pass

        if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
            if path.is_file():
                self.open_file( path )

            elif path.is_dir():
                self.set_path( path )
        
        # dnd: source
        if imgui.begin_drag_drop_source(imgui.DragDropFlags_.none):
            self.gui.dnd_payload.set_payload(
                self.gui.dnd_payload.Type_.asset,
                1001,
                path
            )

            imgui.text(f"{path.name}")
            imgui.end_drag_drop_source()

        hovered : bool = imgui.is_item_hovered()

        draw_list = imgui.get_window_draw_list()  # Get the draw list for the current window
        button_size = imgui.get_item_rect_size()
        button_pos = imgui.get_item_rect_max()
        #window_pos = imgui.get_window_position()

        # Get path name and text wrap centered
        path_name = textwrap.fill( str(path.name), width=10 )
        text_size = imgui.calc_text_size( path_name )
        text_pos = imgui.ImVec2((button_pos.x - button_size.x) + (button_size.x - text_size.x) * 0.5, button_pos.y)

        alpha = 1.0 if hovered else 0.7
        text_color = imgui.color_convert_float4_to_u32((1.0, 1.0, 1.0, alpha))

        draw_list.add_text( text_pos, text_color, path_name )

        imgui.pop_style_color(3)

    def render( self ) -> None:
        imgui.begin( "Project Assets" )

        imgui.text( str(self._file_browser_dir) )

        if self._file_browser_dir != self.get_rootpath():
            if imgui.button( "Page up ^" ):
                self.back()

        if any( self._file_browser_dir.glob("*") ):
            row_width = 0
            for i, path in enumerate(self._file_browser_dir.glob("*")):
                imgui.push_id( str(path.name) )

                # wrapping
                if i > 0 and ( row_width + self._icon_dim.x ) < imgui.get_window_size().x:
                    imgui.same_line()
                elif i > 0:
                    row_width = 0
                    imgui.dummy( imgui.ImVec2(0, 35) )


                row_width += (self._icon_dim.x + 18.0)
                
                self.render_item( path )

                imgui.pop_id()

        imgui.dummy( imgui.ImVec2(0, 50) )
        imgui.end()  