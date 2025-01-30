import os
from pathlib import Path

from OpenGL.GL import *
from OpenGL.GLU import *

from typing import TYPE_CHECKING, TypedDict, List

from impasse.structs import Material as ImpasseMaterial, MaterialProperty
from impasse.constants import MaterialPropertyKey, TextureSemantic

from modules.context import Context
from modules.images import Images

class Materials( Context ):
    class Material(TypedDict):
        albedo      : int # uint32/uintc
        normal      : int # uint32/uintc
        emissive    : int # uint32/uintc
        opacity     : int # uint32/uintc
        phyiscal    : int # uint32/uintc

    def __init__( self, context ):
        """Material loader for models

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )

        self.images     : Images = context.images

        self.materials : List[Materials.Material] = [{} for i in range(300)]
        self._num_materials : int = 0;

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
        """Build a material based on defined textures

        :param albedo: diffuse/albedo/base color map

        :type abledo: Path
        :param normal: normal map 
        :type normal: Path
        :param emissive: emissive map 
        :type emissive: Path
        :param r: roughness map 
        :type r: Path
        :param m: metallic map
        :type m: Path
        :param o: occlusion map
        :type o: Path
        :param rmo: already packed roughness/metallic/occlused map 
        :type rmo: Path
        :return: The index in the material buffer
        :rtype: int
        """
        index = self._num_materials
        mat : Materials.Material = self.materials[index]

        if albedo:
            mat["albedo"] = self.images.loadOrFindFullPath( albedo )

        if normal:
            mat["normal"] = self.images.loadOrFindFullPath( normal )

        if emissive:
            mat["emissive"] = self.images.loadOrFindFullPath( emissive )

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

    def getMaterialByIndex( self, index : int ) -> Material:
        """Get material by index, return default material if out of scope

        :param index: The index of the material in the buffer
        :type index: int
        :return: The material data
        :rtype: Dict, no TypedDict yet
        """
        if index < self._num_materials:
            return self.materials[index]
        
        return self.materials[self.context.defaultMaterial]

    def loadOrFind( self, material : ImpasseMaterial, path : Path ) -> int:
        """Create a material by parsing model material info and loading textures

        :param material: the material data from Impasse/assimp
        :type material: Material as ImpasseMaterial
        :param path: the path where the textures should be located
        :type path: Path
        :return: The index of the material in the buffer
        :rtype: int
        """
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

    def bind( self, index : int ):
        """Bind the textures to the commmand buffer

        :param index: The index of the material in the buffer
        :type index: int
        """
        if index < self._num_materials:
            mat = self.materials[index]
        else:
            mat = self.materials[self.context.defaultMaterial]

        self.images.bind( mat.get("albedo",     self.images.defaultImage),  GL_TEXTURE0, "sTexture",     0 )
        self.images.bind( mat.get("normal",     self.images.defaultNormal), GL_TEXTURE1, "sNormal",      1 )
        self.images.bind( mat.get("phyiscal",   self.images.defaultRMO),    GL_TEXTURE2, "sPhyiscal",    2 )
        self.images.bind( mat.get("emissive",   self.images.blackImage),    GL_TEXTURE3, "sEmissive",    3 )
        self.images.bind( mat.get("opacity",    self.images.whiteImage),    GL_TEXTURE4, "sOpacity",     4 )
