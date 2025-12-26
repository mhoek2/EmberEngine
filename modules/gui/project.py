from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

from typing import TYPE_CHECKING, Callable

from modules.context import Context

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

from pathlib import Path
import re
import uuid as uid

class Project( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper

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

            if self.helper.draw_close_button( f"{fa.ICON_FA_CIRCLE_XMARK}", imgui.get_window_width() - 30 ):
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