import os
from pathlib import Path

class Settings:
    def __init__( self ) -> None:
        """Global applictaion settings"""
        self.application_name = "Ember Engine 3D"

        self.game_running = False
        self.game_start = False
        self.game_stop = False

        self.msaa = 8
        self.msaaEnabled = True if self.msaa > 0 else False

        # extensions
        self.SCENE_EXTENSION    : str = ".scene"
        self.SCRIPT_EXTENSION   : str = ".py"
        self.MODEL_EXTENSION    : list[str] = [
            ".fbx",
            ".obj",
            ".glb",
        ]

        self.rootdir = Path.cwd()

        self.engineAssets   = f"{self.rootdir}\\engineAssets\\"
        self.assets         = f"{self.rootdir}\\assets\\"
        self.shader_path    = f"{self.rootdir}\\shaders\\"
        self.cubemap_path   = f"{self.rootdir}\\cubemaps\\"

        self.engine_texture_path    = f"{self.engineAssets}\\textures\\"
        self.engine_gui_path        = f"{self.engineAssets}\\gui\\"

        self.default_scene          = Path(f"{self.engineAssets}\\scenes\engine_default{self.SCENE_EXTENSION}")
        self.default_environment    = f"{self.engineAssets}\\cubemaps\\day"

        self.default_light_color     = ( 1.0, 1.0, 1.0, 1.0 )
        self.default_ambient_color   = ( 0.3, 0.3, 0.3, 1.0 )

        # wireframe
        self.drawWireframe = False

        # grid
        self.grid_color = ( 0.83, 0.74, 94.0, 1.0 )
        self.grid_size = 10.0
        self.grid_spacing = 0.5

        # scriptable behaivior
        self.SCRIPT_AUTO_IMPORT_MODULES = {
            # module        # as
            "pygame"                : None,
            "pybullet"              : "p",
            #"modules.transform"     : None
        }

        # exported application
        self.is_exported            = self.is_app_exported()
        self.project_default_name   = "New Project"
        self.executable_format      = r"[^a-zA-Z0-9 _-]"
        self.export_clean           = True
        self.export_debug           = False

        # coordination
        self.ENGINE_ROTATION_MAP  = {
            "XYZ": "ZYX",
            "XZY": "YZX",
            "YXZ": "ZXY",
            "YZX": "XZY",
            "ZXY": "YXZ",
            "ZYX": "XYZ"
        }

        self.ENGINE_ROTATION = "YXZ"

    def is_app_exported( self ):
        """Wheter the appliction as exported using Ember Engine"""
        return os.getenv("EE_EXPORTED") == "1"