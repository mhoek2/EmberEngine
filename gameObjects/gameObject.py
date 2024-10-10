import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *

import numpy as np
from pyrr import Matrix44, Vector3

from modules.cubemap import Cubemap
from modules.renderer import Renderer
from modules.images import Images
from modules.models import Models

class GameObject:
    def __init__( self, context, 
                 model_file="Tree/Tree.obj",
                 texture_file="newfloor.jpg",
                 normals_file="newfloor_nh.tga",
                 phyiscal_file="newfloor_rmo.tga",
                 translate=[ 0.0, 0.0, 0.0 ], 
                 rotation=[ 0.0, 0.0, 0.0 ], 
                 scale=[ 1.0, 1.0, 1.0 ] ) -> None:
        self.context = context
        self.renderer : Renderer = context.renderer
        self.images : Images = context.images
        self.cubemaps : Cubemap = context.cubemaps
        self.models : Models = context.models
        
        # https://github.com/adamlwgriffiths/Pyrr
        self.translate = translate
        self.rotation = rotation
        self.scale = scale

        # model
        self.model_file = model_file

        # texture
        self.texture_file = texture_file
        self.normals_file = normals_file
        self.phyiscal_file = phyiscal_file

        self.onStart()
        return

    def _createModelMatrix( self ):
        """Create model matrix with translation, rotation and scale vectors"""
        model = Matrix44.identity()
        model = model * Matrix44.from_translation( Vector3( [self.translate[0], self.translate[1], self.translate[2]] ) )
        model = model * Matrix44.from_eulers( Vector3([self.rotation[0], self.rotation[1], self.rotation[2]] ) )
        return model * Matrix44.from_scale( Vector3( [self.scale[0], self.scale[1], self.scale[2]] ) )

    def onStart( self ) -> None:
        """Implemented by inherited class"""
        return

    def onUpdate( self ) -> None:
        """Implemented by inherited class"""
        return
    