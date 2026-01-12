import os
from pathlib import Path

from OpenGL.GL import *
from OpenGL.GLU import *

from typing import TYPE_CHECKING, TypedDict, List

from impasse.structs import Material as ImpasseMaterial, MaterialProperty
from impasse.constants import MaterialPropertyKey, TextureSemantic

from modules.context import Context
from modules.images import Images
from modules.render.types import Material, TextureKind_

import uuid as uid

class Materials( Context ):

    def __init__( self, context ):
        """Material loader for models

        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        super().__init__( context )

        self.images     : Images = context.images

        self.materials : List[Material] = [Material() for _ in range(1000)]
        self._num_materials : int = 0;

        self.defaultMaterial = self.buildMaterial()

    def __create_uuid( self ) -> uid.UUID:
        return uid.uuid4()

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
        mat : Material = self.materials[index]

        mat.albedo      = self.context.images.defaultImage
        mat.normal      = self.context.images.defaultNormal
        mat.emissive    = self.context.images.blackImage
        mat.opacity     = self.images.whiteImage
        mat.hasNormalMap = 0

        if albedo:
            mat.albedo = self.images.loadOrFindFullPath( albedo )

        if normal:
            mat.normal = self.images.loadOrFindFullPath( normal )

        if emissive:
            mat.emissive = self.images.loadOrFindFullPath( emissive )

        mat.opacity = self.images.whiteImage

        if rmo:
            mat.phyiscal = self.images.loadOrFindFullPath( rmo )
        else:
            if not r and not m and not o:
                mat.phyiscal = self.images.defaultRMO
            else:
                mat.phyiscal = self.images.loadOrFindPhysicalMap( r, m, o ) 

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
        
        return self.materials[self.context.materials.defaultMaterial]

    def is_gltf_texture( self, prop ) -> bool:
        """Assimp.."""
        return prop.data.startswith("*")

    def _get_texture_path( self, texture_str, model_path ) -> Path:
        model_dir = Path(model_path).parent      # /path/to
        texture_name = Path(texture_str).name     # texture.png or /path/to/texture.png, inconsistencies..
        
        return model_dir / texture_name   # /path/to/texture.png

    def load_texture( self, prop, model_path ):
        texture_path : Path = self._get_texture_path( prop.data, model_path )

        return self.images.loadOrFindFullPath( texture_path )

    def get_texture_kind( self, prop ) -> str:
        #
        # odd layout this assimp..
        #

        if prop.semantic == TextureSemantic.DIFFUSE:
            return TextureKind_.albedo

        elif prop.semantic == TextureSemantic.NORMALS or prop.semantic == TextureSemantic.HEIGHT:
            return TextureKind_.normal

        elif prop.semantic == TextureSemantic.OPACITY:
            return TextureKind_.opacity

        elif prop.semantic == TextureSemantic.EMISSIVE:
            return TextureKind_.emissive

        elif prop.semantic == TextureSemantic.SHININESS: 
            return TextureKind_.roughness

        elif prop.semantic == TextureSemantic.AMBIENT: 
            return TextureKind_.ambient

        elif prop.key == "$raw.ReflectionFactor|file": # hmmmm
            return TextureKind_.metallic

        #elif prop.semantic == TextureSemantic.UNKNOWN: 
        else: 
            return {
                0:      TextureKind_.albedo,
                1:      TextureKind_.specular,
                2:      TextureKind_.ambient,
                3:      TextureKind_.emissive,
                6:      TextureKind_.metallicRoughness,     # whats this?
                10:     TextureKind_.metallicRoughness,    # orm?
                #20:     TextureKind_.normal,              # orm?
                16:     TextureKind_.normal,               #actual normal # orm?
                12:     TextureKind_.albedo_dup,
                15:     TextureKind_.metallic,
                27:     TextureKind_.occlusion,
            }.get( prop.semantic, TextureKind_.none )
            #}.get( prop.index )
            # uff, i dont think semantic is the correct index here

            return TextureKind_.none

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

        _model_name = os.path.basename(path)
        scene = material._scene
        #material_name = f"{self.__create_uuid().hex}_modelname_"
        #
        #for prop in material.properties:
        #    if prop.key == "?mat.name":
        #        material_name += prop.data
        #        break

        # preload textures (queued) shared across all meshes/nodes
        # should be global and cleared when model load is finished
        # also needs to store pixels localy, for rmo building?
        # or change order of exising rmo?
        textures = [None] * 25
        for i, tex in enumerate(scene.textures):
            texture_name = f"{_model_name}_{i}"

            width, height, buffer = self.images.pixelsToImage( tex.data )
            textures[i] = self.images.loadFromPixels( width, height, buffer, texture_name )

        # maybce change rmo order to:
        # R -> Occlusion
        # G -> Roughness
        # B -> Metallic
        found_phyisical = False

        for prop in material.properties:
            if prop.key != "$tex.file":
                continue

            kind = self.get_texture_kind( prop )
            print( f"texture kind: {kind.name}")

            if kind == None:
                # console print?
                print( f"uknown prop - semantic: {prop.semantic}")

            # albedo/diffuse
            if kind == TextureKind_.albedo:
                if self.is_gltf_texture( prop ):
                    mat.albedo= textures[ int(prop.data[1:]) ]
                else:
                    mat.albedo= self.load_texture( prop, path )

                    # find ambient occlusion
                    ao = self._get_texture_path( self.add_ao_suffix( os.path.basename(prop.data) ), path )
                    if os.path.isfile( ao ):
                        o = ao
        
            # normals
            if kind == TextureKind_.normal:
                if self.is_gltf_texture( prop ):
                    mat.normal = textures[ int(prop.data[1:]) ]
                else:
                    mat.normal = self.load_texture( prop, path )
        
            # opacity
            if kind == TextureKind_.opacity:
                if self.is_gltf_texture( prop ):
                    mat.opacity = textures[ int(prop.data[1:]) ]
                else:
                    mat.opacity = self.load_texture( prop, path )

            # emissive
            if kind == TextureKind_.emissive:
                if self.is_gltf_texture( prop ):
                    mat.emissive = textures[ int(prop.data[1:]) ]
                else:
                    mat.emissive = self.load_texture( prop, path )

            # roughness
            if kind == TextureKind_.roughness:
                r = self._get_texture_path( prop.data, path )
                #r = path / Path(prop.data).name

            # ambient occlusion
            if kind == TextureKind_.ambient:
                o = self._get_texture_path( prop.data, path )
                #o = path / Path(prop.data).name

            # metallic
            if kind == TextureKind_.metallic:
                m = self._get_texture_path( prop.data, path )
                #m = path / Path(prop.data).name

            # hm
            if kind == TextureKind_.metallicRoughness:
                if self.is_gltf_texture( prop ):
                    mat.phyiscal = textures[ int(prop.data[1:]) ]
                    found_phyisical = True
                else:
                    pass
 
        # r, m and o should be packed into a new _rmo file.
        if not found_phyisical:
            if not r and not m and not o:
                mat.phyiscal = self.images.defaultRMO
            else:
                mat.phyiscal = self.images.loadOrFindPhysicalMap( r, m, o ) 

        mat.hasNormalMap = int( mat.normal is not self.images.defaultNormal )

        self.context.renderer.ubo.ubo_materials._dirty = True
        return index

    def bind( self, index : int ):
        """Bind the textures to the commmand buffer

        :param index: The index of the material in the buffer
        :type index: int
        """
        if index < self._num_materials:
            mat = self.materials[index]
        else:
            mat = self.materials[self.context.materials.defaultMaterial]

        self.images.bind( mat.albedo,   GL_TEXTURE0, "sTexture",     0 )
        self.images.bind( mat.normal,   GL_TEXTURE1, "sNormal",      1 )
        self.images.bind( mat.phyiscal, GL_TEXTURE2, "sPhysical",    2 )
        self.images.bind( mat.emissive, GL_TEXTURE3, "sEmissive",    3 )
        self.images.bind( mat.opacity,  GL_TEXTURE4, "sOpacity",     4 )
