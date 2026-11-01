"""Win and draw detection. Implements R8."""

from __future__ import annotations

from engine.board import Board
from engine.constants import Player, other
from engine.legality import legal_moves


def winner(board: Board) -> Player | None:
    """The side that has won, else None. Implements R8.1, R8.3.

    Elimination wins. Otherwise a side with pieces but no legal move on its
    turn loses: being unable to move is a loss, not a draw.
    """
    white = bool(board.pieces(Player.WHITE))
    black = bool(board.pieces(Player.BLACK))
    if white and not black:
        return Player.WHITE
    if black and not white:
        return Player.BLACK
    if white and black and not legal_moves(board):
        return other(board.turn)
    return None


def is_draw(board: Board) -> bool:
    """True only when neither side has a piece left. Implements R8.2, R8.3."""
    if winner(board) is not None:
        return False
    return not board.pieces(Player.WHITE) and not board.pieces(Player.BLACK)
