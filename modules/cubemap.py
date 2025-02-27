from pathlib import Path

from OpenGL.GL import *
from OpenGL.GLU import *

from modules.imageLoader import load_image_pygame as load_image
from modules.imageLoader import create_image_pygame as create_image
from modules.imageLoader import load_cubemap_pygame as load_cubemap
from modules.context import Context

import numpy as np

class Cubemap( Context ):
    def __init__( self, context ):
        """Cubemap loader class, which loads cubemaps and sets up IBL requirements like BRDF lut
        
        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )

        self.cubemap = glGenTextures(30)
        self._num_cubemaps = 0;

        basepath = self.settings.cubemap_path

        # BRDF Lut
        self.create_brdf_lut()

        return

    @staticmethod
    def create_brdf_texture( size : int ):
        """Create the BRDF lut used for IBL contributions - Currently unused
        
        :param size: the dimension of the LUT, required to calculate each pixel
        :type size: int
        """
        brdf_texture = np.zeros((size, size, 4), dtype=np.float32)

        for i in range( size ):
            for j in range(size):
                print(f"Processing incident angle index: {i}, reflection angle index: {j}")  # Debug statement

                # Calculate theta and phi from i and j
                theta_i = np.pi * (i + 0.5) / size  # incident angle (0 to pi)
                phi_i = 2 * np.pi * (j + 0.5) / size  # incident azimuthal angle (0 to 2pi)

                # Convert spherical coordinates to Cartesian coordinates
                wi = np.array([
                    np.sin(theta_i) * np.cos(phi_i),
                    np.cos(theta_i),
                    np.sin(theta_i) * np.sin(phi_i)
                ])

                # Loop through reflection angles
                for k in range(size):
                    for l in range(size):
                        print(f"  Checking reflection angle index: {k}, {l}")  # Debug statement

                        theta_r = np.pi * (k + 0.5) / size
                        phi_r = 2 * np.pi * (l + 0.5) / size

                        wr = np.array([
                            np.sin(theta_r) * np.cos(phi_r),
                            np.cos(theta_r),
                            np.sin(theta_r) * np.sin(phi_r)
                        ])

                        # Calculate the BRDF value (specular: GGX)
                        N = np.array([0, 1, 0])  # Normal facing up
                        F0 = np.array([0.04, 0.04, 0.04])  # Fresnel reflectance for dielectrics
                        alpha = 0.5  # Roughness

                        # Calculate the halfway vector
                        H = (wi + wr) / np.linalg.norm(wi + wr)
                        V = wi
                        L = wr

                        # Fresnel Schlick approximation
                        F = F0 + (1 - F0) * np.power(1 - np.dot(V, H), 5)

                        # Calculate D and G from GGX model
                        D_num = alpha ** 2
                        D_den = np.pi * (np.dot(N, H) ** 2 * (alpha ** 2 - 1) + 1) ** 2
                        D = D_num / D_den if D_den > 0 else 0

                        G_num = np.dot(N, V) * np.dot(N, L)
                        G_den = np.dot(V, H) * np.dot(L, H)
                        G = G_num / G_den if G_den > 0 else 0

                        # BRDF value
                        brdf_value = (F * D * G) / (4 * np.dot(N, V) * np.dot(N, L) + 1e-5)

                        # Store in texture with an alpha value of 1.0
                        brdf_texture[k, l, :] = np.array([brdf_value[0], brdf_value[1], brdf_value[2], 1.0])
        
        return brdf_texture

    def create_brdf_lut( self ) -> None:
        """Load the BRDF lut used for IBL contributions
        Should be generated, but staticly loaded for now"""
        #self.brdf_lut_texture  = glGenTextures(1)
        #data = self.create_brdf_texture( size )
        #create_image( size, data, self.brdf_lut )
        #load_image( f"{self.basepath}brdf.jpg", self.brdf_lut_texture )
        self.brdf_lut = self.context.images.loadOrFindFullPath( Path(f"{self.settings.shader_path}brdf.jpg") )
        return

    def loadOrFind( self, path : str ) -> int:
        """Load or find an image, implement find later
        :param path: The path to the the folder containing 6 textures, 1 for each side
        :type path: str
        """

        index = self._num_cubemaps
        load_cubemap( path, ".bmp", self.cubemap[index] )

        self._num_cubemaps += 1
        return index


    def bind( self, texture_id, texture_index, shader_uniform : str, shader_index : int ):
        """Bind texture using OpenGL with image index

        :param texture_id: the texture uid in GPU memory
        :type texture_id: uint32/uintc
        :param texture_index: The texture unit index in GLSL (eg. GL_TEXTURE0-GL_TEXTURE31)
        :type texture_index: uint32/uintc
        :param shader_uniform: The varaible name of the GLSL uniform sampler
        :type shader_uniform: str
        :param shader_index: Represent the number also indicated with 'texture_index'. revisit this?
        :type shader_index: int
        """
        glActiveTexture( texture_index )
        glBindTexture( GL_TEXTURE_CUBE_MAP, self.cubemap[texture_id] )
        glUniform1i(glGetUniformLocation( self.renderer.shader.program, shader_uniform ), shader_index)

