"""Storage layer: game persistence behind a swappable interface.

``GameRepository`` (``base``) is the contract; ``InMemoryGameStore``
(``memory``) is the default backend. A database-backed implementation can be
added without touching ``engine.api``.
"""

from engine.storage.base import GameRepository
from engine.storage.errors import (
    GameFull,
    GameNotFound,
    NotASeat,
    NotYourTurn,
    StorageError,
)
from engine.storage.memory import InMemoryGameStore
from engine.storage.models import GameRecord, clean_name, color_for

__all__ = [
    "GameFull",
    "GameNotFound",
    "GameRecord",
    "GameRepository",
    "InMemoryGameStore",
    "NotASeat",
    "NotYourTurn",
    "StorageError",
    "clean_name",
    "color_for",
]
