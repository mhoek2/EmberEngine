from typing import TYPE_CHECKING, List, TypedDict

from modules.settings import Settings

if TYPE_CHECKING:
    from main import EmberEngine

class Console:
    class Entry(TypedDict):
        type_id     : str
        message     : str
        traceback   : None
        _n_lines    : int   # imgui info

    def __init__( self, context ) -> None:
        """Console manager"""
        self.context    : 'EmberEngine' = context
        self.settings   : Settings = context.settings

        self.entries    : List[Console.Entry] = []

        self.ENTRY_TYPE_ERROR = 0
        self.ENTRY_TYPE_WARNING = 1

        self.entry_type_color = [
            (1.0, 0.0, 0.0),        # ENTRY_TYPE_ERROR
            (0, 1.0, 1.0)           # ENTRY_TYPE_WARNING
        ]

    def addEntry( self, type_id : int, traceback, e ):
        
        traceback_filtered = []
        _n_lines = 0
        # needs engine assets path too in lambda?
        for tb in filter( lambda x: str(self.settings.assets) in x, traceback ):
            _n_lines += tb.count("\n")
            traceback_filtered.append( tb )

        self.entries.append( {
            "type_id"   : type_id, 
            "message"   : e,
            "traceback" : traceback_filtered,
            "_n_lines"   : _n_lines,
        } )
        pass

    def clear( self ):
        self.entries.clear()

    def getEntries( self ) -> List[Entry]:
        return self.entries