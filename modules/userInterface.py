from typing import TypedDict, Callable, List, Any
from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

from imgui_bundle import imgui
from imgui_bundle import imguizmo
from imgui_bundle import icons_fontawesome_6 as fa
from imgui_bundle import imgui_color_text_edit as ImGuiColorTextEdit

from pyrr import Matrix44, Vector3
import numpy as np

from modules.context import Context
from modules.material import Materials
from modules.images import Images
from modules.models import Models
from modules.console import Console
from modules.scene import SceneManager
from modules.transform import Transform
from modules.script import Script

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.light import Light
from gameObjects.camera import Camera
from gameObjects.skybox import Skybox

from gameObjects.attachables.physic import Physic
from gameObjects.attachables.physicLink import PhysicLink

from pathlib import Path
import textwrap
import re
import enum
import math
import uuid as uid

from modules.transform import Transform
from modules.engineTypes import EngineTypes

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
        self.gizmo          : imguizmo.im_guizmo = imguizmo.im_guizmo

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
        self.console_window : UserInterface.ConsoleWindow = self.ConsoleWindow( self.context )
        self.asset_browser  : UserInterface.AssetBrowser = self.AssetBrowser( self.context )
        self.text_editor    : UserInterface.TextEditor = self.TextEditor( self.context )
        self.project        : UserInterface.Project = self.Project( self.context )
        self.inspector      : UserInterface.Inspector = self.Inspector( self.context )
        self.hierarchy      : UserInterface.Hierarchy = self.Hierarchy( self.context )
        self.guizmo         : UserInterface.ImGuizmo = self.ImGuizmo( self.context )
        self.scene_settings : UserInterface.SceneSettings = self.SceneSettings( self.context )

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

    #
    # Guizmo
    #
    class ImGuizmo( Context ):
        def __init__( self, context ):
            super().__init__( context )

            self.gizmo      = self.context.gui.gizmo

            self.operation      : int   = 0
            self.mode           : int   = 0

            self.mode_types : list[UserInterface.RadioStruct] = [
                {
                    "name"  : "Local",
                    "icon"  : fa.ICON_FA_LOCATION_CROSSHAIRS,
                    "flag"  : self.gizmo.MODE.local,
                },
                {
                    "name"  : "World",
                    "icon"  : fa.ICON_FA_EARTH_AMERICAS,
                    "flag"  : self.gizmo.MODE.world,
                }
            ]

            self.operation_types : list[UserInterface.RadioStruct] = [
                {
                    "name"  : "Translate",
                    "icon"  : fa.ICON_FA_ARROWS_UP_DOWN_LEFT_RIGHT,
                    "flag"  : self.gizmo.OPERATION.translate,
                },
                {
                    "name"  : "Rotate",
                    "icon"  : fa.ICON_FA_GROUP_ARROWS_ROTATE,
                    "flag"  : self.gizmo.OPERATION.rotate,
                },
                {
                    "name"  : "Scale",
                    "icon"  : fa.ICON_FA_UP_RIGHT_AND_DOWN_LEFT_FROM_CENTER,
                    "flag"  : self.gizmo.OPERATION.scale,
                }
            ]

        def to_matrix16(self, mat):
            """
            Convert a numpy.ndarray or Pyrr Matrix44 to ImGuizmo Matrix16.
            Ensures column-major order for ImGuizmo.
            """
            if isinstance(mat, np.ndarray):
                floats = mat.astype(float).reshape(16).tolist()
                return self.gizmo.Matrix16(floats)

            if isinstance(mat, Matrix44):
                floats = mat.flatten().tolist()
                return self.gizmo.Matrix16(floats)

            raise TypeError(f"Unsupported matrix type: {type(mat)}")

        def begin_frame( self ):
            #self.gizmo.set_im_gui_context(imgui.get_current_context())
            self.gizmo.begin_frame()

        def render( self, _rect_min : imgui.ImVec2, _image_size : imgui.ImVec2 ) -> None:
            self.begin_frame()

            self.gizmo.push_id(0)

            self.gizmo.set_drawlist( imgui.get_window_draw_list() )
            self.gizmo.set_rect(
                _rect_min.x, _rect_min.y, 
                _image_size.x, _image_size.y
            )
            self.gizmo.set_orthographic(False)

            view_m16        = self.to_matrix16(self.renderer.view)
            proj_m16        = self.to_matrix16(self.renderer.projection)

            # selected item
            if self.context.gui.selectedObject:
                gameObject = self.context.gui.selectedObject
                _t          : Transform     = gameObject.transform

                model_m16 = self.to_matrix16(_t._getModelMatrix())

                glEnable(GL_DEPTH_TEST)
                glDepthFunc(GL_LEQUAL)
                self.gizmo.manipulate(
                    view_m16,
                    proj_m16,
                    self.operation_types[self.operation]["flag"],
                    self.mode_types[self.mode]["flag"],
                    model_m16,
                    None,
                    None,
                    None,
                    None
                )

                # write result back on update
                if self.gizmo.is_using():
                    _t.world_model_matrix = Matrix44(model_m16.values.astype(float))
                    _t._update_local_from_world()
                    gameObject._mark_dirty( GameObject.DirtyFlag_.transform )
                    
            self.gizmo.view_manipulate(
                view_m16,
                3.0,
                imgui.ImVec2((_rect_min.x + _image_size.x) - 142, _rect_min.y + 20),
                imgui.ImVec2(128, 128),
                0x10101010,
            )

            if self.gizmo.is_using_view_manipulate():
                view_m16 = Matrix44(view_m16.values.astype(float))
                world_matrix = np.array(view_m16.inverse).reshape((4, 4)).T

                self.renderer.camera.camera_pos     = Vector3(world_matrix[:3, 3])
                self.renderer.camera.camera_right   = Vector3(world_matrix[:3, 0])
                self.renderer.camera.camera_up      = Vector3(world_matrix[:3, 1])
                self.renderer.camera.camera_front   = -Vector3(world_matrix[:3, 2])

                self.renderer.camera.update_yaw_pitch_from_front()
                #self.renderer.view = self.renderer.camera.get_view_matrix()

            self.gizmo.pop_id()

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
            if self._current_file.suffix == self.settings.SCRIPT_EXTENSION:
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

    class Hierarchy( Context ):
        """Logic related to rendering the Hierarchy window"""
        def __init__( self, context ):
            super().__init__( context )

        def draw_recursive( self, 
            parent          : GameObject = None, 
            objects         : list[GameObject] = [], 
            depth           : int = 0,
            base_tree_flags : imgui.TreeNodeFlags_ = imgui.TreeNodeFlags_.none
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

                _t_game_object = UserInterface.GameObjectTypes.get_gameobject_type( type(obj) )
 
                if _t_game_object:
                    imgui.push_id( f"{obj._uuid_gui}" )

                    # treenode flags
                    tree_flags = base_tree_flags
                    if not obj.children:
                        tree_flags |= imgui.TreeNodeFlags_.leaf

                    if self.context.gui.selectedObject == obj:
                        tree_flags |= imgui.TreeNodeFlags_.selected

                    icon : str = fa.ICON_FA_CUBE

                    _is_open = imgui.tree_node_ex( f"{_t_game_object._icon} {obj.name}", tree_flags )
                    _is_hovered = imgui.is_item_hovered()

                    #if imgui.is_item_clicked(): # and imgui.is_item_toggled_open():
                    if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
                        self.context.gui.set_selected_object( obj )
    
                    # dnd: source
                    if imgui.begin_drag_drop_source(imgui.DragDropFlags_.none):
                        self.context.gui.dnd_payload.set_payload(
                            self.context.gui.dnd_payload.Type_.hierarchy,
                            obj._uuid_gui,
                            obj
                        )

                        imgui.text(f"{obj.name}")
                        imgui.end_drag_drop_source()

                    # dnd: receive
                    if imgui.begin_drag_drop_target():
                        payload = imgui.accept_drag_drop_payload_py_id(self.context.gui.dnd_payload.Type_.hierarchy)
                        if payload is not None:
                            payload_obj : GameObject = self.context.gui.dnd_payload.get_payload_data()
                            payload_obj.setParent(obj)

                        imgui.end_drag_drop_target()


                    # Non-runtime editor GUI
                    if not self.renderer.game_runtime:
                        _region = imgui.get_content_region_avail()

                        # visibility
                        #can_hide = True
                        #if isinstance( obj, Camera ):
                        #    can_hide = False
                
                        #if _is_hovered or not obj.visible:
                        if self.context.gui.draw_button( 
                            uid     = f"{self.context.gui.visibility_icon[int(obj.visible)]}", 
                            region  = _region.x - 5,
                            colors  = self.context.gui.color_visibility
                        ):
                            obj.visible = not obj.visible

                        # remove gameObject
                        if self.context.gui.draw_trash_button( f"{fa.ICON_FA_TRASH}", _region.x + 14 ):
                            self.context.removeGameObject( obj )

                    if _is_open:
                        if obj.children:
                            self.draw_recursive( 
                                obj, 
                                obj.children, 
                                depth=depth+1,
                                base_tree_flags=base_tree_flags
                            )

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

    class SceneSettings( Context ):

        def __init__( self, context ):
            super().__init__( context )

            self.test_cubemap_initialized = False

            self.test_cubemap = None
            self.test_cubemap_update = True

        def _camera_selector( self ) -> None:
            imgui.text("camera")
            imgui.same_line(100.0)

            changed : bool = False
            _uuid   : uid.UUID = None

            _camera : GameObject = self.scene.getCamera()
            _camera_name : str = _camera.name if _camera else "None" 

            imgui.push_id( f"gui_camera_selected" )

            if imgui.button( _camera_name ):
                imgui.open_popup("##select_camera")

            # dnd: receive
            if imgui.begin_drag_drop_target():
                payload = imgui.accept_drag_drop_payload_py_id(self.context.gui.dnd_payload.Type_.hierarchy)
                if payload is not None:
                    payload_obj : GameObject = self.context.gui.dnd_payload.get_payload_data()
                    _uuid = payload_obj.uuid
                    changed = True

                imgui.end_drag_drop_target()

            else: 
                changed, _uuid = self.context.gui.draw_popup_gameObject(
                    "##select_camera", filter=lambda obj: isinstance(obj, Camera ))

            if changed:
                self.scene.setCamera( _uuid )

            imgui.pop_id()
            imgui.separator()

        def _sun_selector( self ) -> None:
            imgui.text("sun")
            imgui.same_line(100.0)

            changed : bool = False
            _uuid   : uid.UUID = None

            _sun : GameObject = self.scene.getSun()
            _sun_name : str = _sun.name if _sun else "None" 

            imgui.push_id( f"gui_sun_selected" )

            if imgui.button( _sun_name ):
                imgui.open_popup("##select_sun")

            # dnd: receive
            if imgui.begin_drag_drop_target():
                payload = imgui.accept_drag_drop_payload_py_id(self.context.gui.dnd_payload.Type_.hierarchy)
                if payload is not None:
                    payload_obj : GameObject = self.context.gui.dnd_payload.get_payload_data()
                    _uuid = payload_obj.uuid
                    changed = True

                imgui.end_drag_drop_target()

            else: 
                changed, _uuid = self.context.gui.draw_popup_gameObject(
                    "##select_sun", filter=lambda obj: isinstance(obj, Light ))

            if changed:
                self.scene.setSun( _uuid )
        
            imgui.pop_id()
            imgui.separator()

        def _skybox_preview( self, scene : SceneManager.Scene ) -> None:
            """Preview skybox sides
            
            This logic needs to be refactored, its basicly implemented as concept
            """
            if not self.test_cubemap_initialized:
                self.test_cubemap = glGenTextures(6)

            if self.test_cubemap_update:
                skybox = self.context.cubemaps.cubemap[self.context.environment_map]
                glBindTexture(GL_TEXTURE_CUBE_MAP, skybox)
                pixels = []
                
                size = 0
                for i in range(6):
                    # extract pixels
                    pixels.append( glGetTexImage(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_RGBA, GL_UNSIGNED_BYTE) )

                    size = glGetTexLevelParameteriv(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_TEXTURE_WIDTH)    # width
                    #h = glGetTexLevelParameteriv(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_TEXTURE_HEIGHT)     # height

                    glBindTexture(GL_TEXTURE_2D, self.test_cubemap[i])
                    
                    # allocate storag once
                    if not self.test_cubemap_initialized: 
                        glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, size, size)

                    # copy
                    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, size, size, GL_RGBA, GL_UNSIGNED_BYTE, pixels[i])
                    
                    self.test_cubemap_update = False

                # just for storage lol
                if not self.test_cubemap_initialized:
                    self.test_cubemap_initialized = True

            if imgui.tree_node_ex( f"{fa.ICON_FA_CUBE} Skybox preview", 0 ):
                if self.test_cubemap is not None:
                    for i in range(6):
                        glBindTexture( GL_TEXTURE_2D, self.test_cubemap[i] )

                        image       = imgui.ImTextureRef(self.test_cubemap[i])
                        image_size  = imgui.ImVec2(100, 100);
                        image_uv0   = imgui.ImVec2( 0, 1 )
                        image_uv1   = imgui.ImVec2( 1, 0 )
                        imgui.image( image, image_size, image_uv0, image_uv1 )

                        if i % 3 != 2:
                            imgui.same_line()

                imgui.tree_pop()

        def _sky_settings( self, scene : SceneManager.Scene ) -> None:
            type_names = [t.name for t in Skybox.Type_]

            changed, new_index = imgui.combo(
                "Sky type",
                scene["sky_type"],
                type_names
            )
            if changed:
                scene["sky_type"] = Skybox.Type_( new_index )

                # update, regular skybox cubemaps probably allocates a new cubemap still ..
                self.context.loadDefaultEnvironment()

 
            # ambient
            changed, scene["ambient_color"] = imgui.color_edit3(
                "Ambient color", scene["ambient_color"]
            )

            imgui.separator()

            # procedural settings
            if scene["sky_type"] == Skybox.Type_.procedural:
                if imgui.tree_node_ex( f"{fa.ICON_FA_CUBE} Procedural Skybox", imgui.TreeNodeFlags_.default_open ):
                    _, self.context.skybox.realtime = imgui.checkbox( f"Realtime", self.context.skybox.realtime )
                    imgui.set_item_tooltip("Realtime OR generated cubemap (rebuilt when sky changes)")

                    any_changed = False
                   
                    changed, scene["procedural_sky_color"] = imgui.color_edit3(
                        "Sky color", scene["procedural_sky_color"]
                    )
                    if changed:
                        any_changed = True

                    changed, scene["procedural_horizon_color"] = imgui.color_edit3(
                        "Horizon color", scene["procedural_horizon_color"]
                    )
                    if changed:
                        any_changed = True

                    changed, scene["procedural_ground_color"] = imgui.color_edit3(
                        "Ground color", scene["procedural_ground_color"]
                    )
                    if changed:
                        any_changed = True

                    changed, scene["procedural_sunset_color"] = imgui.color_edit3(
                        "Sunset color", scene["procedural_sunset_color"]
                    )
                    if changed:
                        any_changed = True

                    changed, scene["procedural_night_brightness"] = imgui.drag_float(
                        f"Night intensity", scene["procedural_night_brightness"], 0.01
                    )
                    if changed:
                        any_changed = True

                    changed, scene["procedural_night_color"] = imgui.color_edit3(
                        "Night color", scene["procedural_night_color"]
                    )
                    if changed:
                        any_changed = True

                    # update skybox (cubemap)
                    if any_changed:
                        self.context.skybox.procedural_cubemap_update = True

                    imgui.tree_pop()


            # skybox IBL debug
            self._skybox_preview( scene )

            imgui.separator()

        def render( self ) -> None:
            imgui.begin( "Scene" )
            _scene = self.scene.getCurrentScene()

            self._camera_selector()
            self._sun_selector()
            self._sky_settings( _scene )

            imgui.end()

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
        class RotationMode_(enum.IntEnum):
            """Modes to visualize rotation angles"""
            radians = enum.auto()
            degrees = enum.auto()

        def __init__( self, context ):
            super().__init__( context )

            self.rotation_mode = self.RotationMode_.degrees

        def _transform( self ) -> None:
            if not self.context.gui.selectedObject:
                return

            gameObject  : GameObject    = self.context.gui.selectedObject
            _t          : Transform     = gameObject.transform

            if isinstance( gameObject, Mesh ):
                imgui.text( f"Mesh" );

            if isinstance( gameObject, Light ):
                imgui.text( f"Light" );

            # todo:
            # switch from local to world space editing using viewport gizmo mode?

            # local space
            if imgui.tree_node_ex( f"{fa.ICON_FA_CUBE} Transform local", imgui.TreeNodeFlags_.default_open ):
                # position
                self.context.gui.draw_vec3_control( "Position", _t.local_position, 0.0 )

                # rotation
                match self.rotation_mode:
                    case self.RotationMode_.degrees:
                        self.context.gui.draw_vec3_control(
                            "Rotation", Transform.vec_to_degrees( _t.local_rotation ), 0.0,
                            onChange=lambda v: _t.set_local_rotation( Transform.vec_to_radians( v ) )
                        )
                    case self.RotationMode_.radians:
                        self.context.gui.draw_vec3_control("Rotation", _t.local_rotation, 0.0)

                # scale
                self.context.gui.draw_vec3_control( "Scale", _t.local_scale, 0.0 )

                imgui.tree_pop()

            # world space --should b hidden or disabled?
            if imgui.tree_node_ex( f"{fa.ICON_FA_CUBE} Transform world", imgui.TreeNodeFlags_.default_open ):
                # position
                self.context.gui.draw_vec3_control( "Position", _t.position, 0.0 )

                # rotation
                match self.rotation_mode:
                    case self.RotationMode_.degrees:
                        self.context.gui.draw_vec3_control( "Rotation", Transform.vec_to_degrees( _t.rotation ), 0.0,
                            onChange = lambda v: _t.set_rotation( Transform.vec_to_radians( v ) )
                        )
                    case self.RotationMode_.radians:
                        self.context.gui.draw_vec3_control( "Rotation", _t.rotation, 0.0 )

                # scale
                self.context.gui.draw_vec3_control( "Scale", _t.scale, 0.0 )

                imgui.tree_pop()

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

        def _draw_script_exported_attributes( self, script: Script ):
            if not script.active:
                return 

            imgui.dummy( imgui.ImVec2(20, 0) )

            for class_attr_name, class_attr in script.exports.items():
                # at this point, the effective value 'default' or '.get()' has already been initialized (from class or scene)

                # shuldnt this be at the beginning?
                if script.instance is None:
                    continue

                # exported attribute contains error, type mismatch?
                if not class_attr.active:
                    continue

                #_instance_value = getattr(script["instance"], instance_attr_name)
                _value = class_attr.get()
                _t = class_attr.type
                _changed = False
                _t_engine_type : EngineTypes.Meta = EngineTypes.get_engine_type( _t )

                # FLOAT
                if _t is float:
                    _changed, new = imgui.drag_float(f"{class_attr_name}:", _value, 0.01)

                # INT
                elif _t is int:
                    _changed, new = imgui.drag_int(f"{class_attr_name}:", _value, 1)

                # STRING
                elif _t is str:
                    _changed, new = imgui.input_text(f"{class_attr_name}:", _value, 256)

                # BOOL
                elif _t is bool:
                    _changed, new = imgui.checkbox(f"{class_attr_name}:", _value)

                # ENGINE TYPE
                elif _t_engine_type is not None:
                    _uuid               : uid.UUID = None

                    obj     : GameObject = self.context.findGameObject(_value)
                    _name   : str = obj.name if obj is not None else "Select"

                    imgui.text( f"{_t.__name__}: {class_attr_name}")
                    imgui.same_line(200.0)

                    if imgui.button( f"{_name}##{class_attr_name}" ):
                        imgui.open_popup(f"##{class_attr_name}_select")

                    # dnd: receive
                    if imgui.begin_drag_drop_target():
                        payload = imgui.accept_drag_drop_payload_py_id(self.context.gui.dnd_payload.Type_.hierarchy)
                        if payload is not None:
                            payload_obj : GameObject = self.context.gui.dnd_payload.get_payload_data()
                            new = payload_obj.uuid
                            _changed = True

                        imgui.end_drag_drop_target()

                    else:
                        _changed, new = self.context.gui.draw_popup_gameObject(
                            f"##{class_attr_name}_select", filter=lambda obj: isinstance(obj, GameObject ))

                # Unsupported type
                else:
                    imgui.text(f"{class_attr_name}: <unsupported {_t.__name__}>")

                if _changed:
                    # engine type (uuid)
                    if _t_engine_type is not None:
                        new_obj : GameObject = self.context.findGameObject( new )

                        if new_obj is None:
                            self.console.error( "gameObject is invalid.")
                            return

                        # set the UUID as the experted meta value
                        class_attr.set( new )
                        
                        # get the engine type (Transform, GameObject, etc) and set reference on instance attribute
                        _ref = new_obj.getAttachable( _t_engine_type._name )
                        setattr( script.instance, class_attr_name, _ref )

                    # primitive types are a COPY
                    else:
                        class_attr.set( new )
                        setattr( script.instance, class_attr_name, new )

        def _draw_script( self, script: Script ) -> None:
            _shift_left = 20.0
            _region = imgui.get_content_region_avail()
            _region = imgui.ImVec2(_region.x + _shift_left, _region.y)

            imgui.push_id( f"{script.uuid}" )

            if not imgui.tree_node_ex( f"{fa.ICON_FA_CODE} {script.class_name_f} (Script)##GameObjectScript", imgui.TreeNodeFlags_.default_open ):
                imgui.pop_id()
                return

            # actions
            if not self.renderer.game_runtime: 
                imgui.same_line()

                if self.context.gui.draw_trash_button( f"{fa.ICON_FA_TRASH}", _region.x - 20 ):
                    self.context.gui.selectedObject.removeScript( script )

                if self.context.gui.draw_edit_button( f"{fa.ICON_FA_PEN_TO_SQUARE}", _region.x - 40 ):
                    self.context.gui.text_editor.open_file( script.path )
            
            # draw uuid
            imgui.text_colored( imgui.ImVec4(1.0, 1.0, 1.0, 0.6), f"uuid: { script.uuid.hex }" );

            active_changed, active_state = imgui.checkbox( "Active", script.active )
            if active_changed:
                script.active = active_state
                self.scene.updateScriptonGameObjects( script.path )


            # script contains errors, return
            if script._error:
                imgui.text_colored( imgui.ImVec4(1.0, 0.0, 0.0, 0.9), script._error );
                imgui.dummy( imgui.ImVec2(20, 0) )
                imgui.tree_pop()
                imgui.pop_id()
                return

            draw_list = imgui.get_window_draw_list() 
            draw_list.channels_split(2)
            draw_list.channels_set_current(1)

            p_min = imgui.get_cursor_screen_pos()
            p_min = imgui.ImVec2( (p_min.x-_shift_left), p_min.y)
            imgui.set_cursor_screen_pos(p_min)
                
            imgui.begin_group()
            imgui.text_colored( imgui.ImVec4(1.0, 1.0, 1.0, 0.6), str(script.path) );
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
  
            # exported attributes
            self._draw_script_exported_attributes(script)

            imgui.dummy( imgui.ImVec2(20, 0) )
            imgui.tree_pop()

            imgui.pop_id()

        def _scripts( self ):
            assets = Path( self.settings.assets ).resolve()

            if len(self.context.gui.selectedObject.scripts) == 0:
                imgui.text("No scripts attached")
                return

            for script in self.context.gui.selectedObject.scripts:
                self._draw_script( script )
                imgui.separator()

        def _addAttachable( self ):
            if self.renderer.game_runtime: 
                return

            script_path = None
            attachable_type = None

            _tree_flags =   imgui.TreeNodeFlags_.default_open | \
                            imgui.TreeNodeFlags_.leaf | \
                            imgui.TreeNodeFlags_.span_full_width

            if not imgui.tree_node_ex( f"##AddAttachable", _tree_flags ):
                return

            _region_x = imgui.get_content_region_avail().x
            button_text = "Add Attachable"
            button_width = imgui.calc_text_size(button_text).x + imgui.get_style().frame_padding.x * 2
            
            offset = (_region_x - button_width ) * 0.5
            imgui.set_cursor_pos_x(imgui.get_cursor_pos_x() + offset)

            if imgui.button( button_text ):
                imgui.open_popup("add-attachable-popup")

            # dnd: receive
            if imgui.begin_drag_drop_target():
                is_asset = imgui.accept_drag_drop_payload_py_id(self.context.gui.dnd_payload.Type_.asset)
                if is_asset is not None:
                    script_path = self.context.gui.dnd_payload.get_payload_data()

                imgui.end_drag_drop_target()

            imgui.same_line()

            if imgui.begin_popup("add-attachable-popup"):

                # todo:
                # perhaps there should be a separate thread for this
                # that either updates periodicly, or tracks changes in assets folder
                self.context.findScripts()

                # engine attachables
                attachables : list[EngineTypes.Meta] = EngineTypes.getAttachables()

                for attachable in attachables:
                    imgui.push_id(f"addAttachable_{attachable._name}")
                    _, clicked = imgui.selectable(
                        f"{attachable._name}", False
                    )

                    if clicked:
                        attachable_type = attachable

                    imgui.pop_id()

                imgui.separator()

                # project assets scripts
                assets = Path( self.settings.assets ).resolve()
                for i, script in enumerate(self.context.asset_scripts):
                    imgui.push_id(f"add_script_{str(script)}")
 
                    name = str(script.relative_to(assets))
                    _, clicked = imgui.selectable(
                        f"{name}", False
                    )

                    if clicked:
                        script_path = script

                    imgui.pop_id()

                imgui.end_popup()

            if script_path:
                self.context.gui.selectedObject.addScript( 
                    Script( 
                        context = self.context,
                        path    = script_path,
                        active  = True
                    )   
                )

            if attachable_type:
                self.context.gui.selectedObject.addAttachable( attachable_type._class, attachable_type._class(
                       self.context, 
                       self.context.gui.selectedObject ) 
                )

            imgui.tree_pop()

        def _light( self ) -> None:
            if not self.context.gui.selectedObject:
                return
            
            gameObject = self.context.gui.selectedObject

            if not isinstance( gameObject, Light ):
                return

            if imgui.tree_node_ex( f"{fa.ICON_FA_LIGHTBULB} Light", imgui.TreeNodeFlags_.default_open ):

                type_names = [t.name for t in Light.Type_]

                changed, new_light_index = imgui.combo(
                    "Light type",
                    gameObject.light_type,
                    type_names
                )
                if changed:
                    gameObject.light_type = Light.Type_(new_light_index)

                changed, gameObject.light_color = imgui.color_edit3(
                    "Light color", gameObject.light_color
                )

                changed, gameObject.radius = imgui.drag_float(
                    f"Radius", gameObject.radius, 0.1
                )

                changed, gameObject.intensity = imgui.drag_float(
                    f"Intensity", gameObject.intensity, 0.1
                )

                imgui.separator()
                imgui.tree_pop()

        def _camera( self ) -> None:
            if not self.context.gui.selectedObject:
                return
            
            gameObject = self.context.gui.selectedObject

            if not isinstance( gameObject, Camera ):
                return

            if imgui.tree_node_ex( f"{fa.ICON_FA_CAMERA} Camera properties", imgui.TreeNodeFlags_.default_open ):
                changed, value = imgui.drag_float(
                    f"Fov", gameObject.fov, 1
                )
                if changed:
                    gameObject.fov = value

                changed, value = imgui.drag_float(
                    f"Near", gameObject.near, 1
                )
                if changed:
                    gameObject.near = value

                changed, value = imgui.drag_float(
                    f"Far", gameObject.far, 1
                )
                if changed:
                    gameObject.far = value

                imgui.separator()
                imgui.tree_pop()

        def _physic( self ) -> None:
            if not self.context.gui.selectedObject:
                return
            
            gameObject = self.context.gui.selectedObject

            if Physic not in gameObject.attachables:
                return

            physic : Physic = gameObject.getAttachable(Physic)

            if imgui.tree_node_ex( f"{fa.ICON_FA_PERSON_FALLING_BURST} Physics Base", imgui.TreeNodeFlags_.default_open ):
                imgui.text("This is where joints are created")

                _, physic.base_mass = imgui.drag_float("Base Mass", physic.base_mass, 1.0)

                for link in physic.physics_links:
                    imgui.text( link.gameObject.name )

                imgui.separator()
                imgui.tree_pop()

        def _physicLink( self ) -> None:
            # inspiration:
            # https://tobas-wiki.readthedocs.io/en/latest/create_urdf/

            if not self.context.gui.selectedObject:
                return
            
            gameObject = self.context.gui.selectedObject

            if PhysicLink not in gameObject.attachables:
                return

            physic : PhysicLink = gameObject.getAttachable(PhysicLink)
  
            if imgui.tree_node_ex( f"{fa.ICON_FA_PERSON_FALLING_BURST} Physic", imgui.TreeNodeFlags_.default_open ):

                imgui.push_id("##PhysicTabs")
                _flags = imgui.TabBarFlags_.none

                if imgui.begin_tab_bar( "PhysicProperties", _flags ):
                    if imgui.begin_tab_item("Inertia##Tab1")[0]:
                        inertia : PhysicLink.Inertia = physic.inertia

                        _, inertia.mass = imgui.drag_float("Mass", inertia.mass, 1.0)
                        imgui.end_tab_item()

                    if imgui.begin_tab_item("Joint##Tab2")[0]:
                        joint : PhysicLink.Joint = physic.joint

                        active_changed, active_state = imgui.checkbox( "Active", joint.active )
                        if active_changed:
                            joint.active = active_state

                        # name
                        _, joint.name = imgui.input_text("Name##JointName", joint.name)

                        # type
                        type_names = [t.name for t in PhysicLink.Joint.Type_]

                        changed, new_index = imgui.combo(
                            "Joint type",
                            joint.type,
                            type_names
                        )
                        if changed:
                            joint.type = PhysicLink.Joint.Type_( new_index )

                        # begin parent
                        imgui.push_id( f"physic_join_selector" )

                        changed : bool = False
                        _uuid   : uid.UUID = None

                        _parent : GameObject = joint.getParent()
                        _parent_name : str = _parent.name if _parent else "None" 

                        if imgui.button( _parent_name):
                            imgui.open_popup("##select_parent")

                        # dnd: receive
                        if imgui.begin_drag_drop_target():
                            payload = imgui.accept_drag_drop_payload_py_id(self.context.gui.dnd_payload.Type_.hierarchy)
                            if payload is not None:
                                payload_obj : GameObject = self.context.gui.dnd_payload.get_payload_data()
                                _uuid = payload_obj.uuid
                                changed = True

                            imgui.end_drag_drop_target()

                        else: 
                            changed, _uuid = self.context.gui.draw_popup_gameObject(
                                "##select_parent", filter=lambda obj: isinstance(obj, GameObject ))

                        if changed:
                            joint.setParent( _uuid )

                        imgui.pop_id()
                        # end parent

                        imgui.end_tab_item()

                    # End tab bar
                    imgui.end_tab_bar()

                imgui.separator()
                imgui.pop_id()

                imgui.tree_pop()

        def render( self ) -> None:
            imgui.begin( "Inspector" )
  
            if not self.context.gui.selectedObject:
                imgui.end()
                return

            gameObject = self.context.gui.selectedObject

            if isinstance( gameObject, GameObject ):
                # draw uuid
                imgui.text_colored( imgui.ImVec4(1.0, 1.0, 1.0, 0.6), f"uuid: { gameObject.uuid.hex }" );
                
                active_changed, active_state = imgui.checkbox( "Active", gameObject.active )
                if active_changed:
                    gameObject.active = active_state

                _, _ = imgui.checkbox( "Active Parent", gameObject.hierachyActive() )

                _, gameObject.name = imgui.input_text("Name##ObjectName", gameObject.name)

                self._transform()
                imgui.separator()

                self._camera()
                self._light()
                self._physic()
                self._physicLink()

                self._material()
                imgui.separator()

                self._scripts()
                imgui.separator()

                self._addAttachable()

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
            # model
            if path.suffix in self.settings.MODEL_EXTENSION:
                game_object_name = path.name.replace(path.suffix, "")
                self.context.addGameObject( 
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

            self.save_as_name : str = "Scene Name"

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