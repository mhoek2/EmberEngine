from OpenGL.GL import *
from OpenGL.GLU import *
import os

from impasse.structs import Material as ImpasseMaterial, MaterialProperty
from impasse.constants import MaterialPropertyKey, TextureSemantic

from modules.context import Context
from modules.images import Images

class Material( Context ):
    def __init__( self, context ):
        super().__init__( context )

        self.images     : Images = context.images

        self.materials = [{} for i in range(300)]
        self._num_materials = 0;

        return

    @staticmethod
    def add_ao_suffix( filename ):
        base, ext = os.path.splitext(filename)
        return f"{base}_ao{ext}"

    def buildMaterial( self, 
                       albedo   : str = False, 
                       normal   : str = False, 
                       emissive : str = False, 
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
            mat["normal"] = self.images.defaultNormal

        if emissive:
            mat["emissive"] = self.images.loadOrFindFullPath( emissive )
        else:
            mat["emissive"] = self.images.blackImage

        mat["opacity"] = self.images.whiteImage

        if rmo:
            mat["phyiscal"] = self.images.loadOrFindFullPath( rmo )
        else:
            if not r and not m and not o:
                mat["phyiscal"] = self.images.defaultRMO
            else:
                mat["phyiscal"] = self.images.loadOrFindPhysicalMap( r, m, o ) 

        self._num_materials += 1
        return index

    def getMaterialByIndex( self, index : int ):
        """Get material by index, return default material if out of scope"""
        if index < self._num_materials:
            return self.materials[index]
        else:
            return self.materials[self.context.defaultMaterial]

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

                # opacity
                elif prop.semantic == TextureSemantic.OPACITY:
                    _filename = os.path.basename( prop.data )
                    mat["opacity"] = self.images.loadOrFindFullPath( f"{path}\\{_filename}")

                # emissive
                if prop.semantic == TextureSemantic.EMISSIVE:
                    _filename = os.path.basename( prop.data )
                    mat["emissive"] = self.images.loadOrFindFullPath( f"{path}\\{_filename}")

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
            mat["phyiscal"] = self.images.defaultRMO
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
            self.images.bind( self.images.defaultNormal, GL_TEXTURE1, "sNormal", 1 )

        if 'phyiscal' in mat:
            self.images.bind( mat["phyiscal"], GL_TEXTURE2, "sPhyiscal", 2 )
        else:
            self.images.bind( self.images.defaultRMO, GL_TEXTURE2, "sPhyiscal", 2 )

        if 'emissive' in mat:
            self.images.bind( mat["emissive"], GL_TEXTURE3, "sEmissive", 3 )
        else:
            self.images.bind( self.images.blackImage, GL_TEXTURE3, "sEmissive", 3 )

        if 'opacity' in mat:
            self.images.bind( mat["opacity"], GL_TEXTURE4, "sOpacity", 4 )
        else:
            self.images.bind( self.images.whiteImage, GL_TEXTURE4, "sOpacity", 4 )

        return
