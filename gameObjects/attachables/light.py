import enum

from modules.engineTypes import EngineTypes

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject

from dataclasses import dataclass, field

@dataclass(slots=True)
class Light:
    class Type_(enum.IntEnum):
        direct  = 0             # (= 0)
        spot    = enum.auto()   # (= 1)
        area    = enum.auto()   # (= 2)

    context         : "EmberEngine" = field( default=None )
    gameObject      : "GameObject"  = field( default=None )

    light_type      : Type_         = field( default=Type_.direct )
    light_color     : list[float]   = field( default_factory=lambda: [0.98, 1.0, 0.69] )
    radius          : float         = field( default=12.0 )
    intensity       : float         = field( default=1.0 )
   