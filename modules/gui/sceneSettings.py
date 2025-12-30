from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

from typing import TYPE_CHECKING

from modules.context import Context
from modules.scene import SceneManager

from gameObjects.gameObject import GameObject
from gameObjects.mesh import Mesh
from gameObjects.camera import Camera
from gameObjects.skybox import Skybox

from imgui_bundle import imgui
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

import uuid as uid

class SceneSettings( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper

        self.test_cubemap_initialized = False

        self.test_cubemap = None
        self.test_cubemap_update = True

    def _camera_selector( self ) -> None:
        imgui.text("Scene Camera")
        imgui.same_line(150.0)

        changed : bool = False
        _uuid   : uid.UUID = None

        _camera : GameObject = self.scene.getCamera()
        _camera_name : str = _camera.name if _camera else "None" 

        imgui.push_id( f"gui_camera_selected" )

        if imgui.button( _camera_name ):
            imgui.open_popup("##select_camera")

        # dnd: receive
        if imgui.begin_drag_drop_target():
            payload = imgui.accept_drag_drop_payload_py_id(self.gui.dnd_payload.Type_.hierarchy)
            if payload is not None:
                payload_obj : GameObject = self.gui.dnd_payload.get_payload_data()
                _uuid = payload_obj.uuid
                changed = True

            imgui.end_drag_drop_target()

        else: 
            changed, _uuid = self.helper.draw_popup_gameObject(
                "##select_camera", filter=lambda obj: isinstance(obj, Camera ))

        if changed:
            self.scene.setCamera( _uuid )

        imgui.pop_id()

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
            payload = imgui.accept_drag_drop_payload_py_id(self.gui.dnd_payload.Type_.hierarchy)
            if payload is not None:
                payload_obj : GameObject = self.gui.dnd_payload.get_payload_data()
                _uuid = payload_obj.uuid
                changed = True

            imgui.end_drag_drop_target()

        else: 
            changed, _uuid = self.helper.draw_popup_gameObject(
                "##select_sun", filter=lambda obj: isinstance(obj, GameObject ))

        if changed:
            self.scene.setSun( _uuid )
        


        imgui.pop_id()

    def _procedural_skybox_preview( self, scene : SceneManager.Scene ) -> None:
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

        self.helper._node_sep()
        if imgui.tree_node_ex( f"{fa.ICON_FA_LAYER_GROUP} Skybox preview", 0 ):
            self.helper._node_header_pad()

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
        self.helper._node_sep()
        if imgui.tree_node_ex( f"{fa.ICON_FA_CLOUD_MOON} Environment", imgui.TreeNodeFlags_.default_open ):
            self.helper._node_header_pad()

            self._sun_selector()

            _, scene["shadowmap_enabled"] = imgui.checkbox( f"Sun shadows", scene["shadowmap_enabled"] )

            self.helper._node_sep()

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
            changed, ambient = imgui.color_edit3(
                "Ambient color", scene["ambient_color"]
            )
            if changed:
                scene["ambient_color"] = ambient

            # procedural settings
            if scene["sky_type"] == Skybox.Type_.procedural:

                self.helper._node_sep()
                if imgui.tree_node_ex( f"{fa.ICON_FA_PALETTE} Procedural Skybox", imgui.TreeNodeFlags_.default_open ):
                    self.helper._node_header_pad()

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

                self._procedural_skybox_preview( scene )
            
            imgui.tree_pop()

    def _fog_settings( self, scene : SceneManager.Scene ) -> None:
        self.helper._node_sep()
        if imgui.tree_node_ex( f"{fa.ICON_FA_CLOUD_MOON} Fog", imgui.TreeNodeFlags_.default_open ):
            self.helper._node_header_pad()

            _, scene["fog_enabled"] = imgui.checkbox( f"Enable Fog", scene["fog_enabled"] )

            _, scene["fog_color"] = imgui.color_edit3(
                "Fog color", scene["fog_color"]
            )

            _, scene["fog_density"] = imgui.drag_float(
                f"Fog density", scene["fog_density"], 0.001
            )

            _, scene["fog_height"] = imgui.drag_float(
                f"Fog height", scene["fog_height"], 0.001
            )

            _, scene["fog_falloff"] = imgui.drag_float(
                f"Fog falloff", scene["fog_falloff"], 0.001
            )

            imgui.tree_pop()

    def _general_settings( self, scene : SceneManager.Scene ) -> None:
        if imgui.tree_node_ex( f"{fa.ICON_FA_SLIDERS} General", imgui.TreeNodeFlags_.default_open ):
            self.helper._node_header_pad()
            
            self._camera_selector()

            imgui.tree_pop()

    def render( self ) -> None:
        imgui.begin( "Scene" )
        _scene = self.scene.getCurrentScene()

        self._general_settings( _scene )
        self._sky_settings( _scene )
        self._fog_settings( _scene )

        imgui.end()