"""Win and draw detection. Implements R8."""

from __future__ import annotations

from engine.board import Board
from engine.constants import Player
from engine.legality import legal_moves


def winner(board: Board) -> Player | None:
    """The last side with pieces, else None. Implements R8.1, R8.3."""
    white = bool(board.pieces(Player.WHITE))
    black = bool(board.pieces(Player.BLACK))
    if white and not black:
        return Player.WHITE
    if black and not white:
        return Player.BLACK
    return None


def is_draw(board: Board) -> bool:
    """True iff nobody has won and the side to move has no legal moves. Implements R8.2, R8.3."""
    if winner(board) is not None:
        return False
    return not legal_moves(board)
