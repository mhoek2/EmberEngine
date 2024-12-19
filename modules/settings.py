from pathlib import Path
from tkinter import IntVar

class Settings:
    def __init__( self ) -> None:
        """Global applictaion settings"""

        self.msaa = 8
        self.msaaEnabled = True if self.msaa > 0 else False

        self.rootdir = Path.cwd()

        self.engineAssets   = f"{self.rootdir}\\engineAssets\\"
        self.assets         = f"{self.rootdir}\\assets\\"
        self.shader_path    = f"{self.rootdir}\\shaders\\"
        self.cubemap_path   = f"{self.rootdir}\\cubemaps\\"

        self.engine_texture_path    = f"{self.engineAssets}\\textures\\"
        self.engine_gui_path        = f"{self.engineAssets}\\gui\\"

        # wireframe
        self.drawWireframe = False

        # grid
        self.grid_color = ( 0.83, 0.74, 94.0, 1.0 )
        self.grid_size = 10.0
        self.grid_spacing = 0.5