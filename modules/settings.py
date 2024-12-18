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