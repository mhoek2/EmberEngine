from pickletools import read_stringnl_noescape_pair
from typing import Callable, List, Union, Any
from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa
from imgui_bundle import imgui_color_text_edit as ImGuiColorTextEdit

import pygame

from modules.context import Context
from modules.material import Materials
from modules.images import Images
from modules.models import Models
from modules.console import Console
from modules.scene import SceneManager

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.camera import Camera

from pathlib import Path
import textwrap
import re
import uuid as uid
import enum

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
    def __init__( self, context ):
        super().__init__( context )
        
        self.initialized    : bool = False
        self.io             : imgui.IO = imgui.get_io()

        self.drawWireframe          : bool = False
        self.selectedObject         : GameObject = None

        self.char_game_state : List = ["play", "stop"]
        self.color_game_state : List[imgui.ImVec4] = [
            imgui.ImVec4(0.2, 0.7, 0.2, 1.0), 
            imgui.ImVec4(0.8, 0.1, 0.15, 1.0)
        ]

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

        # text_input placeholders
        self.save_as_name : str = "Scene Name"

    def set_selected_object( self, obj : GameObject = None ):
            self.selectedObject = obj

    class DragAndDropPayload:
        def __init__(self, 
                     type_id : str = None, 
                     data_id : int = None,
                     data : Any = None ):
            """Wrapper to store additional drag and drop payload data"""
            self.type_id    = type_id
            self.data_id    = data_id
            self.data       = data

        class Type_(enum.StrEnum):
            """Explicit source or acceptance types"""
            hierarchy   = enum.auto()
            asset       = enum.auto()

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

    #
    # text editor
    #
    class TextEditor( Context ):
        def __init__( self, context ):
            super().__init__( context )

            #with open(__file__, encoding="utf8") as f:
            #    this_file_code = f.read()

            self._current_file : Path = None

            self.ed : ImGuiColorTextEdit.TextEditor = ImGuiColorTextEdit.TextEditor()
            self.ed.set_text("")
            self.ed.set_palette(ImGuiColorTextEdit.TextEditor.PaletteId.dark)
            self.ed.set_language_definition(ImGuiColorTextEdit.TextEditor.LanguageDefinitionId.python)
  
        def get_current_file( self ) -> None:
            """"Returns Path of current file, None if no file selected"""
            return self._current_file

        def reset( self ) -> None:
            """Completely clears the text editor and resets its state."""
            self.ed.set_text("")
            self.ed.set_cursor_position(0, 0)
            self.ed.clear_selections()
            self.ed.clear_extra_cursors()

            self._current_file = None

        def save( self ) -> None:
            text = self.ed.get_text()

            if self._current_file:
                with open(self._current_file, "w", encoding="utf8") as f:
                    f.write(text)

                self.console.note( f"Saved to {self._current_file}")

                self.scene.updateScriptonGameObjects( self._current_file )

            else:
                self.console.error( "No file selected yet.")

        def open_file( self, path : Path ) -> None:
            """Opens a file and make its content the current text of the text editor"""
            buffer = None

            if path.is_absolute():
                relative_path = path.relative_to(self.settings.rootdir)
            else:
                relative_path = path

            if not relative_path.is_file():
                self.console.error( f"File: {relative_path} does not exist!" )
                return

            with open(relative_path, encoding="utf8") as f:
                buffer = f.read()

            self.reset();
            self.ed.set_text( buffer )
            self._current_file = relative_path

        def fix_tabs( self ) -> None:
            """"Hacky but fine for now
 
            This will replace all tabs '\t' with 4 spaces, not just the freshly added tab
            """
            if self._current_file.suffix == ".py":
                _text = self.ed.get_text()
                self.ed.set_text( _text.replace("\t", "    ") )

        def render( self ) -> None: 
            """handles ImGuiColorTextEdit rendering and logic"""
            imgui.begin( "IDE" )

            self.ed.render("Code")

            # handle events
            if imgui.is_window_focused(imgui.FocusedFlags_.root_and_child_windows):
                self.context.cevent.handle( "save",   self.save )
                self.context.cevent.handle( "copy",   self.ed.copy )
                self.context.cevent.handle( "paste",  self.ed.paste )
                self.context.cevent.handle( "undo",   self.ed.undo )
                self.context.cevent.handle( "redo",   self.ed.redo )
                self.context.cevent.handle( "tab",    self.fix_tabs )

            imgui.end()

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
        self.console_window : UserInterface.ConsoleWindow = self.ConsoleWindow( self.context )
        self.asset_browser  : UserInterface.AssetBrowser = self.AssetBrowser( self.context )
        self.text_editor    : UserInterface.TextEditor = self.TextEditor( self.context )
        self.project        : UserInterface.Project = self.Project( self.context )
        self.inspector      : UserInterface.Inspector = self.Inspector( self.context )

        # drag and drop
        self.dnd_payload    : UserInterface.DragAndDropPayload = UserInterface.DragAndDropPayload()

        self.initialized = True

    # https://github.com/pyimgui/pyimgui/blob/9adcc0511c5ce869c39ced7a2b423aa641f3e7c6/doc/examples/integrations_glfw3_docking.py#L10
    def docking_space(self, name: str):
        viewport = imgui.get_main_viewport()
        x, y = viewport.pos
        w, h = viewport.size

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
        imgui.dock_space(dockspace_id, imgui.ImVec2(0, 0) )
        #imgui.dock_space(dockspace_id, imgui.ImVec2(0, 0), passthru_central_node=True)

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

    def draw_status_bar(self, height=25.0) -> None:
        viewport = imgui.get_main_viewport()
        x, y = viewport.pos
        w, h = viewport.size

        pos_y = y + h - height
        imgui.set_next_window_pos(imgui.ImVec2(x, pos_y))
        imgui.set_next_window_size(imgui.ImVec2(w, height))

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

    def draw_gamestate( self ):
        width = imgui.get_window_size().x / 2
        imgui.same_line( width - 50 )

        game_state = int(self.settings.game_running)
        imgui.push_style_color(imgui.Col_.button, self.color_game_state[game_state])

        if imgui.button( self.char_game_state[game_state] ):
            if self.settings.game_running:
                self.settings.game_stop = True
                self.settings.game_running = False
            else:
                self.settings.game_start = True
                self.settings.game_running = True

        imgui.pop_style_color(1)

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

        imgui.same_line()
        self.draw_gamestate()

        # window resizing
        window_size : imgui.ImVec2 = imgui.get_window_size()
        bias_y = 58

        if window_size != imgui.ImVec2(self.renderer.viewport_size.x, self.renderer.viewport_size.y):
            self.renderer.viewport_size = imgui.ImVec2( int(window_size.x), int(window_size.y) )
            self.renderer.setup_projection_matrix( self.renderer.viewport_size - imgui.ImVec2(0, bias_y) )

        glBindTexture( GL_TEXTURE_2D, self.renderer.main_fbo["output"] )

        image       = imgui.ImTextureRef(self.renderer.main_fbo["output"])
        image_size  = imgui.ImVec2(self.renderer.viewport_size.x, (self.renderer.viewport_size.y - bias_y));
        image_uv0   = imgui.ImVec2( 0, 1 )
        image_uv1   = imgui.ImVec2( 1, 0 )
        imgui.image( image, image_size, image_uv0, image_uv1 )

        imgui.end()

    def draw_gameObject_recursive( self, 
        parent          : GameObject = None, 
        objects         : List[GameObject] = [], 
        depth           : int = 0,
        base_tree_flags : imgui.TreeNodeFlags_ = imgui.TreeNodeFlags_.none
        ):
        
        if not objects:
            return

        for n, obj in enumerate( objects ):
            if isinstance( obj, GameObject ): # link class name
                if obj is None:
                    return False 

                if obj._removed:
                    continue

                if obj.parent != parent or obj.parent and parent == None:
                    continue

                imgui.push_id( f"gameObject_{obj._uuid_gui}" )

                # treenode flags
                tree_flags = base_tree_flags
                if not obj.children:
                    tree_flags |= imgui.TreeNodeFlags_.leaf

                if self.selectedObject == obj:
                    tree_flags |= imgui.TreeNodeFlags_.selected

                _is_open = imgui.tree_node_ex( obj.name, tree_flags )
                _is_hovered = imgui.is_item_hovered()

                if imgui.is_item_clicked(): # and imgui.is_item_toggled_open():
                    self.set_selected_object( obj )
    
                # dnd: source
                if imgui.begin_drag_drop_source(imgui.DragDropFlags_.none):
                    self.dnd_payload.set_payload(
                        self.dnd_payload.Type_.hierarchy,
                        obj._uuid_gui,
                        obj
                    )

                    imgui.text(f"{obj.name}")
                    imgui.end_drag_drop_source()

                # dnd: receive
                if imgui.begin_drag_drop_target():
                    payload = imgui.accept_drag_drop_payload_py_id(self.dnd_payload.Type_.hierarchy)
                    if payload is not None:
                        payload_obj = self.dnd_payload.get_payload_data()
                        payload_obj.setParent(obj)

                    imgui.end_drag_drop_target()


                # Non-runtime editor GUI
                if not self.settings.game_running:
                    _region = imgui.get_content_region_avail()

                    # visibility
                    #can_hide = True
                    #if isinstance( obj, Camera ):
                    #    can_hide = False
                
                    #if _is_hovered or not obj.visible:
                    if self.context.gui.draw_button( 
                        uid     = f"{self.visibility_icon[int(obj.visible)]}", 
                        region  = _region.x - 5,
                        colors  = self.context.gui.color_visibility
                    ):
                        obj.visible = not obj.visible

                    # remove gameObject
                    if self.context.gui.draw_trash_button( f"{fa.ICON_FA_TRASH}", _region.x + 14 ):
                        self.context.removeGameObject( obj )

                if _is_open:
                    if obj.children:
                        self.draw_gameObject_recursive( 
                            obj, 
                            obj.children, 
                            depth=depth+1,
                            base_tree_flags=base_tree_flags
                        )

                    imgui.tree_pop()

                imgui.pop_id()
        
    def draw_hierarchy( self ) -> None:
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
            self.draw_gameObject_recursive( 
                None, 
                self.context.gameObjects,
                depth=0,
                base_tree_flags=_base_tree_flags
            )
            
            imgui.tree_pop()

        imgui.end()
        return

    def draw_settings( self ) -> None:
        imgui.begin( "Settings" )

        changed, self.settings.drawWireframe = imgui.checkbox( 
            "Wireframe", self.settings.drawWireframe 
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
                return True, -1

            for i, obj in enumerate(self.context.gameObjects):
                if filter is not None and not filter(obj) or obj._removed :
                    continue

                _, clicked = imgui.selectable(
                    f"{obj.name}##object_{i}", clicked
                )

                if clicked:
                    selected = i
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

    def draw_camera_selector( self ) -> None:
        imgui.text("camera")
        imgui.same_line(100.0)

        _camera : GameObject = self.scene.getCamera()
        _camera_name : str = _camera.name if _camera else "None" 

        if imgui.button( _camera_name ):
            imgui.open_popup("##select_camera")

        imgui.same_line()
        changed_camera_gameobject, _changed_id = self.draw_popup_gameObject(
            "##select_camera", filter=lambda obj: isinstance(obj, Camera ))

        if changed_camera_gameobject:
            self.scene.setCamera( _changed_id )

    def draw_environment( self ) -> None:
        imgui.begin( "Environment" )

        self.draw_camera_selector()

        imgui.separator()

        _scene = self.scene.getCurrentScene()

        #changed, _scene["light_color"] = imgui.color_edit3(
        #    "Light color", _scene["light_color"]
        #)
        #
        #changed, _scene["ambient_color"] = imgui.color_edit3(
        #    "Ambient color", _scene["ambient_color"]
        #)

        imgui.end()
        return

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


    class Inspector( Context ):
        def __init__( self, context ):
            super().__init__( context )

        def _transform( self ) -> None:
            if not self.context.gui.selectedObject:
                return

            gameObject = self.context.gui.selectedObject

            if isinstance( gameObject, Mesh ):
                imgui.text( f"Mesh" );

            if isinstance( gameObject, Light ):
                imgui.text( f"Light" );

            if imgui.tree_node_ex( f"{fa.ICON_FA_CUBE} Transform local", imgui.TreeNodeFlags_.default_open ):
                self.context.gui.draw_vec3_control( "Position", gameObject.transform.local_position, 0.0 )
                self.context.gui.draw_vec3_control( "Rotation", gameObject.transform.local_rotation, 0.0 )
                self.context.gui.draw_vec3_control( "Scale", gameObject.transform.local_scale, 0.0 )
                imgui.tree_pop()


            if imgui.tree_node_ex( f"{fa.ICON_FA_CUBE} Transform world", imgui.TreeNodeFlags_.default_open ):
                pos = gameObject.transform.extract_position()
                rot = gameObject.transform.extract_euler()
                scl = gameObject.transform.extract_scale()

                self.context.gui.draw_vec3_control( "Position", pos, 0.0,          
                    onChange = lambda v: gameObject.transform.updatePositionFromWorld(v)
                )
                self.context.gui.draw_vec3_control( "Rotation", rot, 0.0,
                    onChange = lambda v: gameObject.transform.updateRotationFromWorld(v)
                )
                self.context.gui.draw_vec3_control( "Scale", scl, 0.0,
                    onChange = lambda v: gameObject.transform.updateScaleFromWorld(v)
                )
                imgui.tree_pop()

            if imgui.tree_node_ex( f"{fa.ICON_FA_PERSON_FALLING} Physics", imgui.TreeNodeFlags_.default_open ):
                changed, gameObject.mass = imgui.drag_float(
                        f"Mass", gameObject.mass, 1
                )

                imgui.tree_pop()

            return

        def _material_thumb( self, label, texture_id ) -> None:
            imgui.text( f"{label}" );
            imgui.next_column()
            self.context.gui.draw_thumb( texture_id, imgui.ImVec2(75.0, 75.0) )
            imgui.next_column()

        def _material( self ) -> None:
            if imgui.tree_node( f"{fa.ICON_FA_BRUSH} Material" ):

                if not self.context.gui.selectedObject:
                    imgui.tree_pop()
                    return

                _models = self.context.gui.models
                _images = self.context.gui.images
                _materials = self.context.gui.materials

                gameObject = self.context.gui.selectedObject

                if not isinstance( gameObject, GameObject ):
                    imgui.tree_pop()
                    return

                # collect material(s)
                materials = []

                for mesh in _models.model[gameObject.model].meshes:
                    mesh_index = _models.model[gameObject.model].meshes.index(mesh)
                    mesh_gl = _models.model_mesh[gameObject.model][mesh_index]
      
                    if mesh_gl["material"] >= 0:
                        materials.append( mesh_gl["material"] )

                # visualize material(s)
                multi_mat : bool = True if len(materials) > 1 else False

                for material_id in materials:
                    mat : Materials.Material = _materials.getMaterialByIndex( material_id )

                    is_open : bool = False

                    # use tree node of this mesh has multiple materials
                    if multi_mat:
                        if imgui.tree_node( f"Material ID: { material_id }" ):
                            is_open = True
                    else:
                        imgui.text( f"Material ID: { material_id }" );
                        imgui.separator()
                        is_open = True

                    if is_open:
                        imgui.columns( count=2, borders=False )
                        imgui.set_column_width (0, 70.0 )

                        self._material_thumb( "Albedo",     mat["albedo"]   if 'albedo'     in mat else _images.defaultImage    )
                        self._material_thumb( "Normal",     mat["normal"]   if 'normal'     in mat else _images.defaultNormal   )
                        self._material_thumb( "Phyiscal",   mat["phyiscal"] if 'phyiscal'   in mat else _images.defaultRMO      )
                        self._material_thumb( "Emissive",   mat["emissive"] if 'emissive'   in mat else _images.blackImage      )
            
                        imgui.columns( count=1 )

                    if multi_mat and is_open:
                        imgui.tree_pop()

                imgui.tree_pop()
            return

        def _draw_script_exported_attributes( self, script: GameObject.Script ):
            if not script.get("active"):
                return 

            imgui.dummy( imgui.ImVec2(20, 0) )

            for instance_attr_name, instance_attr in script["exports"].items():
                if script["obj"] is None:
                    continue

                _value = getattr(script["obj"], instance_attr_name)
                _t = instance_attr.type
                _changed = False

                # FLOAT
                if _t is float:
                    _changed, new = imgui.drag_float(f"{instance_attr_name}:", _value, 0.01)

                # INT
                elif _t is int:
                    _changed, new = imgui.drag_int(f"{instance_attr_name}:", _value, 1)

                # STRING
                elif _t is str:
                    _changed, new = imgui.input_text(f"{instance_attr_name}:", _value, 256)

                # BOOL
                elif _t is bool:
                    _changed, new = imgui.checkbox(f"{instance_attr_name}:", _value)

                # Unsupported type
                else:
                    imgui.text(f"{instance_attr_name}: <unsupported {_t}>")

                if _changed:
                    instance_attr.set(new)
                    setattr(script["obj"], instance_attr_name, new)

        def _draw_script( self, index, script: GameObject.Script ):
            _shift_left = 20.0
            _region = imgui.get_content_region_avail()
            _region = imgui.ImVec2(_region.x + _shift_left, _region.y)

            if not imgui.tree_node_ex( f"{fa.ICON_FA_CODE} {script['class_name_f']} (Script)##GameObjectScript", imgui.TreeNodeFlags_.default_open ):
                return

            imgui.push_id(f"draw_script_{str(script["path"])}")

            # actions
            if not self.settings.game_running: 
                imgui.same_line()

                if self.context.gui.draw_trash_button( f"{fa.ICON_FA_TRASH}", _region.x - 20 ):
                    self.context.gui.selectedObject.removeScript( script["path"] )

                if self.context.gui.draw_edit_button( f"{fa.ICON_FA_PEN_TO_SQUARE}", _region.x - 40 ):
                    self.context.gui.text_editor.open_file( script["path"] )

                active_changed, active_state = imgui.checkbox( "Active", script.get("active") )
                if active_changed:
                    script["active"] = active_state
                    self.scene.updateScriptonGameObjects( script["path"] )


            draw_list = imgui.get_window_draw_list() 
            draw_list.channels_split(2)
            draw_list.channels_set_current(1)

            p_min = imgui.get_cursor_screen_pos()
            p_min = imgui.ImVec2( (p_min.x-_shift_left), p_min.y)
            imgui.set_cursor_screen_pos(p_min)
                
            imgui.begin_group()
            imgui.text_colored( imgui.ImVec4(1.0, 1.0, 1.0, 0.6), str(script["path"]) );
            #imgui.c( label="File##ScriptName", flags=imgui.INPUT_TEXT_READ_ONLY, value=name)
            imgui.end_group()

            _group_height = imgui.get_item_rect_size().y

            # background rect
            _header_height = 20
            _bg_color = imgui.color_convert_float4_to_u32(imgui.ImVec4(1, 1, 1, 0.05))
            p_max = imgui.ImVec2( p_min.x + _region.x, p_min.y + _group_height)
            p_min.y -= 3

            draw_list.channels_set_current(0)
            draw_list.add_rect_filled(p_min, imgui.ImVec2(p_max.x, (p_min.y + _header_height)), _bg_color)
            #draw_list.add_rect_filled(imgui.ImVec2(p_min.x, p_min.y + _header_height), p_max, imgui.color_convert_float4_to_u32(imgui.ImVec4(1, 1, 1, 0.1)))
            draw_list.channels_merge()
  
            imgui.pop_id()

            # exported attributes
            self._draw_script_exported_attributes(script)

            imgui.dummy( imgui.ImVec2(20, 0) )
            imgui.tree_pop()

        def _scripts( self ):
            assets = Path( self.settings.assets ).resolve()

            if len(self.context.gui.selectedObject.scripts) == 0:
                imgui.text("No scripts attached")
                return

            for i, script in enumerate(self.context.gui.selectedObject.scripts):
                self._draw_script( i, script )
                imgui.separator()

        def _add_component( self ):
            if self.settings.game_running: 
                return

            path = False

            _tree_flags =   imgui.TreeNodeFlags_.default_open | \
                            imgui.TreeNodeFlags_.leaf | \
                            imgui.TreeNodeFlags_.span_full_width

            if not imgui.tree_node_ex( f"##AddComponentNode", _tree_flags ):
                return

            _region_x = imgui.get_content_region_avail().x
            button_text = "Add Component"
            button_width = imgui.calc_text_size(button_text).x + imgui.get_style().frame_padding.x * 2
            
            offset = (_region_x - button_width ) * 0.5
            imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + offset)

            if imgui.button( button_text ):
                imgui.open_popup("add-script")

            # dnd: receive
            if imgui.begin_drag_drop_target():
                is_asset = imgui.accept_drag_drop_payload_py_id(self.context.gui.dnd_payload.Type_.asset)
                if is_asset is not None:
                    path = self.context.gui.dnd_payload.get_payload_data()

                imgui.end_drag_drop_target()

            imgui.same_line()

            if imgui.begin_popup("add-script"):

                # todo:
                # perhaps there should be a separate thread for this
                # that either updates periodicly, or tracks changes in assets folder
                self.context.findScripts()

                # project assets
                assets = Path( self.settings.assets ).resolve()
                for i, script in enumerate(self.context.asset_scripts):
                    imgui.push_id(f"add_script_{str(script)}")
                    clicked = False

                    name = str(script.relative_to(assets))
                    _, clicked = imgui.selectable(
                        f"{name}", clicked
                    )

                    if clicked:
                        path = script

                    imgui.pop_id()

                # engine assets not supported yet
                # ..

                imgui.end_popup()

            if path:
                _script : GameObject.Script = {
                    "path"      : path,
                    "obj"       : None,
                    "exports"   : {}
                }
                self.context.gui.selectedObject.addScript( _script )

            imgui.tree_pop()

        def render( self ) -> None:
            imgui.begin( "Inspector" )
  
            if not self.context.gui.selectedObject:
                imgui.end()
                return

            gameObject = self.context.gui.selectedObject

            if isinstance( gameObject, GameObject ):
                imgui.text_colored( imgui.ImVec4(1.0, 1.0, 1.0, 0.6), f"uuid: { gameObject.uuid.hex }" );
                
                active_changed, active_state = imgui.checkbox( "Active", gameObject.active )
                if active_changed:
                    gameObject.active = active_state

                _, _ = imgui.checkbox( "Active Parent", gameObject.hierachyActive() )

                _, gameObject.name = imgui.input_text("Name##ObjectName", gameObject.name)


                # components
                self._transform()
                imgui.separator()

                self._material()
                imgui.separator()

                self._scripts()

                self._add_component()

            imgui.end()
            return

    #
    # asset explorer
    #
    class AssetBrowser( Context ):
        def __init__( self, context ):
            super().__init__( context )

            self._file_browser_dir = self.get_rootpath()
            self._icon_dim = imgui.ImVec2(75.0, 75.0)  

        def open_file( self, path ) -> None:
            if path.suffix == ".fbx" or path.suffix == ".obj":
                game_object_name = path.name.replace(path.suffix, "")
                self.context.addGameObject( 
                        Mesh( self.context,
                        name        = game_object_name,
                        model_file  = str( path ),
                        translate   = [ 0, 0, 0 ],
                        scale       = [ 1, 1, 1 ],
                        rotation    = [ 0.0, 0.0, 0.0 ]
                ) )
            if path.suffix == ".scene":
                self.scene.clearEditorScene()
                self.scene.loadScene( path.stem )

            if path.suffix == ".py":
                self.context.gui.text_editor.open_file( path )

        def get_rootpath( self ) -> Path:
            return Path( self.settings.assets ).resolve()

        def get_icon( self, path ) -> imgui.ImTextureRef:
            _icons = self.context.gui.icons

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
                self.context.gui.dnd_payload.set_payload(
                    self.context.gui.dnd_payload.Type_.asset,
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

    #
    # Console
    #
    class ConsoleWindow( Context ):
        def __init__( self, context ):
            super().__init__( context )

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

            entries : List[Console.Entry] = self.console.getEntries()

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

    #
    # Project
    #
    class Project( Context ):
        def __init__( self, context ):
            super().__init__( context )

        def draw_save_scene_modal( self, popup_uid : str, note : str, callback : Callable = None ):
            if imgui.begin_popup_modal( popup_uid, None, imgui.WindowFlags_.always_auto_resize)[0]:
                imgui.text( note )
                imgui.separator()

                changed, self.save_as_name = imgui.input_text( "Name##SceneName", self.save_as_name )

                if imgui.button("Save", imgui.ImVec2(120, 0)):
                    callback( self.save_as_name )
                    imgui.close_current_popup()

                imgui.set_item_default_focus()
                imgui.same_line()
                if imgui.button("Cancel", imgui.ImVec2(120, 0)):
                    imgui.close_current_popup()

                imgui.end_popup()

        def _draw_export( self, _region ):
            """Display export settings, eg: name"""

            # project name
            changed, project_name = imgui.input_text( "Name##ProjectName", self.project.meta.get("name"))

            if changed:
                filtered_name = re.sub(self.settings.executable_format, "", project_name)

                if filtered_name != self.project.meta["name"]:
                    self.project.meta["name"] = filtered_name

            # export using pyinstaller --clean flag
            _, self.project.meta["export_clean"] = imgui.checkbox( 
                "Clean on export##export_clean", self.context.project.meta["export_clean"] )
       
           # export using pyinstaller console enable
            _, self.project.meta["export_debug"] = imgui.checkbox( 
                "Debug export##export_debug", self.context.project.meta["export_debug"] )

        def _draw_scenes( self, _region ):
            # keep updating the scenes List?
            # or just on open?
            self.scene.getScenes()

            for scene in self.scene.scenes:
                scene_uid : str = scene["uid"]
                imgui.push_id( f"scne_{scene_uid}" )

                imgui.text(scene["name"])

                if scene["uid"] == self.project.meta["default_scene"]:
                    imgui.same_line( _region.x - 175 )
                    imgui.text("default")

                imgui.same_line( _region.x - 115 )
                if imgui.button( "Load" ):
                    self.scene.clearEditorScene()
                    self.scene.loadScene( scene["uid"] )

                if scene_uid != self.settings.default_scene.stem:
                    imgui.same_line( _region.x - 75 )

                    if imgui.button( "Set default" ):
                        self.project.setDefaultScene( scene["uid"] )

                imgui.separator()
                imgui.pop_id()

        def draw_settings_modal( self ):
            if imgui.begin_popup_modal("Project Settings", None, imgui.WindowFlags_.no_resize)[0]:
                imgui.set_window_size( imgui.ImVec2(600, 400) )  # Example: width=4

                if self.context.gui.draw_close_button( f"{fa.ICON_FA_CIRCLE_XMARK}", imgui.get_window_width() - 30 ):
                    imgui.close_current_popup()

                _region = imgui.get_content_region_avail()
                pos = imgui.get_cursor_screen_pos()

                self._draw_export( _region )
                self._draw_scenes( _region )

                pos = imgui.ImVec2( pos.x, pos.y + _region.y - 20)
                imgui.set_cursor_screen_pos(pos)  

                if imgui.button( "Save Project" ):
                    self.context.project.save()

                imgui.same_line()

                if imgui.button( "Export Project" ):
                    self.project.save()
                    self.context.project.export()

                imgui.end_popup()

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
            self.draw_hierarchy()
            self.draw_settings()
            self.inspector.render()
            self.draw_environment()

            self.console_window.render()
            self.text_editor.render()

            # popups
            self.project.draw_save_scene_modal( "Save Scene As##Modal", "Choose a name for the scene\n\n", self.scene.saveSceneAs )
            self.project.draw_save_scene_modal( "New Scene##Modal", "Choose a name for the scene\n\n", self.scene.newScene )
            self.project.draw_settings_modal()