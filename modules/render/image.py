from pathlib import Path

from OpenGL.GL import glGetError, GL_NO_ERROR, glGenerateMipmap, glBindTexture, glTexParameteri, GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, \
    GL_TEXTURE_WRAP_T, GL_TEXTURE_WRAP_R, GL_REPEAT, GL_CLAMP_TO_EDGE, GL_LINEAR, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR, GL_TEXTURE_MAG_FILTER, GL_LINEAR,\
    glTexImage2D, GL_RGBA, GL_RGBA16F, GL_RGBA32F, GL_FLOAT, GL_UNSIGNED_BYTE, GL_TEXTURE_CUBE_MAP, GL_TEXTURE_CUBE_MAP_POSITIVE_X 

from OpenGL.GLU import gluErrorString

from dataclasses import dataclass, field

@dataclass(slots=True)
class ImageUpload:
    path            : Path = field( default=None )
    width           : int = field( default=None )
    height          : int = field( default=None )
    mipmap          : bool = field( default=False)
    buffer          : str = field( default=None)
    _format         : int = field( default=GL_UNSIGNED_BYTE)
    _internal_format: int = field( default=GL_RGBA)

def create_image_pygame( size, data, texture ):
    import numpy as np

    glBindTexture(GL_TEXTURE_2D, texture)

    # Set the texture wrapping parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    # Set texture filtering parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

     # load image
    image = Image.fromarray((data * 255).astype(np.uint8), 'RGBA')

    image_width, image_height = size

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image_width, image_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    return texture

def upload_image( texture_id, image : ImageUpload ):
    glBindTexture(GL_TEXTURE_2D, texture_id)

    # set the texture wrapping parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    # set texture filtering parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glTexImage2D( GL_TEXTURE_2D, 0, GL_RGBA, image.width, image.height, 0, GL_RGBA, image._format, image.buffer )

    # mipmap
    if image.mipmap:
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)

    err = glGetError()
    if (err != GL_NO_ERROR):
        print('GLERROR: ', gluErrorString(err)) # pylint: disable=E1101

def load_cubemap_pygame( path : Path, extension, texture ):
    import pygame
    glBindTexture(GL_TEXTURE_CUBE_MAP, texture)

    faces = ( "right", "left", "down", "up", "front", "back" )

    for i, face in enumerate(faces):
        filepath = f"{str(path)}\\{face}{extension}"

        image = pygame.image.load( filepath )
        image = pygame.transform.flip( image, False, True )
        image_width, image_height = image.get_rect().size
        img_data = pygame.image.tostring( image, "RGBA" )

        glTexImage2D( GL_TEXTURE_CUBE_MAP_POSITIVE_X + i, 0, GL_RGBA, image_width, image_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data )

        print(filepath)

    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);

    return texture