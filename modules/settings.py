from pathlib import Path
from tkinter import IntVar

class Settings:
    def __init__( self ) -> None:
        """Global applictaion settings"""

        self.game_running = False
        self.game_start = False

        self.msaa = 8
        self.msaaEnabled = True if self.msaa > 0 else False

        self.rootdir = Path.cwd()

        self.engineAssets   = f"{self.rootdir}\\engineAssets\\"
        self.assets         = f"{self.rootdir}\\assets\\"
        self.shader_path    = f"{self.rootdir}\\shaders\\"
        self.cubemap_path   = f"{self.rootdir}\\cubemaps\\"

        self.engine_texture_path    = f"{self.engineAssets}\\textures\\"
        self.engine_gui_path        = f"{self.engineAssets}\\gui\\"

        self.default_scene = f"{self.engineAssets}\\scenes\default.scene"
        self.default_environment = f"{self.engineAssets}\\cubemaps\\day"

        self.default_light_color     = ( 1.0, 1.0, 1.0, 1.0 )
        self.default_ambient_color   = ( 0.3, 0.3, 0.3, 1.0 )

        # wireframe
        self.drawWireframe = False

        # grid
        self.grid_color = ( 0.83, 0.74, 94.0, 1.0 )
        self.grid_size = 10.0
        self.grid_spacing = 0.5