from pathlib import Path

from OpenGL.GL import glGetError, GL_NO_ERROR, glGenerateMipmap, glBindTexture, glTexParameteri, GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, \
    GL_TEXTURE_WRAP_T, GL_TEXTURE_WRAP_R, GL_REPEAT, GL_CLAMP_TO_EDGE, GL_LINEAR, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR, GL_TEXTURE_MAG_FILTER, GL_LINEAR,\
    glTexImage2D, GL_RGBA, GL_RGBA16F, GL_RGBA32F, GL_FLOAT, GL_UNSIGNED_BYTE, GL_TEXTURE_CUBE_MAP, GL_TEXTURE_CUBE_MAP_POSITIVE_X 

from OpenGL.GLU import gluErrorString

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

# for use with pygame
def load_image_pygame(path : Path, texture, flip_x: bool = False, flip_y: bool = True):
    import pygame
    glBindTexture(GL_TEXTURE_2D, texture)

    # Set the texture wrapping parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    # Set texture filtering parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    # load image
    image = pygame.image.load( str(path) )
    image = pygame.transform.flip(image, flip_x, flip_y)
    image_width, image_height = image.get_rect().size
    img_data = pygame.image.tostring(image, "RGBA")
    
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, image_width, image_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    
    print(str(path))

    return texture

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


def create_white_image( size ):
    import pygame
    white_surface = pygame.Surface(size)
    white_surface.fill((255, 255, 255, 255))
    return white_surface

def create_black_image( size ):
    import pygame
    white_surface = pygame.Surface(size)
    white_surface.fill((0, 0, 0, 255))
    return white_surface

def create_grey_image( size ):
    import pygame
    white_surface = pygame.Surface(size)
    white_surface.fill((127, 127, 127, 255))
    return white_surface

# load rmo map
def create_rmo_map( roughness_path, metallic_path, ao_path, texture ):
    import pygame
    import numpy as np


    size = (-1, -1)
    # Load images and get highest dimension
    # TODO: fix missing file issue..
    if roughness_path:
        roughness = pygame.image.load( roughness_path )
        if size < roughness.get_size() : size = roughness.get_size()

    if metallic_path:
        metallic = pygame.image.load( metallic_path )
        if size < metallic.get_size() : size = metallic.get_size()

    if ao_path:
        ambient_occlusion = pygame.image.load( ao_path )
        if size < ambient_occlusion.get_size() : size = ambient_occlusion.get_size()

    if size == (-1, -1):
        raise ValueError("No map found!")
        return False

    # fill empty channels
    if not roughness_path:
        roughness = create_grey_image( size )

    if not metallic_path:
        metallic = create_black_image( size )

    if not ao_path:
        ambient_occlusion = create_white_image( size )

    # Ensure all images are the same size
    # todo: should probably auto-scale to highest dimension ..
    if roughness.get_size() != metallic.get_size() or roughness.get_size() != ambient_occlusion.get_size():
        raise ValueError("All images must be the same size!")

    # Get image dimensions
    image_width, image_height = roughness.get_size()

    # Create a new surface to hold combined image data
    combined_image = pygame.Surface((image_width, image_height))

    # Lock surfaces to access pixel data
    roughness.lock()
    metallic.lock()
    ambient_occlusion.lock()
    combined_image.lock()

    roughness_array = pygame.surfarray.array3d(roughness).astype(np.float32) / 255.0
    metallic_array = pygame.surfarray.array3d(metallic).astype(np.float32) / 255.0
    ambient_occlusion_array = pygame.surfarray.array3d(ambient_occlusion).astype(np.float32) / 255.0

    # you may need to transpose based on your orientation.
    combined_array = np.zeros((image_width, image_height, 4), dtype=np.float32)
    combined_array[..., 0] = roughness_array[..., 0]                            # Roughness from R channel
    combined_array[..., 1] = metallic_array[..., 1]                             # Metallic from G channel
    combined_array[..., 2] = ambient_occlusion_array[..., 2]                    # AO from B channel
    combined_array[..., 3] = 1.0
    combined_array = np.rot90(combined_array, k=1)

    # Unlock surfaces
    roughness.unlock()
    metallic.unlock()
    ambient_occlusion.unlock()
    combined_image.unlock()

    glBindTexture(GL_TEXTURE_2D, texture)

    # Set the texture wrapping parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)

    # Set texture filtering parameters
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA16F, image_width, image_height, 0, GL_RGBA, GL_FLOAT, combined_array.tobytes())
    
    glGenerateMipmap(GL_TEXTURE_2D)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)

    err = glGetError()
    if (err != GL_NO_ERROR):
        print('GLERROR: ', gluErrorString(err)) # pylint: disable=E1101


    return texture