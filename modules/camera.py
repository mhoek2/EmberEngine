from pyrr import Vector3, vector, vector3, matrix44, Matrix44
from math import atan2, asin, sin, cos, radians, degrees
import pygame

from modules.settings import Settings
from modules.scene import SceneManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine

class Camera:
    def __init__( self, context ):
        """This class is responsible for creating the viewmatrix,
        Based on what camera is active, either from scene or editor

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        self.context    : 'EmberEngine' = context
        self.settings   : Settings      = context.settings
        self.scene      : SceneManager  = context.scene

        self.camera_pos     = Vector3([0.0, 1.0, 5.0])
        self.camera_front   = Vector3([0.0, 0.0, -1.0])
        self.camera_up      = Vector3([0.0, 1.0, 0.0])
        self.camera_right   = Vector3([1.0, 0.0, 0.0])

        self.mouse_sensitivity = 0.25
        self.jaw = -90
        self.pitch = 0

    def place_object_in_front_of_another( self, position, rotation_quat, distance ) -> Vector3:
        """-This should become a scriptable function perhaps

        :param position: The position of the parent object
        :type position: Vector3
        :param rotation: The rotation of the parent object
        :type rotation: Vector3
        :param distance: The distance the object is placed from the parent on the Z-axis
        :type distance: float
        :return: The position of an object placed in front of another object along the Z-axis at a defined distance
        :rtype: Vector3
        """
        rotation_matrix = Matrix44.from_quaternion(rotation_quat)
        forward_vector = rotation_matrix * Vector3([0, 0, 1]) # forward is along the Z-axis
        return position + forward_vector * distance

    def get_view_matrix_running( self ) -> Matrix44:
        """Get the view matrix from the camera gameObject when the game is running.
        Do this by placing an object in front of the cameras direction, and use lookAt.

        :return: The viewmatrix from the active Camera gameobject, return Identity when no camera
        :rtype: matrix44 or Matrix44
        """
        camera = self.scene.getCamera()

        if not camera:
            return Matrix44.identity()

        camera_rotation = Matrix44.from_quaternion(camera.transform._local_rotation_quat)
        up = camera_rotation * Vector3([0.0, 1.0, 0.0])

        target = self.place_object_in_front_of_another( camera.transform._local_position, camera.transform._local_rotation_quat, 10.0 )

        return matrix44.create_look_at(camera.transform._local_position, target, up)

    def get_view_matrix( self ):
        """Get the current view matrix, based on if game is running,
        switch between editor and scene camera

        :return: The viewmatrix from the current active camera
        :rtype: matrix44 or Matrix44
        """
        if self.settings.game_running:
            return self.get_view_matrix_running()
 
        # return editor camera
        return matrix44.create_look_at(self.camera_pos, self.camera_pos + self.camera_front, self.camera_up)

    def update_yaw_pitch_from_front( self ):
        """Update jaw (yaw) and pitch based on current camera_front"""
        front = Vector3(vector.normalise(self.camera_front))

        self.pitch = degrees(asin(front.y))
        self.jaw = degrees(atan2(front.z, front.x))

    def process_mouse_movement( self, constrain_pitch : float = 89.5 ):
        """Handle mouse events for the editor camera, with constraints and sensitivity bias.

        :param constrain_pitch: Enable to contraint the pitch to 45degrees both directions
        :type constrain_pitch: bool
        """
        xoffset, yoffset = self.context.mouse.get_rel()

        if self.context.renderer.ImGuiInputFocussed:
            """Input state changed, dont process mouse movement on the first """
            self.context.renderer.ImGuiInputFocussed = False
            return

        xoffset *= self.mouse_sensitivity
        yoffset *= self.mouse_sensitivity

        self.jaw += xoffset
        self.pitch += -yoffset

        if constrain_pitch:
            if self.pitch > constrain_pitch:
                self.pitch = constrain_pitch
            if self.pitch < -constrain_pitch:
                self.pitch = -constrain_pitch

        self.update_camera_vectors()

    def update_camera_vectors( self ):
        """Convert radians to camera axis for editor camera"""
        front = Vector3([0.0, 0.0, 0.0])
        front.x = cos(radians(self.jaw)) * cos(radians(self.pitch))
        front.y = sin(radians(self.pitch))
        front.z = sin(radians(self.jaw)) * cos(radians(self.pitch))

        self.camera_front = vector.normalise(front)
        self.camera_right = vector.normalise(vector3.cross(self.camera_front, Vector3([0.0, 1.0, 0.0])))
        self.camera_up = vector.normalise(vector3.cross(self.camera_right, self.camera_front))

    def process_keyboard( self ):
        """Handle key events for the editor camera"""
        keypress = self.context.key.get_pressed()
        velocity : float = 0.05;

        if keypress[pygame.K_LCTRL] or keypress[pygame.K_RCTRL]:
            velocity *= 30

        if keypress[pygame.K_w]:
            self.camera_pos += self.camera_front * velocity
        if keypress[pygame.K_s]:
            self.camera_pos -= self.camera_front * velocity
        if keypress[pygame.K_a]:
            self.camera_pos -= self.camera_right * velocity
        if keypress[pygame.K_d]:
            self.camera_pos += self.camera_right * velocity

    def new_frame( self ):
        """Called on beginning of a frame, trigger keyboard and mouse processing when in editor mode"""
        if not self.context.renderer.ImGuiInput and not self.settings.game_running:
            self.context.camera.process_keyboard()
            self.context.camera.process_mouse_movement()
















