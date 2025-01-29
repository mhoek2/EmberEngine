import os
from pathlib import Path

from OpenGL.GL import *
from OpenGL.GLU import *

from impasse.structs import Material as ImpasseMaterial, MaterialProperty
from impasse.constants import MaterialPropertyKey, TextureSemantic

from modules.context import Context
from modules.images import Images

class Material( Context ):
    def __init__( self, context ):
        super().__init__( context )

        self.images     : Images = context.images

        self.materials = [{} for i in range(300)]
        self._num_materials : int = 0;

        return

    @staticmethod
    def add_ao_suffix( filename ):
        base, ext = os.path.splitext(filename)
        return f"{base}_ao{ext}"

    def buildMaterial( self, 
                       albedo   : Path = False, 
                       normal   : Path = False, 
                       emissive : Path = False, 
                       r        : Path = False, 
                       m        : Path = False, 
                       o        : Path = False,
                       rmo      : Path = False ) -> int:
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

    def loadOrFind( self, material, path : Path ) -> int:
        """Create a material by parsing model material info and loading textures"""

        # find
        #for i, mat in self.materials:
        #    if mat == material:
        #        return i

        # initialize empty material
        index = self.buildMaterial()
        mat = self.materials[index]
  
        r = False
        m = False
        o = False

        load_texture = lambda prop, path: self.images.loadOrFindFullPath( 
            path / Path(prop.data).name
        )

        for prop in material.properties:

            if prop.key == MaterialPropertyKey.TEXTURE:
                # albedo
                if prop.semantic == TextureSemantic.DIFFUSE:
                    mat["albedo"] = load_texture( prop, path )

                    # find ambient occlusion
                    _filepath_ao = Path( f"{path}\\{ self.add_ao_suffix( os.path.basename(prop.data) )}" )
                    if os.path.isfile( _filepath_ao ):
                        o = _filepath_ao
        
                # normals
                elif prop.semantic == TextureSemantic.NORMALS or prop.semantic == TextureSemantic.HEIGHT:
                    mat["normal"] = load_texture( prop, path )
        
                # roughness
                elif prop.semantic == TextureSemantic.SHININESS: 
                    r = path / Path(prop.data).name

                # opacity
                elif prop.semantic == TextureSemantic.OPACITY:
                    mat["opacity"] = load_texture( prop, path )

                # emissive
                if prop.semantic == TextureSemantic.EMISSIVE:
                    mat["emissive"] = load_texture( prop, path )

                # ambient occlusion
                elif prop.semantic == TextureSemantic.AMBIENT: 
                    o = path / Path(prop.data).name

            # metallic
            if prop.key == "$raw.ReflectionFactor|file":  # hmmm... 
                m = path / Path(prop.data).name

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
