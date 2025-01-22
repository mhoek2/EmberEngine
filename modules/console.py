from typing import TYPE_CHECKING, List, TypedDict

from modules.settings import Settings

if TYPE_CHECKING:
    from main import EmberEngine

class Console:
    class Entry(TypedDict):
        type_id: str
        message: str

    def __init__( self, context ) -> None:
        """Console manager"""
        self.context    : 'EmberEngine' = context
        self.settings   : Settings = context.settings

        self.entries    : List[Console.Entry] = []

    def addEntry( self, type_id, message ):
        self.entries.append( {"type_id": type_id, "message": message} )
        pass

    def clear( self ):
        self.entries.clear()

    def getEntries( self ) -> List[Entry]:
        return self.entries