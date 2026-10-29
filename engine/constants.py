"""Enums and board-size constants (spec sections 3, 12, 21.3)."""

from enum import Enum

BOARD_SIZE = 8
NUM_SQUARES = 64


class Player(str, Enum):
    """The two sides. JSON-safe string values."""

    WHITE = "WHITE"
    BLACK = "BLACK"


class Kind(str, Enum):
    """Piece kinds. JSON-safe string values."""

    MAN = "MAN"
    KING = "KING"


# Decision (spec 21.3): WHITE moves first.
STARTING_TURN = Player.WHITE


def other(player: Player) -> Player:
    """Return the opponent of player."""
    return Player.BLACK if player is Player.WHITE else Player.WHITE
