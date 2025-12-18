from typing import TYPE_CHECKING

from modules.context import Context

from gameObjects.gameObject import GameObject
from gameObjects.attachables.physic import Physic
from gameObjects.attachables.physic import PhysicLink

from modules.gui.types import GameObjectTypes

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

from dataclasses import dataclass
import enum

@dataclass(frozen=True)
class HierarchyStyle():
    text        : tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    lines       : tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)

class Hierarchy( Context ):

    styles = {
        Physic: HierarchyStyle(
            text  = (0.62, 0.50, 0.78, 1.0), 
            lines = (0.62, 0.50, 0.78, 0.30),
        ),
        PhysicLink: HierarchyStyle(
            text  = (0.72, 0.62, 0.86, 0.95),
            lines = (0.72, 0.62, 0.86, 0.22),
        ) 
    }

    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper

    def tree_node_parse_style( self, obj : GameObject = None ) -> int:
        pushed_styles     : int = 0

        if obj.physic:
            _style = Hierarchy.styles[Physic]
            imgui.push_style_color( imgui.Col_.text, _style.text )
            pushed_styles += 1 

        if obj.physic_link:
            _style = Hierarchy.styles[PhysicLink]
            imgui.push_style_color( imgui.Col_.text, _style.text )
            pushed_styles += 1 

        return pushed_styles

    def tree_node_line_style_color( self, obj : GameObject = None ):
        pushed_styles     : int = 0

        if obj.physic:
            _style = Hierarchy.styles[Physic]
            imgui.push_style_color( imgui.Col_.tree_lines, _style.lines )
            pushed_styles += 1

        if obj.physic_link:
            _style = Hierarchy.styles[PhysicLink]
            imgui.push_style_color( imgui.Col_.tree_lines, _style.lines )
            pushed_styles += 1

        return pushed_styles

    def draw_recursive( self, 
        parent          : GameObject = None, 
        objects         : list[GameObject] = [], 
        depth           : int = 0,
        base_tree_flags : imgui.TreeNodeFlags_ = imgui.TreeNodeFlags_.none,
        ) -> None:
        """Recursivly render the gameObjects in a treenode

        :param parent: The root object or parent during recursion
        :param parent: GameObject
        :param objects: A list of gameobjects, root or children during recursion
        :type objects: list[GameObject]
        :param depth: Current depth in the treenode, starting from 0
        :type depth: int
        :param base_tree_flags: Base ImGui tree flags applied to each tree node.
        :type base_tree_flags: imgui.TreeNodeFlags_
        """

        if not objects:
            return

        for n, obj in enumerate( objects ):
            if obj is None or obj._removed:
                continue

            if obj.parent != parent or obj.parent and parent == None:
                continue

            _t_game_object = GameObjectTypes.get_gameobject_type( type(obj) )
 
            if _t_game_object:
                imgui.push_id( f"{obj._uuid_gui}" )

                # treenode flags
                tree_flags = base_tree_flags
                if not obj.children:
                    tree_flags |= imgui.TreeNodeFlags_.leaf

                if self.gui.selectedObject == obj:
                    tree_flags |= imgui.TreeNodeFlags_.selected

                # push alternate style_colors set by parent, and set style_flags for children
                _pushed_styles = self.tree_node_parse_style( obj )

                _is_open = imgui.tree_node_ex( f"{_t_game_object._icon} {obj.name}", tree_flags )
                _is_hovered = imgui.is_item_hovered()

                if _pushed_styles:
                    imgui.pop_style_color( _pushed_styles )

                #if imgui.is_item_clicked(): # and imgui.is_item_toggled_open():
                if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
                    self.gui.set_selected_object( obj )
    
                # dnd: source
                if imgui.begin_drag_drop_source(imgui.DragDropFlags_.none):
                    self.gui.dnd_payload.set_payload(
                        self.gui.dnd_payload.Type_.hierarchy,
                        obj._uuid_gui,
                        obj
                    )

                    imgui.text(f"{obj.name}")
                    imgui.end_drag_drop_source()

                # dnd: receive
                if imgui.begin_drag_drop_target():
                    payload = imgui.accept_drag_drop_payload_py_id(self.gui.dnd_payload.Type_.hierarchy)
                    if payload is not None:
                        payload_obj : GameObject = self.gui.dnd_payload.get_payload_data()
                        payload_obj.setParent(obj)

                    imgui.end_drag_drop_target()

                # Non-runtime editor GUI
                if not self.renderer.game_runtime:
                    _region = imgui.get_content_region_avail()

                    # visibility
                    #can_hide = True
                    #if isinstance( obj, Camera ):
                    #    can_hide = False
                
                    _button_region = 21 * depth
                    #if _is_hovered or not obj.visible:
                    if self.helper.draw_button( 
                        uid     = f"{self.gui.visibility_icon[int(obj.visible)]}", 
                        region  = _region.x + _button_region + 10,
                        colors  = self.gui.color_visibility
                    ):
                        obj.visible = not obj.visible

                    # remove gameObject
                    if self.helper.draw_trash_button( f"{fa.ICON_FA_TRASH}", _region.x + _button_region + 30 ):
                        self.context.removeGameObject( obj )

                if _is_open:
                    if obj.children:
                        _pushed_styles = self.tree_node_line_style_color( obj )

                        self.draw_recursive( 
                            parent          = obj, 
                            objects         = obj.children, 
                            depth           = depth + 1 ,
                            base_tree_flags = base_tree_flags
                        )

                        if _pushed_styles:
                            imgui.pop_style_color( _pushed_styles )

                    imgui.tree_pop()

                imgui.pop_id()
        
    def render( self ) -> None:
        imgui.begin( "Hierarchy" )

        if imgui.button( "Cube" ):
            self.context.addDefaultCube()

        imgui.same_line()

        if imgui.button( "Light" ):
            self.context.addDefaultLight()

        imgui.same_line()

        if imgui.button( "Empty" ):
            self.context.addEmptyGameObject()

        imgui.same_line()

        if imgui.button( "Camera" ):
            self.context.addDefaultCamera()

        _base_tree_flags =  imgui.TreeNodeFlags_.default_open | \
                            imgui.TreeNodeFlags_.draw_lines_full | \
                            imgui.TreeNodeFlags_.open_on_double_click

        if imgui.tree_node_ex( "Hierarchy", _base_tree_flags ):
            self.draw_recursive( 
                parent          = None, 
                objects         = self.context.gameObjects,
                depth           = 0,
                base_tree_flags = _base_tree_flags
            )
            
            imgui.tree_pop()

        imgui.end()
        return