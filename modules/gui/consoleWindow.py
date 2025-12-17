from typing import TYPE_CHECKING

from modules.context import Context
from modules.console import Console

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

class ConsoleWindow( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper

    def render_entry( self, i, entry : Console.Entry ):
        imgui.push_id( f"exception_{i}" )
   
        _line_height = 17
        _region = imgui.get_content_region_avail()
        _color = self.console.get_entry_color(entry)

        # header background
        draw_list = imgui.get_window_draw_list() 
        p_min = imgui.get_cursor_screen_pos()
        p_max = imgui.ImVec2( p_min.x + _region.x, p_min.y + _line_height)
        color = imgui.color_convert_float4_to_u32(imgui.ImVec4(_color[0], _color[1], _color[2], 0.2))
        draw_list.add_rect_filled(p_min, p_max, color)
        
        # header hover background
        imgui.push_style_color(imgui.Col_.header_hovered, imgui.ImVec4(_color[0], _color[1], _color[2], 0.4) ) 

        _n_lines : int = entry["_n_lines"]

        tree_flags = imgui.TreeNodeFlags_.none

        if _n_lines == 0:
            tree_flags |= imgui.TreeNodeFlags_.leaf # remove flag

        match entry["type_id"]:
            case self.console.Type_.error   : _icon = f"{fa.ICON_FA_EXPLOSION} "
            case self.console.Type_.warning : _icon = f"{fa.ICON_FA_TRIANGLE_EXCLAMATION} "
            case _                          : _icon = ""
                
        if imgui.tree_node_ex( f"{_icon}{ entry['message'] }", tree_flags ):
            # content background
            _h_cor_bias = 4 # imgui.STYLE_ITEM_SPACING
            p_min = imgui.ImVec2(p_min.x, p_max.y)
            _height = (_line_height * entry["_n_lines"]) - _h_cor_bias
            p_max = imgui.ImVec2(p_max.x, p_min.y + _height)
            color = imgui.color_convert_float4_to_u32(imgui.ImVec4(_color[0], _color[1], _color[2], 0.1))
            draw_list.add_rect_filled(p_min, p_max, color)

            for tb in entry["traceback"]:
                imgui.text( f"{tb}" )

            imgui.tree_pop()

        imgui.pop_style_color(1)
        imgui.pop_id()

    def render( self ):
        imgui.begin( "Console" )

        entries : list[Console.Entry] = self.console.getEntries()

        if not hasattr(self, "_last_console_count"):
            self._last_console_count = 0

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 6.0))

        for i, entry in enumerate(entries):
            self.render_entry( i, entry )

        imgui.pop_style_var(1)

        # scroll to bottom
        if len(entries) > self._last_console_count:
            imgui.set_scroll_here_y(1.0)
            self._last_console_count = len(entries)

        imgui.dummy( imgui.ImVec2(0, 15) )
        imgui.end()