from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

from modules.context import Context
from modules.material import Materials
from modules.images import Images
from modules.models import Models
from modules.console import Console
from modules.scene import SceneManager
from gameObjects.attachables.transform import Transform
from modules.script import Script
from modules.engineTypes import EngineTypes

from gameObjects.gameObject import GameObject

from pathlib import Path
import uuid as uid

# Gui modules
from modules.gui.helper import Helper
from modules.gui.types import DragAndDropPayload

from modules.gui.hierarchy import Hierarchy
from modules.gui.inspector import Inspector
from modules.gui.imGuizmo import ImGuizmo
from modules.gui.consoleWindow import ConsoleWindow
from modules.gui.assetBrowser import AssetBrowser
from modules.gui.textEditor import TextEditor
from modules.gui.project import Project
from modules.gui.sceneSettings import SceneSettings
from modules.gui.viewport import Viewport
from modules.gui.rendererInfo import RendererInfo

import pybullet as p

class UserInterface( Context ):

    def __init__( self, context ):
        super().__init__( context )
        
        self.initialized    : bool = False
        self.io             : imgui.IO = imgui.get_io()

        self.drawWireframe          : bool = False
        self.selectedObject         : GameObject = None

        self.status_bar_height      : float = 25.0

        self.color_button_trash : list[imgui.ImVec4] = [
            imgui.ImVec4(1.0, 0.0, 0.0, 0.6),   # default   
            imgui.ImVec4(1.0, 0.0, 0.0, 1.0)    # hover
        ]

        self.color_button_edit_ide : list[imgui.ImVec4] = [
            imgui.ImVec4(0.988, 0.729, 0.012, 0.6),   # default   
            imgui.ImVec4(0.988, 0.729, 0.012, 1.0)    # hover
        ]

        self.color_visibility : list[imgui.ImVec4] = [
            imgui.ImVec4(1.0, 1.0, 1.0, 0.2),   # default   
            imgui.ImVec4(1.0, 1.0, 1.0, 1.0)    # hover
        ]

        self.visibility_icon : list = [
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

        # helpers
        self.helper : Helper = Helper( self.context )

        # user inferface modules
        self.console_window : ConsoleWindow     = ConsoleWindow( self.context )
        self.asset_browser  : AssetBrowser      = AssetBrowser( self.context )
        self.text_editor    : TextEditor        = TextEditor( self.context )
        self.project        : Project           = Project( self.context )
        self.inspector      : Inspector         = Inspector( self.context )
        self.hierarchy      : Hierarchy         = Hierarchy( self.context )
        self.guizmo         : ImGuizmo          = ImGuizmo( self.context )
        self.scene_settings : SceneSettings     = SceneSettings( self.context )
        self.viewport       : Viewport          = Viewport( self.context )
        self.renderer_info  : RendererInfo      = RendererInfo( self.context )

        # drag and drop
        self.dnd_payload    : DragAndDropPayload = DragAndDropPayload()

        self.initialized = True

    def set_selected_object( self, obj : GameObject = None ):
        self.selectedObject = obj

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
        _open_save_scene_as_modal   = False
        _open_new_scene_modal       = False
        _open_project_settings      = False
        _open_renderer_info      = False

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
    
                if imgui.menu_item( "Renderer info", '', False, True )[0]:
                    _open_renderer_info = True

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

            if _open_renderer_info:
                imgui.open_popup("Renderer Info")

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

    def draw_settings( self ) -> None:
        imgui.begin( "Settings" )

        #_, self.settings.grid_color = ImGuiHelpers.color_edit3_safe("Grid color", self.settings.grid_color)

        # deprecated (26-12-2025)
        # need to rebuild vao, however this was mostly for debugging purposes
        #_, self.settings.grid_size = imgui.drag_float(
        #    f"Grid size", self.settings.grid_size, 1
        #)
        #
        #_, self.settings.grid_spacing = imgui.drag_float(
        #    f"Grid spacing", self.settings.grid_spacing, 0.01
        #)
        #
        #imgui.separator()

        _, self.context.roughnessOverride = imgui.drag_float(
            f"Roughness override", self.context.roughnessOverride, 0.01
        )

        _, self.context.metallicOverride = imgui.drag_float(
            f"Metallic override", self.context.metallicOverride, 0.01
        )

        imgui.end()
        return

    def render( self ):
        # init
        self.initialize_context()

        # debug print version
        # print(imgui.get_version())

        # exported apps draw directly
        if self.settings.is_exported:
            self.viewport.render_exported()

        # draw engine GUI
        else:
            self.docking_space('docking_space')
        
            self.draw_menu_bar()
            self.draw_status_bar()

            # windows
            self.viewport.render()
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
            self.renderer_info.render()