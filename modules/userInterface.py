from pickletools import read_stringnl_noescape_pair
from typing import Callable, List
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
    def __init__( self, context ):
        super().__init__( context )
        
        self.initialized    : bool = False
        self.io             : imgui.IO = imgui.get_io()

        self.drawWireframe          : bool = False
        self.selectedObject         : GameObject = False
        self.selectedObjectIndex    : int = -1

        self.char_game_state : List = ["play", "stop"]
        self.color_game_state : List[imgui.ImVec4] = [
            imgui.ImVec4(0.2, 0.7, 0.2, 1.0), 
            imgui.ImVec4(0.8, 0.1, 0.15, 1.0)
        ]

        # text_input placeholders
        self.save_as_name : str = "Scene Name"

    def set_selected_object( self, uid : int ):
        self.selectedObjectIndex = uid

        if uid >= 0:
            self.selectedObject = self.context.gameObjects[ uid ]
        else:
            self.selectedObject = False

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
                self.console.log( self.console.Type_.note, [], f"Saved to {self._current_file}")
        
            else:
                self.console.log( self.console.Type_.error, [], "No file selected yet.")

        def open_file( self, path : Path ) -> None:
            """Opens a file and make its content the current text of the text editor"""
            buffer = None

            if not path.is_file():
                self.console.log( self.console.Type_.error, [], f"File: {path} does not exist!" )
                return

            with open(path, encoding="utf8") as f:
                buffer = f.read()

            self.reset();
            self.ed.set_text( buffer )
            self._current_file = path

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


        if imgui.tree_node_ex( "Hierarchy", imgui.TreeNodeFlags_.default_open ):

            for n, obj in enumerate( self.context.gameObjects ):
                if isinstance( obj, GameObject ): # link class name

                    if obj._removed:
                        continue

                    can_hide = True

                    imgui.push_id( f"gameObject_{n}" )
                    _region = imgui.get_content_region_avail()

                    clicked, hover = imgui.selectable(
                        label = obj.name,
                        p_selected = bool( self.selectedObjectIndex == n ),
                        size = imgui.ImVec2(_region.x - 20.0, 15.0)
                    )

                    if clicked:
                        self.set_selected_object( n )
                    
                    # toggle visibility
                    if isinstance( obj, Camera ):
                        can_hide = False

                    if can_hide:
                        imgui.same_line()
                        pos = imgui.get_cursor_screen_pos()
                        pos = imgui.ImVec2(5, pos.y - 3)
                        imgui.set_cursor_screen_pos(pos)

                        imgui.push_item_width(5) 
                        _, self.context.gameObjects[ n ].visible = imgui.checkbox( 
                            "##visible", self.context.gameObjects[ n ].visible )
                        imgui.pop_item_width()

                    # remove gameObject
                    if not self.settings.game_running:
                        imgui.same_line(_region.x + 14)
                        if imgui.button("x"):
                            self.context.removeGameObject( self.context.gameObjects[ n ] )
   
                    imgui.pop_id()
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

    def draw_vec3_control( self, label, vector, resetValue = 0.0 ) -> bool:

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

        changed, _scene["light_color"] = imgui.color_edit3(
            "Light color", _scene["light_color"]
        )

        changed, _scene["ambient_color"] = imgui.color_edit3(
            "Ambient color", _scene["ambient_color"]
        )

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

            if imgui.tree_node_ex( "Transform", imgui.TreeNodeFlags_.default_open ):
                self.context.gui.draw_vec3_control( "Position", gameObject.translate, 0.0 )
                self.context.gui.draw_vec3_control( "Rotation", gameObject.rotation, 0.0 )
                self.context.gui.draw_vec3_control( "Scale", gameObject.scale, 0.0 )

                imgui.tree_pop()

            if imgui.tree_node_ex( "Physics", imgui.TreeNodeFlags_.default_open ):
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
            if imgui.tree_node( "Material" ):

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

        def _scripts( self ):
            if not imgui.tree_node_ex( "Scripts", imgui.TreeNodeFlags_.default_open ):
                return

            assets = Path( self.settings.assets ).resolve()
            _shift_left = 20.0
            _region = imgui.get_content_region_avail()
            _region = imgui.ImVec2(_region.x + _shift_left, _region.y)

            i = -1
            for i, script in enumerate(self.context.gui.selectedObject.scripts):
                imgui.push_id(f"draw_script_{str(script['file'])}")

                name = str(script['file'])

                draw_list = imgui.get_window_draw_list() 
                draw_list.channels_split(2)
                draw_list.channels_set_current(1)

                p_min = imgui.get_cursor_screen_pos()
                p_min = imgui.ImVec2( (p_min.x-_shift_left), p_min.y)
                imgui.set_cursor_screen_pos(p_min)
                
                imgui.begin_group()

                imgui.text(name) # should become the Class name
                imgui.same_line( _region.x - 15 )
                if not self.settings.game_running and imgui.button("x"):
                    self.context.gui.selectedObject.removeScript( script['file'] )

                imgui.same_line( _region.x - 35 )
                if not self.settings.game_running and imgui.button("E"):
                    self.context.gui.text_editor.open_file( script['file'] )

                #imgui.c( label="File##ScriptName", flags=imgui.INPUT_TEXT_READ_ONLY, value=name)

                imgui.end_group()
                _group_height = imgui.get_item_rect_size().y

                # background rect
                _header_height = 20
                p_max = imgui.ImVec2( p_min.x + _region.x, p_min.y + _group_height)

                draw_list.channels_set_current(0)
                draw_list.add_rect_filled(p_min, imgui.ImVec2(p_max.x, (p_min.y + _header_height)), imgui.color_convert_float4_to_u32(imgui.ImVec4(1, 1, 1, 0.2)))
                draw_list.add_rect_filled(imgui.ImVec2(p_min.x, p_min.y + _header_height), p_max, imgui.color_convert_float4_to_u32(imgui.ImVec4(1, 1, 1, 0.1)))
                draw_list.channels_merge()
   
                imgui.pop_id()

            if i == -1:
                imgui.text("No scripts attached")

            imgui.tree_pop()

        def _add_script( self ):
            path = False
        
            _region = imgui.get_content_region_avail()
            pos = imgui.get_cursor_screen_pos()
            pos = imgui.ImVec2( pos.x + (_region.x / 2) - 50, pos.y + _region.y - 20)
            imgui.set_cursor_screen_pos(pos)

            if imgui.button("Add Script"):
                imgui.open_popup("add-script")

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
                self.context.gui.selectedObject.addScript( path )

        def render( self ) -> None:
            imgui.begin( "Inspector" )
  
            if not self.context.gui.selectedObject:
                imgui.end()
                return

            gameObject = self.context.gui.selectedObject

            if isinstance( gameObject, GameObject ):
                #imgui.text( f"{ gameObject.name }" );
                
                changed, gameObject.name = imgui.input_text("Name##ObjectName", gameObject.name)

                # components
                self._transform()
                imgui.separator()

                self._material()
                imgui.separator()

                self._scripts()

                if not self.settings.game_running:
                    self._add_script()

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
            self.set_file_browser_path( path )

        def render_item( self, path ):
            imgui.push_style_color(imgui.Col_.button,          imgui.ImVec4(1.0, 1.0, 1.0, 0.0) ) 
            imgui.push_style_color(imgui.Col_.button_hovered,  imgui.ImVec4(1.0, 1.0, 1.0, 0.1) ) 
            imgui.push_style_color(imgui.Col_.button_active,   imgui.ImVec4(1.0, 1.0, 1.0, 0.2) ) 
               
            if imgui.image_button( f"file##{path}", self.get_icon( path ), self._icon_dim, self._icon_dim):
                if path.is_file():
                    self.open_file( path )

                elif path.is_dir():
                    self.set_path( path )
        
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

            if imgui.tree_node( f"{ entry['message'] }" ):
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

                imgui.same_line(imgui.get_window_width() - 30) 
                if imgui.button("X", imgui.ImVec2(20, 20)):
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