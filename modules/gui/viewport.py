from OpenGL.GL import *  # pylint: disable=W0614

from typing import TYPE_CHECKING

from modules.context import Context

from modules.gui.types import RadioStruct, ToggleStruct

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

import uuid as uid

class Viewport( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper

        self.game_state_modes : list[RadioStruct] = [
            {
                "name"  : "Start",
                "icon"  : fa.ICON_FA_CIRCLE_PLAY,
                "flag"  : self.context.renderer.GameState_.running,
            },
            {
                "name"  : "Pause",
                "icon"  : fa.ICON_FA_CIRCLE_PAUSE,
                "flag"  : self.context.renderer.GameState_.paused,
                "hide"  : lambda: not self.context.renderer.game_runtime
            },
            {
                "name"  : "Stop",
                "icon"  : fa.ICON_FA_CIRCLE_STOP,
                "flag"  : self.context.renderer.GameState_.none,
            }
        ]
        self._game_state_lookup = {
            op["flag"]  : i
                for i, op in enumerate(self.game_state_modes)
        }

        self.overlay_toggles : list[ToggleStruct] = [
            {
                "name"  : "Grid",
                "icon"  : fa.ICON_FA_BORDER_ALL,
            },
            {
                "name"  : "Axis",
                "icon"  : fa.ICON_FA_COMPASS,
            },
            {
                "name"  : "Wireframe",
                "icon"  : fa.ICON_FA_GLOBE,
            },
            {
                "name"  : "Colliders",
                "icon"  : fa.ICON_FA_PERSON_FALLING_BURST,
            },
        ]


    def _draw_render_mode( self, start_pos : imgui.ImVec2 = None ) -> None:
        #imgui.begin_group()
        total_width = 150
        old_cursor  = imgui.get_cursor_screen_pos()     # restore cursor pos afterwards
        draw_list   = imgui.get_window_draw_list()

        if start_pos is not None:
            imgui.set_cursor_screen_pos( start_pos )
        else:
            start_pos = imgui.get_cursor_screen_pos()

        # combo
        imgui.push_item_width( total_width );
        imgui.push_style_var(imgui.StyleVar_.frame_padding, (8, 6))
        imgui.push_style_var(imgui.StyleVar_.frame_rounding, 5.0)
        imgui.push_style_var(imgui.StyleVar_.frame_border_size, 0.0)

        # combo
        imgui.push_style_color(imgui.Col_.frame_bg,        (0.2, 0.2, 0.2, 1.0))
        imgui.push_style_color(imgui.Col_.frame_bg_hovered,(0.2, 0.2, 0.2, 1.0))
        imgui.push_style_color(imgui.Col_.frame_bg_active, (0.3, 0.3, 0.3, 1.0))
        imgui.push_style_color(imgui.Col_.button,          (0, 0, 0, 1.0))

        # dropown
        imgui.push_style_var(imgui.StyleVar_.popup_rounding, 5.0)
        imgui.push_style_var(imgui.StyleVar_.popup_border_size, 0.0)
        imgui.push_style_var(imgui.StyleVar_.window_padding, (6, 6))

        imgui.push_style_color(imgui.Col_.popup_bg,          (0.18, 0.18, 0.18, 1.0))
        imgui.push_style_color(imgui.Col_.header,            (0.06, 0.53, 0.98, 1.0))
        imgui.push_style_color(imgui.Col_.header_hovered,    (0.06, 0.53, 0.98, 0.85))
        imgui.push_style_color(imgui.Col_.header_active,     (0.06, 0.53, 0.98, 1.0))
        imgui.push_style_color(imgui.Col_.text,              (1.0, 1.0, 1.0, 1.0))

        changed, _render_mode = imgui.combo(
            "##renderMode", self.renderer.renderMode, self.renderer.renderModes
        )
        if changed:
            self.renderer.renderMode = _render_mode

        imgui.pop_style_color(9)
        imgui.pop_style_var(6)
        imgui.pop_item_width();

        #imgui.end_group()

        # restore cursor position
        imgui.set_cursor_screen_pos(old_cursor)

        return changed, total_width

    def render( self ) -> None:
        imgui.set_next_window_size( imgui.ImVec2(915, 640), imgui.Cond_.first_use_ever )
        imgui.push_style_var(imgui.StyleVar_.window_padding, (0.0, 0.0))
        imgui.begin( "Viewport" )

        # window resizing
        window_size : imgui.ImVec2 = imgui.get_window_size()
        bias_y = 12.0

        if window_size != imgui.ImVec2(self.renderer.viewport_size.x, self.renderer.viewport_size.y):
            self.renderer.viewport_size = imgui.ImVec2( int(window_size.x), int(window_size.y) ) - imgui.ImVec2(0, bias_y)

            self.renderer.setup_projection_matrix( 
                size = self.renderer.viewport_size
            )

        glBindTexture( GL_TEXTURE_2D, self.renderer.main_fbo["output"] )

        image       = imgui.ImTextureRef(self.renderer.main_fbo["output"])
        image_size  = imgui.ImVec2(self.renderer.viewport_size.x, (self.renderer.viewport_size.y - bias_y));
        image_uv0   = imgui.ImVec2( 0, 1 )
        image_uv1   = imgui.ImVec2( 1, 0 )
        imgui.image( image, image_size, image_uv0, image_uv1 )

        # ImGuizmo
        _rect_min = imgui.get_item_rect_min()
        self.gui.guizmo.render( _rect_min, image_size )

        # game state
        _rect_min.y += 10.0
        _rect_min.x += 10.0
        _game_state_changed, _new_game_state, group_width = self.helper.radio_group( "game_state_mode",
            items           = self.game_state_modes,
            current_index   = self._game_state_lookup.get( self.context.renderer.game_state, 0 ),
            start_pos       = _rect_min
        )

        if _game_state_changed:
            self.context.renderer.game_state = self.game_state_modes[_new_game_state]["flag"]

        # select imguizmo operation
        _rect_min.x += (group_width + 10.0)
        _, self.gui.guizmo.operation, group_width = self.helper.radio_group( "guizmo_operation",
            items           = self.gui.guizmo.operation_types,
            current_index   = self.gui.guizmo.operation,
            start_pos       = _rect_min
        )

        # select imguizmo mode
        _rect_min.x += (group_width + 10.0)
        _, self.gui.guizmo.mode, group_width = self.helper.radio_group( "guizmo_mode",
            items           = self.gui.guizmo.mode_types,
            current_index   = self.gui.guizmo.mode,
            start_pos       = _rect_min
        )

        # viewport overlay toggles
        _rect_min.x += (group_width + 10.0)
        _states : list = [
                self.context.settings.drawGrid,
                self.context.settings.drawAxis,
                self.context.settings.drawWireframe,
                self.context.settings.drawColliders,
        ]
        changed, group_width = self.helper.toggle_group( "viewport_overlay_toggles",
            items           = self.overlay_toggles,
            current_states  = _states,
            start_pos       = _rect_min
        )
        if changed: (
            self.context.settings.drawGrid,
            self.context.settings.drawAxis,
            self.context.settings.drawWireframe,
            self.context.settings.drawColliders,
        ) = _states

        # render modes
        _rect_min.x += (group_width + 10.0)
        self._draw_render_mode( start_pos=_rect_min )

        imgui.end()
        imgui.pop_style_var()

    def render_exported( self ) -> None:
        window_size = imgui.get_io().display_size 

        glBindTexture(GL_TEXTURE_2D, self.renderer.main_fbo["output"])

        imgui.set_next_window_pos( imgui.ImVec2(0, 0) )
        imgui.set_next_window_size( imgui.ImVec2(window_size.x, window_size.y) )

        flags = (
            imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_resize
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_scrollbar
        )

        imgui.begin("ExportedViewport", None, flags)

        image       = imgui.ImTextureRef(self.renderer.main_fbo["output"])
        image_uv0   = imgui.ImVec2( 0, 1 )
        image_uv1   = imgui.ImVec2( 1, 0 )
        imgui.image( image, window_size, image_uv0, image_uv1 )

        imgui.end()