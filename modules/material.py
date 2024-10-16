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
        self.renderer   : Renderer = context.renderer
        self.images     : Images = context.images

        self.materials = [{} for i in range(300)]
        self._num_materials = 0;

        self.defaultRMO = self.images.loadOrFindFullPath( f"{self.context.engineAssets}textures\\default_rmo.png")
        self.defaultNormal = self.images.loadOrFindFullPath( f"{self.context.engineAssets}textures\\default_normal.png")
        return

    @staticmethod
    def add_ao_suffix( filename ):
        base, ext = os.path.splitext(filename)
        return f"{base}_ao{ext}"

    def buildMaterial( self, 
                       albedo   : str = False, 
                       normal   : str = False, 
                       r        : str = False, 
                       m        : str = False, 
                       o        : str = False,
                       rmo      : str = False ) -> int:
        """Build a material based on defined textures"""

        index = self._num_materials
        mat = self.materials[index]

        mat["albedo"] = self.images.loadOrFindFullPath( albedo )

        if normal:
            mat["normal"] = self.images.loadOrFindFullPath( normal )
        else:
            mat["normal"] = self.defaultNormal

        if rmo:
            mat["phyiscal"] = self.images.loadOrFindFullPath( rmo )
        else:
            if not r and not m and not o:
                mat["phyiscal"] = self.defaultRMO
            else:
                mat["phyiscal"] = self.images.loadOrFindPhysicalMap( r, m, o ) 

        self._num_materials += 1
        return index

    def loadOrFind( self, material, path ) -> int:
        """Create a material by parsing model material info and loading textures"""

        # find
        #for i, mat in self.materials:
        #    if mat == material:
        #        return i

        # initiliate empty material
        index = self.buildMaterial()
        mat = self.materials[index]
  
        r = False
        m = False
        o = False

        for prop in material.properties:

            if prop.key == MaterialPropertyKey.TEXTURE:
                # albedo
                if prop.semantic == TextureSemantic.DIFFUSE:
                    _filename = os.path.basename( prop.data )
                    mat["albedo"] = self.images.loadOrFindFullPath( f"{path}\\{_filename}")

                    # find ambient occlusion
                    _filepath_ao = f"{path}\\{ self.add_ao_suffix( _filename )}"
                    if os.path.isfile( _filepath_ao ):
                        o = _filepath_ao
        
                # normals
                elif prop.semantic == TextureSemantic.NORMALS or prop.semantic == TextureSemantic.HEIGHT:
                    _filename = os.path.basename( prop.data )
                    mat["normal"] = self.images.loadOrFindFullPath( f"{path}\\{_filename}")
        
                # roughness
                elif prop.semantic == TextureSemantic.SHININESS: 
                    _filename = os.path.basename( prop.data )
                    r = f"{path}\\{_filename}"

                # ambient occlusion
                elif prop.semantic == TextureSemantic.AMBIENT: 
                    _filename = os.path.basename( prop.data )
                    o = f"{path}\\{_filename}"

            # metallic
            if prop.key == "$raw.ReflectionFactor|file":  # hmmm... 
                _filename = os.path.basename( prop.data )
                m = f"{path}\\{_filename}"

        # r, m and o should be packed into a new _rmo file.
        if not r and not m and not o:
            mat["phyiscal"] = self.defaultRMO
        else:
            mat["phyiscal"] = self.images.loadOrFindPhysicalMap( r, m, o ) 

        return index

    def bind( self, index ):

        if index < self._num_materials:
            mat = self.materials[index]
        else:
            mat = self.materials[self.context.defaultMaterial]

        if 'albedo' in mat:
            self.images.bind( mat["albedo"], GL_TEXTURE0, "sTexture", 0 )
        else:
            self.images.bind( self.images.defaultImage, GL_TEXTURE0, "sTexture", 0 )

        if 'normal' in mat:
            self.images.bind( mat["normal"], GL_TEXTURE1, "sNormal", 1 )
        else:
            self.images.bind( self.images.defaultImage, GL_TEXTURE1, "sNormal", 1 )

        if 'phyiscal' in mat:
            self.images.bind( mat["phyiscal"], GL_TEXTURE2, "sPhyiscal", 2 )
        else:
            self.images.bind( self.images.defaultImage, GL_TEXTURE1, "sPhyiscal", 2 )

        return
