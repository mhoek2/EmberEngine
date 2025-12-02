import os, sys, enum
from pathlib import Path

from modules.settings import Settings

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject

import uuid as uid

class ScriptOBJ:
    def __init__( self, context : "EmberEngine", 
                    uuid            : uid.UUID  = None,
                    path            : Path      = None,
                    active          : bool      = False,
                    class_name      : str       = "",
                    class_name_f    : str       = "",
                    exports         : dict      = {}
                 ) -> None :
        if uuid is None:
            uuid = self.__create_uuid()

        self.instance       = None
        self.settings = context.settings

        self.uuid           : uid.UUID = uuid
        self.path           : Path     = path.relative_to(self.settings.rootdir)
        self.active         : bool     = active
        self.class_name     : str      = class_name
        self.class_name_f   : str      = class_name_f
        self.exports        : dict     = exports
        self._error         : str = None

    def __create_uuid( self ) -> uid.UUID:
        return uid.uuid4()

