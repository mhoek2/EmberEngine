import copy
from OpenGL.GL import *
from OpenGL.GLU import *
import os

from impasse.structs import Material as ImpasseMaterial, MaterialProperty
from impasse.constants import MaterialPropertyKey, TextureSemantic

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

        self.defaultRMO = self.images.loadOrFindFullPath( f"{self.context.engineAssets}textures\\default_rmo.png")
        return

    #, mesh_mat_index : int

    @staticmethod
    def add_ao_suffix( filename ):
        base, ext = os.path.splitext(filename)
        return f"{base}_ao{ext}"

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
        info["phyiscal"] = False

        _metallic = False
        _roughness = False
        _ao = False

        for prop in material.properties:

            if prop.key == MaterialPropertyKey.TEXTURE:
                # albedo
                if prop.semantic == TextureSemantic.DIFFUSE:
                    _filename = os.path.basename( prop.data )
                    info["albedo"] = self.images.loadOrFindFullPath( f"{path}\\{_filename}")

                    # find ambient occlusion
                    _filepath_ao = f"{path}\\{ self.add_ao_suffix( _filename )}"
                    if os.path.isfile( _filepath_ao ):
                        _ao = _filepath_ao
        
                # normals
                elif prop.semantic == TextureSemantic.NORMALS or prop.semantic == TextureSemantic.HEIGHT:
                    _filename = os.path.basename( prop.data )
                    info["normal"] = self.images.loadOrFindFullPath( f"{path}\\{_filename}")
        
                # roughness
                elif prop.semantic == TextureSemantic.SHININESS: 
                    _filename = os.path.basename( prop.data )
                    _roughness = f"{path}\\{_filename}"

                # ambient occlusion
                elif prop.semantic == TextureSemantic.AMBIENT: 
                    _filename = os.path.basename( prop.data )
                    _ao = f"{path}\\{_filename}"

            # metallic
            if prop.key == "$raw.ReflectionFactor|file":  # hmmm... 
                _filename = os.path.basename( prop.data )
                _metallic = f"{path}\\{_filename}"

        # _roughness, _metallic and _ao should be packed into a new _rmo file.
        if not _metallic and not _roughness and not _ao:
            info["phyiscal"] = self.defaultRMO
        else:
            info["phyiscal"] = self.images.loadOrFindPhysicalMap( _roughness, _metallic, _ao ) 

        self._materials_size += 1

        return index

    def bind( self, index ):

        #mat : ImpasseMaterial = self.materials[index] # can be deprecatedv
        info = self.materials_info[index]

        if info["albedo"]:
            self.images.bind( info["albedo"], GL_TEXTURE0, "sTexture", 0 )
       
        if info["normal"]:
            self.images.bind( info["normal"], GL_TEXTURE1, "sNormal", 1 )

        if info["phyiscal"]:
            self.images.bind( info["phyiscal"], GL_TEXTURE2, "sPhyiscal", 2 )

        return
