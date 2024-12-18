from pathlib import Path
from tkinter import IntVar

class Settings:
    def __init__( self ) -> None:
        """Global applictaion settings"""

        self.rootdir = Path.cwd()

        self.engineAssets   = f"{self.rootdir}\\engineAssets\\"
        self.assets         = f"{self.rootdir}\\assets\\"
        self.shader_path    = f"{self.rootdir}\\shaders\\"
        self.cubemap_path   = f"{self.rootdir}\\cubemaps\\"

        # wireframe
        self.drawWireframe = False

        # grid
        self.grid_color = ( 0.0, 1.0, 0.0, 1.0 )
        self.grid_size = 10.0
        self.grid_spacing = 0.5