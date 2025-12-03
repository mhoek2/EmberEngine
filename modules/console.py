from typing import TYPE_CHECKING, overload, List, TypedDict, Optional, Union
import enum

from modules.settings import Settings

if TYPE_CHECKING:
    from main import EmberEngine

import inspect

class Console:
    class Entry(TypedDict):
        type_id     : str
        message     : str
        traceback   : None
        _n_lines    : int   # imgui info

    # IntFlag is bitwise  (1 << index)
    # IntEnum is seqential
    class Type_(enum.IntEnum):
        none    = enum.auto()    # (= 0)
        error   = enum.auto()    # (= 1)
        warning = enum.auto()    # (= 2)
        note    = enum.auto()    # (= 3)

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
            (1.00, 0.27, 0.23),      # Type_.error
            (1.00, 0.78, 0.20),      # Type_.warning
            (0.38, 0.82, 0.32),      # Type_.note
        ]

    def get_entry_color( self, entry : Entry ) -> None:
        """Get the color of a given entry"""
        return self._entry_type_color[ (entry["type_id"] - 1) ]
    
    @overload
    def log( self, message : str ) -> None: ...

    @overload
    def log( self, message : str, log_type : Type_  ) -> None: ...

    @overload
    def log( self, message : str, log_type : Type_, stack : list[str]  ) -> None: ...

    def log( self, 
             message    : str,
             log_type   : Optional[Type_] = None, 
             stack      : Optional[List[str]] = None
        ) -> None:
        """Add entry to the console entries buffer
        
        :param log_type: The type of a entry, Type_.error Type_.warning, or Type_.note
        :type log_type: Console.Type_
        :param stack: A list that contains detailed information of a raised Exception
        :type stack: List[str]
        :param message: The message of the entry
        :type message: str
        """

        traceback_filtered = []

        # simple log overload
        if log_type is None and stack is None:
            #message = message
            log_type   = self.Type_.none
            stack   = []

        if not isinstance(stack, list) or not isinstance(log_type, self.Type_):
            __func_name__ = inspect.currentframe().f_code.co_name

            self.error( f"[{__func_name__}] Incorrect argument datatype" )
            return

        _n_lines = 0
        # needs engine assets path too in lambda?
        #for tb in filter( lambda x: str(self.settings.assets) in x, stack ):
        for tb in filter( lambda x: str(self.settings.rootdir) in x, stack ):
            _n_lines += tb.count("\n")
            traceback_filtered.append( tb )

        self.entries.append( {
            "type_id"   : log_type, 
            "message"   : message,
            "traceback" : traceback_filtered,
            "_n_lines"   : _n_lines,
        } )
        
    @overload
    def error( self, message : str ) -> None: ...

    @overload
    def error( self, message : str, stack : list[str] ) -> None: ...

    def error( self, 
               message : str,
               stack      : Optional[List[str]] = []
        ) -> None:
        """Wrapper method to add error entry"""
        self.log( 
            message, 
            log_type    = self.Type_.error, 
            stack       = stack
        )

    def warn( self, message : str ) -> None:
        """Wrapper method to add warning entry"""
        self.log( 
            message, 
            log_type    = self.Type_.warning, 
            stack       = []
        )

    def note( self, message : str ) -> None:
        """Wrapper method to add note entry"""
        self.log( 
            message, 
            log_type    = self.Type_.note, 
            stack       = []
        )

    def clear( self ):
        """Clear the console entries buffer"""
        self.entries.clear()

    def getEntries( self ) -> List[Entry]:
        """Get console entries buffer
        
        :return: A reference to the entries buffer
        :rtype: List[Entry]
        """
        return self.entries