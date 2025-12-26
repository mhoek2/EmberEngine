from pathlib import Path

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from main import EmberEngine
    from gameObjects.gameObject import GameObject

from dataclasses import dataclass, field

@dataclass(slots=True)
class Model:
    context         : "EmberEngine" = field( default=None )
    gameObject      : "GameObject"  = field( default=None )

    handle  : int   = field( default=-1 )
    path    : Path  = field( default_factory=Path )
   