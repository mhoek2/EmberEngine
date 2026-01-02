from typing import TYPE_CHECKING

from OpenGL.GL import *  # pylint: disable=W0614

from modules.context import Context

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

import uuid as uid

class RendererInfo( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper
     
        self.extension_filter = imgui.TextFilter()

    def render( self ):
        if imgui.begin_popup_modal("Renderer Info", None, imgui.WindowFlags_.no_resize)[0]:
            imgui.set_window_size( imgui.ImVec2(600, 400) )  # Example: width=4

            if self.helper.draw_close_button( f"{fa.ICON_FA_CIRCLE_XMARK}", imgui.get_window_width() - 30 ):
                imgui.close_current_popup()

            _region = imgui.get_content_region_avail()
            pos = imgui.get_cursor_screen_pos()

            imgui.text( f"GL_VERSION : { glGetString(GL_VERSION).decode() }" )   
            imgui.text( f"GL_VENDOR  : { glGetString(GL_VENDOR).decode() }" )    
            imgui.text( f"GL_RENDERER: { glGetString(GL_RENDERER).decode() }" )  

            self.helper._node_sep()

            # extensions
            self.extension_filter.draw("Filter extensions")

            _table_flags = imgui.TableFlags_.resizable | \
                           imgui.TableFlags_.hideable | \
                           imgui.TableFlags_.borders_v | \
                           imgui.TableFlags_.borders_outer

            if imgui.begin_table( "OpenGL Extensions", 1, _table_flags ):

                imgui.table_setup_column("Extensions")
                imgui.table_headers_row()

                for extension in self.context.renderer.gl_extensions:

                    # filter
                    if not self.extension_filter.pass_filter(extension):
                        continue

                    imgui.table_next_row()
                    imgui.table_set_column_index(0)
                    imgui.text( extension )

                imgui.end_table()

            imgui.end_popup()