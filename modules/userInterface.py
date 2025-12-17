from typing import TypedDict, Callable, List, Any
from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

from modules.context import Context
from modules.material import Materials
from modules.images import Images
from modules.models import Models
from modules.console import Console
from modules.scene import SceneManager
from modules.transform import Transform
from modules.script import Script
from modules.engineTypes import EngineTypes

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.camera import Camera
from gameObjects.skybox import Skybox

from gameObjects.attachables.physic import Physic
from gameObjects.attachables.physicLink import PhysicLink

from pathlib import Path
import re
import enum
import math
import uuid as uid



# Gui modules
from modules.gui.hierarchy import Hierarchy
from modules.gui.inspector import Inspector
from modules.gui.imGuizmo import ImGuizmo
from modules.gui.consoleWindow import ConsoleWindow
from modules.gui.assetBrowser import AssetBrowser
from modules.gui.textEditor import TextEditor
from modules.gui.project import Project
from modules.gui.sceneSettings import SceneSettings

import pybullet as p

class CustomEvent( Context ):
    def __init__(self):
        self._queue : List = []

    def add(self, name: str, data=None):
        self._queue.append((name, data))

    def has(self, name: str) -> bool:
        """Return True if queue has given entry, Fales if not"""
        return any(event[0] == name for event in self._queue)

    def clear(self, name: str = None):
        """Clear given entry by rebuilding and excluding, no argument will clear entire queue"""
        if name is None: 
            self._queue.clear()

        else:
            self._queue = [e for e in self._queue if e[0] != name]

    def handle(self, name: str, func):
        """Call the given function if the event exists, then clear it automatically."""
        if self.has(name):
            func()
            self.clear(name)

class UserInterface( Context ):

    class RadioStruct(TypedDict):
        name    : str
        icon    : str
        flag    : int

    def __init__( self, context ):
        super().__init__( context )
        
        self.initialized    : bool = False
        self.io             : imgui.IO = imgui.get_io()

        self.drawWireframe          : bool = False
        self.selectedObject         : GameObject = None

        self.status_bar_height      : float = 25.0

        self.game_state_modes : list[UserInterface.RadioStruct] = [
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

        self.color_button_trash : List[imgui.ImVec4] = [
            imgui.ImVec4(1.0, 0.0, 0.0, 0.6),   # default   
            imgui.ImVec4(1.0, 0.0, 0.0, 1.0)    # hover
        ]

        self.color_button_edit_ide : List[imgui.ImVec4] = [
            imgui.ImVec4(0.988, 0.729, 0.012, 0.6),   # default   
            imgui.ImVec4(0.988, 0.729, 0.012, 1.0)    # hover
        ]

        self.color_visibility : List[imgui.ImVec4] = [
            imgui.ImVec4(1.0, 1.0, 1.0, 0.2),   # default   
            imgui.ImVec4(1.0, 1.0, 1.0, 1.0)    # hover
        ]

        self.visibility_icon : List = [
            fa.ICON_FA_EYE_SLASH,    
            fa.ICON_FA_EYE,    
        ]

        self.empty_vec4 = imgui.ImVec4(0.0, 0.0, 0.0, 0.0)

    def initialize_context( self ) -> None:
        if self.initialized:
            return

        self.materials  : Materials = self.context.materials
        self.images     : Images = self.context.images
        self.models     : Models = self.context.models

        self.scene      : SceneManager = self.context.scene

       # self.file_browser_init()
        self.load_gui_icons()

        # user inferface modules
        self.console_window : ConsoleWindow     = ConsoleWindow( self.context )
        self.asset_browser  : AssetBrowser      = AssetBrowser( self.context )
        self.text_editor    : TextEditor        = TextEditor( self.context )
        self.project        : Project           = Project( self.context )
        self.inspector      : Inspector         = Inspector( self.context )
        self.hierarchy      : Hierarchy         = Hierarchy( self.context )
        self.guizmo         : ImGuizmo          = ImGuizmo( self.context )
        self.scene_settings : SceneSettings     = SceneSettings( self.context )

        # drag and drop
        self.dnd_payload    : UserInterface.DragAndDropPayload = UserInterface.DragAndDropPayload()

        self.initialized = True

    def set_selected_object( self, obj : GameObject = None ):
            self.selectedObject = obj

    class DragAndDropPayload:
        class Type_(enum.StrEnum):
            """Explicit source or acceptance types"""
            hierarchy   = enum.auto()
            asset       = enum.auto()

        def __init__(self, 
                     type_id : str = None, 
                     data_id : int = None,
                     data : Any = None ):
            """Wrapper to store additional drag and drop payload data"""
            self.type_id    = type_id
            self.data_id    = data_id
            self.data       = data

        def set_payload( self, type_id : str, data_id : int, data : Any ):
            self.type_id    = type_id
            self.data_id    = data_id
            self.data       = data

            imgui.set_drag_drop_payload_py_id( type=self.type_id, data_id=self.data_id)

        def get_payload_type(self) -> str:
            return self.type_id

        def get_payload_data_id(self) -> int:
            return self.data_id

        def get_payload_data(self):
            return self.data

    def load_gui_icons( self ) -> None:
        """Load icons from game assets gui folder"""
        self.icons = {}
        self.icon_dir = Path( f"{self.settings.engine_gui_path}\\icons" )

        if any( self.icon_dir.glob("*") ):
            for path in self.icon_dir.glob("*"):
                if path.suffix != ".png":
                    continue
                
                icon_id = path.name.replace( path.suffix, "")
                self.icons[f".{icon_id}"] = self.context.images.loadOrFindFullPath( path, flip_y=False )

    # https://github.com/pyimgui/pyimgui/blob/9adcc0511c5ce869c39ced7a2b423aa641f3e7c6/doc/examples/integrations_glfw3_docking.py#L10
    def docking_space(self, name: str):
        viewport = imgui.get_main_viewport()
        x, y = viewport.pos
        w, h = viewport.size

        # reserve space for status bar
        h -= self.status_bar_height

        imgui.set_next_window_pos(imgui.ImVec2(x, y))
        imgui.set_next_window_size(imgui.ImVec2(w, h))
        # imgui.set_next_window_viewport(viewport.id)  # still optional

        # Styles
        imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
        imgui.push_style_var(imgui.StyleVar_.window_rounding, 0.0)
        imgui.push_style_var(imgui.StyleVar_.window_padding, (0, 0))

        flags = (imgui.WindowFlags_.menu_bar 
        | imgui.WindowFlags_.no_docking 
        # | imgui.WINDOW_NO_BACKGROUND
        | imgui.WindowFlags_.no_title_bar
        | imgui.WindowFlags_.no_collapse
        | imgui.WindowFlags_.no_resize
        | imgui.WindowFlags_.no_move
        | imgui.WindowFlags_.no_bring_to_front_on_focus
        | imgui.WindowFlags_.no_nav_focus
        )

        imgui.begin( name, None, flags )

        imgui.pop_style_var()
        imgui.pop_style_var(2)

        # DockSpace
        dockspace_id = imgui.get_id(name)

        imgui.dock_space(
            dockspace_id, 
            imgui.ImVec2(0, 0), 
            imgui.DockNodeFlags_.passthru_central_node
        )

        imgui.end()

    def draw_menu_bar( self ) -> None:
        _open_save_scene_as_modal = False
        _open_new_scene_modal = False
        _open_project_settings = False

        if imgui.begin_main_menu_bar():
            viewport = imgui.get_main_viewport()
            x, y = viewport.pos
            w, h = viewport.size  

            if imgui.begin_menu("File", True):

                if imgui.menu_item( "Quit", '', False, True )[0]:
                    self.renderer.running = False

                if imgui.menu_item( "New Scene", '', False, True )[0]:
                    _open_new_scene_modal = True

                if imgui.menu_item( "Save", '', False, True )[0]:
                    self.context.project.save()
                    self.scene.saveScene()

                if imgui.menu_item( "Save Scene as", '', False, True )[0]:
                    _open_save_scene_as_modal = True
      
                if imgui.menu_item( "Project Settings", '', False, True )[0]:
                    _open_project_settings = True
    
                if imgui.menu_item( "Export", '', False, True )[0]:
                    self.context.project.export()

                imgui.end_menu()

            imgui.menu_item(f"Current Scene: {self.scene.getCurrentSceneUID()}", "", False, False )

            imgui.end_main_menu_bar()

            if _open_save_scene_as_modal:
                imgui.open_popup("Save Scene As##Modal")

            if _open_new_scene_modal:
                imgui.open_popup("New Scene##Modal")

            if _open_project_settings:
                imgui.open_popup("Project Settings")

    def draw_status_bar( self ) -> None:
        viewport = imgui.get_main_viewport()
        x, y = viewport.pos
        w, h = viewport.size

        pos_y = y + h - self.status_bar_height
        imgui.set_next_window_pos(imgui.ImVec2(x, pos_y))
        imgui.set_next_window_size(imgui.ImVec2(w, self.status_bar_height))

        flags = (
            imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_resize
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_scrollbar
            | imgui.WindowFlags_.no_scroll_with_mouse
            | imgui.WindowFlags_.menu_bar
            | imgui.WindowFlags_.no_docking
        )

        if imgui.begin("##StatusBar", None, flags):
            if imgui.begin_menu_bar():
                io = imgui.get_io()

                frame_time = 1000.0 / self.io.framerate
                fps = self.io.framerate

                state = "enabled" if not self.renderer.ImGuiInput else "disabled"
                imgui.menu_item( f"[F1] Input { state }", "", False, False );

                imgui.menu_item( f"{frame_time:.3f} ms/frame ({fps:.1f} FPS)", "", False, False  )

                imgui.end_menu_bar()
            imgui.end()

    def draw_exported_viewport( self ) -> None:
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

    def draw_viewport( self ) -> None:
        imgui.set_next_window_size( imgui.ImVec2(915, 640), imgui.Cond_.first_use_ever )

        imgui.begin( "Viewport" )

        # select render mode
        imgui.push_item_width( 150.0 );
        clicked, self.renderer.renderMode = imgui.combo(
            "##renderMode", self.renderer.renderMode, self.renderer.renderModes
        )
        imgui.pop_item_width();

        # window resizing
        window_size : imgui.ImVec2 = imgui.get_window_size()
        bias_y = 58

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
        self.guizmo.render( _rect_min, image_size )

        # game state
        _rect_min.y += 10.0
        _rect_min.x += 10.0
        _game_state_changed, _new_game_state, group_width = self.radio_group( "game_state_mode",
            items           = self.game_state_modes,
            current_index   = self._game_state_lookup.get( self.context.renderer.game_state, 0 ),
            start_pos       = _rect_min
        )

        if _game_state_changed:
            self.context.renderer.game_state = self.game_state_modes[_new_game_state]["flag"]

        # select imguizmo operation
        _rect_min.x += (group_width + 10.0)
        _, self.guizmo.operation, group_width = self.radio_group( "guizmo_operation",
            items           = self.guizmo.operation_types,
            current_index   = self.guizmo.operation,
            start_pos       = _rect_min
        )

        # select imguizmo mode
        _rect_min.x += (group_width + 10.0)
        _, self.guizmo.mode, group_width = self.radio_group( "guizmo_mode",
            items           = self.guizmo.mode_types,
            current_index   = self.guizmo.mode,
            start_pos       = _rect_min
        )

        imgui.end()

    class GameObjectTypes:
        """Bind meta data to gameObject types, currently only used for the UserInterface
        
        Whenever this finds use in a global scope, move this to: modules.gameObjectTypes.py
        """
        _registry = None

        class Meta:
            """Structure that hold meta data per gameObject type"""
            def __init__( self, _class : type, _icon : str = "" ):
                self._name      = _class.__name__
                self._class     = _class
                self._icon      = _icon

        @staticmethod
        def registry():
            """Singleton registry of the gameObject types (inherting GameObject).

                _registry is stored as a class variable, meaniung:

                - initialized only once per Python process
                - shared across all imports and all scripts

            :return: Map of gameObject type classes to Meta
            :rtype: dict
            """
            if UserInterface.GameObjectTypes._registry is None:
                UserInterface.GameObjectTypes._registry = {
                    Camera: UserInterface.GameObjectTypes.Meta( 
                        _class  = Camera, 
                        _icon   = fa.ICON_FA_CAMERA
                    ),
                    Mesh: UserInterface.GameObjectTypes.Meta( 
                        _class  = Mesh, 
                        _icon   = fa.ICON_FA_CUBE
                    ),
                    Light: UserInterface.GameObjectTypes.Meta( 
                        _class  = Light, 
                        _icon   = fa.ICON_FA_LIGHTBULB
                    ),

                    # baseclass
                    GameObject: UserInterface.GameObjectTypes.Meta( 
                        _class  = GameObject, 
                        _icon   = fa.ICON_FA_CIRCLE_DOT
                    ),
                }

            return UserInterface.GameObjectTypes._registry

        @staticmethod
        def is_gameobject_type( t : type ) -> bool:
            """Check wheter a type is registered as gameObject type
        
            :param t: The type of a variable, e.g., type(variable)
            :type t: type
            :return: True if t is a registered gameObject type
            :rtype: bool
            """
            return t in UserInterface.GameObjectTypes.registry()

        @staticmethod
        def get_gameobject_type( t : type ) -> Meta:
            """Get the gameObject type meta

            :param t: The type of a variable, e.g., type(variable)
            :type t: type
            :return: Meta object if t is a registered gameObject type, None if not
            :rtype: Meta
            """
            if not UserInterface.GameObjectTypes.is_gameobject_type( t ):
                return None

            return UserInterface.GameObjectTypes.registry()[t]



    def draw_settings( self ) -> None:
        imgui.begin( "Settings" )

        _, self.settings.drawWireframe = imgui.checkbox( 
            "Wireframe", self.settings.drawWireframe 
        )

        imgui.same_line()
        _, self.settings.drawGrid = imgui.checkbox( 
            "Grid", self.settings.drawGrid 
        )

        imgui.same_line()
        _, self.settings.drawAxis = imgui.checkbox( 
            "Axis", self.settings.drawAxis 
        )


        imgui.separator()

        #changed, self.settings.grid_color = ImGuiHelpers.color_edit3_safe("Grid color", self.settings.grid_color)

        changed, self.settings.grid_size = imgui.drag_float(
                f"Grid size", self.settings.grid_size, 1
        )

        changed, self.settings.grid_spacing = imgui.drag_float(
                f"Grid spacing", self.settings.grid_spacing, 0.01
        )

        imgui.separator()

        changed, self.context.roughnessOverride = imgui.drag_float(
                f"Roughness override", self.context.roughnessOverride, 0.01
        )

        changed, self.context.metallicOverride = imgui.drag_float(
                f"Metallic override", self.context.metallicOverride, 0.01
        )

        imgui.end()
        return

    # helper
    def draw_vec3_control( self, label, vector, resetValue = 0.0, onChange = None ) -> bool:

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
                f"##{labels[i]}", vector[i], 0.01
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

    # helper
    def _draw_transform_local( self, _t : Transform ) -> None:
        # position
        self.draw_vec3_control( "Position", _t.local_position, 0.0 )

        # rotation
        match self.inspector.rotation_mode:
            case self.inspector.RotationMode_.degrees:
                self.draw_vec3_control(
                    "Rotation", Transform.vec_to_degrees( _t.local_rotation ), 0.0,
                    onChange=lambda v: _t.set_local_rotation( Transform.vec_to_radians( v ) )
                )
            case self.inspector.RotationMode_.radians:
                self.draw_vec3_control("Rotation", _t.local_rotation, 0.0)

        # scale
        self.draw_vec3_control( "Scale", _t.local_scale, 0.0 )

    # helper
    def _draw_transform_world( self, _t : Transform ) -> None:
        # position
        self.draw_vec3_control( "Position", _t.position, 0.0 )

        # rotation
        match self.inspector.rotation_mode:
            case self.inspector.RotationMode_.degrees:
                self.draw_vec3_control( "Rotation", Transform.vec_to_degrees( _t.rotation ), 0.0,
                    onChange = lambda v: _t.set_rotation( Transform.vec_to_radians( v ) )
                )
            case self.RotationMode_.radians:
                self.inspector.draw_vec3_control( "Rotation", _t.rotation, 0.0 )

        # scale
        self.draw_vec3_control( "Scale", _t.scale, 0.0 )

    # helper
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

    # helper
    def draw_thumb( self, image : int, size : imgui.ImVec2 ):
        #glBindTexture( GL_TEXTURE_2D, image )
        imgui.image( imgui.ImTextureRef(image), size )

    # helper
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

    # helper
    def draw_button( self, uid : str, region : float = -1.0, colors : List[imgui.ImVec4] = None ) -> bool:
        called : bool = False

        imgui.same_line( region )

        imgui.push_style_color( imgui.Col_.button, self.context.gui.empty_vec4 )
        imgui.push_style_color( imgui.Col_.button_hovered, self.context.gui.empty_vec4 )
        imgui.push_style_color( imgui.Col_.button_active, self.context.gui.empty_vec4 )
                        
        if imgui.button(f"{uid}"):
            called = True
   
        imgui.push_style_color( imgui.Col_.text, colors[1 if imgui.is_item_hovered() else 0] )

        imgui.same_line( region + 4 )
        imgui.text(f"{uid}")

        imgui.pop_style_color(4)

        return called

    # helper
    def draw_trash_button( self, uid : str, region : float = -1.0 ) -> bool:
        return self.draw_button( 
            uid     = uid, 
            region  = region,
            colors  = self.context.gui.color_button_trash
        )

    # helper
    def draw_edit_button( self, uid : str, region : float = -1.0 ) -> bool:
        return self.draw_button( 
            uid     = uid, 
            region  = region,
            colors  = self.context.gui.color_button_edit_ide
        )

    # helper
    def draw_close_button( self, uid : str, region : float = -1.0 ) -> bool:
        return self.draw_button( 
            uid     = uid, 
            region  = region,
            colors  = self.context.gui.color_button_trash
        )

    # combo example
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

    def render( self ):
        # init
        self.initialize_context()

        # debug print version
        # print(imgui.get_version())

        # exported apps draw directly
        if self.settings.is_exported:
            self.draw_exported_viewport()

        # draw engine GUI
        else:
            self.docking_space('docking_space')
        
            self.draw_menu_bar()
            self.draw_status_bar()

            # windows
            self.draw_viewport()
            self.asset_browser.render()
            self.hierarchy.render()
            self.draw_settings()
            self.inspector.render()
            self.scene_settings.render()

            self.console_window.render()
            self.text_editor.render()

            # popups
            self.project.draw_save_scene_modal( "Save Scene As##Modal", "Choose a name for the scene\n\n", self.scene.saveSceneAs )
            self.project.draw_save_scene_modal( "New Scene##Modal", "Choose a name for the scene\n\n", self.scene.newScene )
            self.project.draw_settings_modal()