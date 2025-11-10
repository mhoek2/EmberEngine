from typing import TYPE_CHECKING, List, TypedDict
import enum

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
        """Console manager
        
        :param context: This is the main context of the application
        :type context: EmberEngine
        """
        self.context    : 'EmberEngine' = context
        self.settings   : Settings = context.settings

        self.entries    : List[Console.Entry] = []

        self._entry_type_color = [
            (0.0, 0.0, 0.0),         # Type_.none
            (1.0, 0.0, 0.0),         # Type_.error
            (0, 1.0, 1.0),           # Type_.warning
            (0, 0.6, 0.3),           # Type_.note
        ]

    # IntFlag is bitwise  (1 << index)
    # IntEnum is seqential
    class Type_(enum.IntEnum):
        none    = enum.auto()    # (= 0)
        error   = enum.auto()    # (= 1)
        warning = enum.auto()    # (= 2)
        note    = enum.auto()    # (= 3)

    def get_entry_color( self, entry : Entry ) -> None:
        """Get the color of a given entry"""
        return self._entry_type_color[ (entry["type_id"] - 1) ]
    

    def log( self, type_id : int, traceback : List[str], e : Exception ):
        """Add entry to the console entries buffer
        
        :param type_id: The type of a entry, Type_.error Type_.warning, or Type_.note
        :type type_id: int
        :param traceback: A list that contains detailed information of a raised Exception
        :type traceback: List[str]
        :param e: The final raised Exception
        :type e: Exception
        """
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

    def clear( self ):
        """Clear the console entries buffer"""
        self.entries.clear()

    def getEntries( self ) -> List[Entry]:
        """Get console entries buffer
        
        :return: A reference to the entries buffer
        :rtype: List[Entry]
        """
        return self.entries