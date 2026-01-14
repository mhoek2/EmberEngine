from OpenGL.GL import *  # pylint: disable=W0614
from OpenGL.GLU import *

from typing import TYPE_CHECKING

from modules.context import Context
from gameObjects.attachables.transform import Transform

from gameObjects.gameObject import GameObject

from pyrr import Matrix44, Vector3
import numpy as np

from imgui_bundle import imgui
from imgui_bundle import imguizmo
from imgui_bundle import icons_fontawesome_6 as fa

if TYPE_CHECKING:
    from main import EmberEngine

from modules.gui.types import RadioStruct

class ImGuizmo( Context ):
    """Logic related to rendering the Hierarchy window"""
    def __init__( self, context : 'EmberEngine' ):
        super().__init__( context )
        self.gui        = context.gui
        self.helper     = context.gui.helper

        self.gizmo : imguizmo.im_guizmo = imguizmo.im_guizmo

        self.operation      : int   = 0
        self.mode           : int   = 0

        self.mode_types : list[RadioStruct] = [
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

        self.operation_types : list[RadioStruct] = [
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
                "hide"  : lambda: self.gameObject_is_physic
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

        self.gameObject_is_physic = self.gui.selectedObject and self.gui.selectedObject.get_physic()

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
        if self.gui.selectedObject:
            gameObject = self.gui.selectedObject
            _t          : Transform     = gameObject.transform

            model_m16 = self.to_matrix16(_t._getModelMatrix())

            glEnable(GL_DEPTH_TEST)
            glDepthFunc(GL_LEQUAL)

            _draw_manipulate = True

            if self.operation_types[self.operation]["flag"] == self.gizmo.OPERATION.scale and self.gameObject_is_physic:
                _draw_manipulate = False

            if _draw_manipulate:
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
