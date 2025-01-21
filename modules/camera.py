from pyrr import Vector3, vector, vector3, matrix44, Matrix44
from math import sin, cos, radians

from modules.settings import Settings
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine

class Camera:
    def __init__( self, context ):
        self.context    : 'EmberEngine' = context
        self.settings   : Settings = context.settings

        self.camera_pos = Vector3([0.0, 1.0, 5.0])
        self.camera_front = Vector3([0.0, 0.0, -1.0])
        self.camera_up = Vector3([0.0, 1.0, 0.0])
        self.camera_right = Vector3([1.0, 0.0, 0.0])

        self.mouse_sensitivity = 0.25
        self.jaw = -90
        self.pitch = 0

    def update_camera_pos( self, pos, p, y, r ):
        self.camera_pos = pos
        self.pitch = p
        self.jaw = y
        self.update_camera_vectors()

    def get_view_matrix_running(self) -> Matrix44:
        """Get the view matrix from the camera gameObject"""
        camera = self.context.gameObjects[self.context.camera_object]
            
        camera_rotation = Matrix44.from_eulers(Vector3([camera.rotation[0], camera.rotation[1], -camera.rotation[2]]))
        camera_translation = Matrix44.from_translation(Vector3([camera.translate[0], -camera.translate[1], camera.translate[2]]))

        return camera_rotation * camera_translation;

    def get_view_matrix(self):
        """Get the current view matrix, based on if game is running,
        switch between editor and scene camera"""
        if self.settings.game_running:
            return self.get_view_matrix_running()
 
        # return editor camera
        return matrix44.create_look_at(self.camera_pos, self.camera_pos + self.camera_front, self.camera_up)

    def process_mouse_movement(self, xoffset, yoffset, constrain_pitch=True):
        xoffset *= self.mouse_sensitivity
        yoffset *= self.mouse_sensitivity

        self.jaw += xoffset
        self.pitch += yoffset

        if constrain_pitch:
            if self.pitch > 45:
                self.pitch = 45
            if self.pitch < -45:
                self.pitch = -45

        self.update_camera_vectors()

    def update_camera_vectors(self):
        front = Vector3([0.0, 0.0, 0.0])
        front.x = cos(radians(self.jaw)) * cos(radians(self.pitch))
        front.y = sin(radians(self.pitch))
        front.z = sin(radians(self.jaw)) * cos(radians(self.pitch))

        self.camera_front = vector.normalise(front)
        self.camera_right = vector.normalise(vector3.cross(self.camera_front, Vector3([0.0, 1.0, 0.0])))
        self.camera_up = vector.normalise(vector3.cross(self.camera_right, self.camera_front))

    # Camera method for the WASD movement
    def process_keyboard(self, direction, velocity):
        if direction == "FORWARD":
            self.camera_pos += self.camera_front * velocity
        if direction == "BACKWARD":
            self.camera_pos -= self.camera_front * velocity
        if direction == "LEFT":
            self.camera_pos -= self.camera_right * velocity
        if direction == "RIGHT":
            self.camera_pos += self.camera_right * velocity
















