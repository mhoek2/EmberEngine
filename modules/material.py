import copy
from OpenGL.GL import *
from OpenGL.GLU import *
import os

from impasse.structs import Material as ImpasseMaterial, MaterialProperty
from impasse.constants import MaterialPropertyKey, TextureSemantic

from modules.imageLoader import load_image_pygame as load_image
from modules.images import Images
from modules.renderer import Renderer

class Material:
    def __init__( self, context ):
        self.context = context
        self.renderer : Renderer = context.renderer
        self.images : Images = context.images

        self.materials = [ImpasseMaterial for i in range(300)]
        self.materials_info = [{} for i in range(300)]
        self._materials_size = 0;

        self.basepath = "C:/Github-workspace/EmberEngine/assets/textures/"
        return

    #, mesh_mat_index : int
    def loadOrFind( self, material, path ) -> int:
        """Processes a material by loading images and setting info"""

        # find
        #for i, mat in self.materials:
        #    if mat == material:
        #        return i

        # load
        index = self._materials_size

        self.materials[index] = material # can be deprecated later
        
        info = self.materials_info[index]

        info["albedo"] = False
        info["normal"] = False

        for prop in material.properties:
            if prop.key == MaterialPropertyKey.TEXTURE:
                if prop.semantic == TextureSemantic.DIFFUSE:
                    _filename = os.path.basename( prop.data )
                    info["albedo"] = self.images.loadOrFindFullPath( f"{path}/{_filename}")
        
                if prop.semantic == TextureSemantic.NORMALS:
                    _filename = os.path.basename( prop.data )
                    info["normal"] = self.images.loadOrFindFullPath( f"{path}/{_filename}")
        
                if prop.semantic == TextureSemantic.SHININESS: #roughness
                    _filename = os.path.basename( prop.data )
                    return

                if prop.semantic == 18: #metallic
                    _filename = os.path.basename( prop.data )
                    info["normal"] = self.images.loadOrFindFullPath( f"{path}/{_filename}")

            if prop.key == MaterialPropertyKey.USE_ROUGHNESS_MAP:
                test = 1

        self._materials_size += 1

        return index

    def bind( self, index ):

        #mat : ImpasseMaterial = self.materials[index] # can be deprecatedv
        info = self.materials_info[index]

        if info["albedo"]:
            self.images.bind( info["albedo"], GL_TEXTURE0, "sTexture", 0 )
       
        if info["normal"]:
            self.images.bind( info["normal"], GL_TEXTURE1, "sNormal", 1 )


        return
