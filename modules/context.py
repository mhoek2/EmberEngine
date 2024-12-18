from typing import TYPE_CHECKING
from modules.renderer import Renderer
from modules.settings import Settings

if TYPE_CHECKING:
    from main import EmberEngine

class Context:
    def __init__( self, context ):
        self.context    : 'EmberEngine' = context
        self.renderer   : Renderer = context.renderer
        self.settings   : Settings = context.settings