"""Contains logic for json handling"""
import json
from typing import Any

from modules.files import FileHandler   # custom module

class JsonHandler:
    """This class will handle json processing"""

    file:   FileHandler

    def __init__( self, filename: str ) -> None:
        self.file = FileHandler( filename )

    def getJson( self ) -> Any:
        """Get json from instanced file"""
        content = self.file.getContent()

        if not content:
            return False

        return json.loads( content )

    def storeJson( self, data ) -> bool:
        """Store/dump/serialize object to instanced file"""

        if self.file.setContent( json.dumps( data ) ) :
           return True
        else:
           return False