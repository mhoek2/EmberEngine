from typing import TYPE_CHECKING

from modules.context import Context
from modules.transform import Transform

from gameObjects.gameObject import GameObject

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

from pathlib import Path

from modules.gui.types import RadioStruct, ToggleStruct, RotationMode_

class Helper( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = self

    #
    # combo example
    #
    #selected = 0
    #items = self.context.asset_scripts
    #
    #if imgui.begin_combo("combo", items[selected]):
    #    for i, item in enumerate(items):
    #        is_selected = (i == selected)
    #        if imgui.selectable(item, is_selected)[0]:
    #            selected = i
    #        
    #        # Set the initial focus when opening the combo (scrolling + keyboard navigation focus)                    
    #        if is_selected:
    #            imgui.set_item_default_focus()
    #
    #    imgui.end_combo()

    def draw_vec3_control( self, label, vector, resetValue = 0.0, onChange = None, step : float = 0.01 ) -> bool:

        labels = ["X", "Y", "Z"]
        label_colors = [(0.8, 0.1, 0.15), (0.2, 0.7, 0.2), (0.1, 0.25, 0.8)]

        imgui.push_id( f"{label}_vec3_control" )

        imgui.columns( count=2, borders=False )
        imgui.set_column_width(0, 70.0)

        imgui.text( label )
        imgui.next_column()

        #imgui.push_multi_items_width(3, imgui.calc_item_width())
        width = min(125, max(40, (imgui.get_window_size().x / 3) - ( 20 * 3)))

        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 0.0))

        changed_any : bool = False

        for i in range( 0, 3 ):
            imgui.push_style_color(imgui.Col_.button, imgui.ImVec4(label_colors[i][0], label_colors[i][1], label_colors[i][2], 1.0))
            if imgui.button( labels[i] ):
                vector[i] = resetValue
            imgui.pop_style_color(1)
            imgui.same_line()
            imgui.push_item_width( width );

            changed, _value = imgui.drag_float(
                f"##{labels[i]}", vector[i], step
            )
            imgui.pop_item_width();

            if changed:
                vector[i] = _value
                changed_any = True

            if i < 2:
                imgui.same_line()
                imgui.dummy( imgui.ImVec2(5, 5) )
                imgui.same_line()

        imgui.pop_style_var( 1 )

        imgui.columns( count=1 )

        imgui.pop_id()

        if changed_any and onChange is not None:
            onChange( vector )

        return changed_any

    def draw_transform_local( self, _t : Transform ) -> None:
        # position
        self.draw_vec3_control( "Position", _t.local_position, 0.0 )

        # rotation
        match self.gui.inspector.rotation_mode:
            case RotationMode_.degrees:
                self.draw_vec3_control(
                    "Rotation", Transform.vec_to_degrees( _t.local_rotation ), 0.0,
                    step        = self.gui.inspector.rotation_step[RotationMode_.degrees],
                    onChange    = lambda v: _t.set_local_rotation( Transform.vec_to_radians( v ) )
                )
            case RotationMode_.radians:
                self.draw_vec3_control("Rotation", _t.local_rotation, 0.0,
                    step        = self.gui.inspector.rotation_step[RotationMode_.radians]                       
                )

        # scale
        self.draw_vec3_control( "Scale", _t.local_scale, 0.0 )

    def draw_transform_world( self, _t : Transform ) -> None:
        # position
        self.draw_vec3_control( "Position", _t.position, 0.0 )

        # rotation
        match self.gui.inspector.rotation_mode:
            case RotationMode_.degrees:
                self.draw_vec3_control( "Rotation", Transform.vec_to_degrees( _t.rotation ), 0.0,
                    step        = self.gui.inspector.rotation_step[RotationMode_.degrees],
                    onChange    = lambda v: _t.set_rotation( Transform.vec_to_radians( v ) )
                )
            case RotationMode_.radians:
                self.draw_vec3_control( "Rotation", _t.rotation, 0.0,
                    step        = self.gui.inspector.rotation_step[RotationMode_.radians]                        
                )

        # scale
        self.draw_vec3_control( "Scale", _t.scale, 0.0 )


    def toggle_group( self, 
                    label           : str, 
                    items           : list[ToggleStruct],
                    current_states  : list[bool], 
                    start_pos       : imgui.ImVec2 = None 
        ):
        _any_changed = False

        imgui.begin_group()

        old_cursor  = imgui.get_cursor_screen_pos()     # restore cursor pos afterwards
        avail       = imgui.get_content_region_avail()
        draw_list   = imgui.get_window_draw_list()

        if start_pos is not None:
            imgui.set_cursor_screen_pos( start_pos )
        else:
            start_pos = imgui.get_cursor_screen_pos()

        # sizing
        padding_x       = 8
        padding_y       = 6
        item_spacing    = 2
        rounding        = 5.0

        # compute item width based on text
        item_widths = []
        total_width = 0
        for item in items:
            text_width = imgui.calc_text_size( item["icon"] ).x
            width = padding_x * 2 + text_width
            item_widths.append( width )

            hide_func = item.get("hide", lambda: False)
            if hide_func():
                continue

            total_width += width + item_spacing
        total_width -= item_spacing  # last one has no trailing space

        text_height = imgui.get_text_line_height()
        item_height = text_height + padding_y * 2

        group_min = start_pos
        group_max = imgui.ImVec2( start_pos.x + total_width, start_pos.y + item_height )

        # group background
        draw_list.add_rect_filled(
            group_min, group_max,
            imgui.color_convert_float4_to_u32( imgui.ImVec4( 0.2, 0.2, 0.2, 1.0 ) ),
            rounding
        )

        # invisible button
        imgui.invisible_button( label, (total_width, item_height) )
        clicked = imgui.is_item_clicked()

        x = start_pos.x
        #new_index = current_index
        for idx, item in enumerate( items ):
            hide_func = item.get("hide", lambda: False)
            if hide_func():
                continue

            width = item_widths[idx]
            item_min = imgui.ImVec2( x, start_pos.y )
            item_max = imgui.ImVec2( x + width, start_pos.y + item_height )

            if clicked:
                mx, my = imgui.get_mouse_pos()
                if mx >= item_min.x and mx <= item_max.x and my >= item_min.y and my <= item_max.y:
                    current_states[idx] = not current_states[idx]
                    _any_changed = True

            # active item
            if current_states[idx]:
                draw_list.add_rect_filled(
                    item_min, item_max,
                    imgui.color_convert_float4_to_u32( imgui.ImVec4( 0.06, 0.53, 0.98, 1.0 ) ), 
                    rounding
                )

            color = imgui.ImVec4( 1.0, 1.0, 1.0, 1.0 )
            text_pos = imgui.ImVec2( x + padding_x, start_pos.y + padding_y )
            draw_list.add_text( text_pos, imgui.color_convert_float4_to_u32( color ), item["icon"] )

            x += width + item_spacing

        imgui.end_group()
            
        # restore cursor position
        imgui.set_cursor_screen_pos(old_cursor)

        return _any_changed, total_width

    def radio_group( self, 
                    label           : str, 
                    items           : list[RadioStruct],
                    current_index   : int, 
                    start_pos       : imgui.ImVec2 = None 
        ):

        imgui.begin_group()

        old_cursor  = imgui.get_cursor_screen_pos()     # restore cursor pos afterwards
        avail       = imgui.get_content_region_avail()
        draw_list   = imgui.get_window_draw_list()

        if start_pos is not None:
            imgui.set_cursor_screen_pos( start_pos )
        else:
            start_pos = imgui.get_cursor_screen_pos()

        # sizing
        padding_x       = 8
        padding_y       = 6
        item_spacing    = 2
        rounding        = 5.0

        # compute item width based on text
        item_widths = []
        total_width = 0
        for item in items:
            text_width = imgui.calc_text_size( item["icon"] ).x
            width = padding_x * 2 + text_width
            item_widths.append( width )

            hide_func = item.get("hide", lambda: False)
            if hide_func():
                continue

            total_width += width + item_spacing
        total_width -= item_spacing  # last one has no trailing space

        text_height = imgui.get_text_line_height()
        item_height = text_height + padding_y * 2

        group_min = start_pos
        group_max = imgui.ImVec2( start_pos.x + total_width, start_pos.y + item_height )

        # group background
        draw_list.add_rect_filled(
            group_min, group_max,
            imgui.color_convert_float4_to_u32( imgui.ImVec4( 0.2, 0.2, 0.2, 1.0 ) ),
            rounding
        )

        # invisible button
        imgui.invisible_button( label, (total_width, item_height) )
        clicked = imgui.is_item_clicked()

        x = start_pos.x
        new_index = current_index
        for idx, item in enumerate( items ):
            hide_func = item.get("hide", lambda: False)
            if hide_func():
                continue

            width = item_widths[idx]
            item_min = imgui.ImVec2( x, start_pos.y )
            item_max = imgui.ImVec2( x + width, start_pos.y + item_height )

            if clicked:
                mx, my = imgui.get_mouse_pos()
                if mx >= item_min.x and mx <= item_max.x and my >= item_min.y and my <= item_max.y:
                    new_index = idx

            # active item
            if idx == new_index:
                draw_list.add_rect_filled(
                    item_min, item_max,
                    imgui.color_convert_float4_to_u32( imgui.ImVec4( 0.06, 0.53, 0.98, 1.0 ) ), 
                    rounding
                )

            color = imgui.ImVec4( 1.0, 1.0, 1.0, 1.0 )
            text_pos = imgui.ImVec2( x + padding_x, start_pos.y + padding_y )
            draw_list.add_text( text_pos, imgui.color_convert_float4_to_u32( color ), item["icon"] )

            x += width + item_spacing

        imgui.end_group()
            
        # restore cursor position
        imgui.set_cursor_screen_pos(old_cursor)

        return bool(new_index != current_index), new_index, total_width

    def draw_thumb( self, image : int, size : imgui.ImVec2 ):
        #glBindTexture( GL_TEXTURE_2D, image )
        imgui.image( imgui.ImTextureRef(image), size )

    def draw_popup_gameObject( self, uid : str, filter = None ):
        selected = -1
        clicked = False

        if imgui.begin_popup( uid ):

            _, clicked = imgui.selectable(
                f"None##object_-1", clicked
            )

            if clicked:
                imgui.end_popup()
                return True, None

            for i, obj in enumerate(self.context.gameObjects):
                if filter is not None and not filter(obj) or obj._removed :
                    continue

                _, clicked = imgui.selectable(
                    f"{obj.name}##object_{i}", clicked
                )

                if clicked:
                    selected = obj.uuid
                    break;

            imgui.end_popup()

        return clicked, selected

    def draw_button( self, uid : str, region : float = -1.0, colors : list[imgui.ImVec4] = None ) -> bool:
        called : bool = False

        imgui.same_line( region )

        imgui.push_style_color( imgui.Col_.button, self.gui.empty_vec4 )
        imgui.push_style_color( imgui.Col_.button_hovered, self.gui.empty_vec4 )
        imgui.push_style_color( imgui.Col_.button_active, self.gui.empty_vec4 )
                        
        if imgui.button(f"{uid}"):
            called = True
   
        imgui.push_style_color( imgui.Col_.text, colors[1 if imgui.is_item_hovered() else 0] )

        imgui.same_line( region + 4 )
        imgui.text(f"{uid}")

        imgui.pop_style_color(4)

        return called

    def draw_trash_button( self, uid : str, region : float = -1.0 ) -> bool:
        return self.draw_button( 
            uid     = uid, 
            region  = region,
            colors  = self.gui.color_button_trash
        )

    def draw_edit_button( self, uid : str, region : float = -1.0 ) -> bool:
        return self.draw_button( 
            uid     = uid, 
            region  = region,
            colors  = self.gui.color_button_edit_ide
        )

    def draw_close_button( self, uid : str, region : float = -1.0 ) -> bool:
        return self.draw_button( 
            uid     = uid, 
            region  = region,
            colors  = self.gui.color_button_trash
        )
