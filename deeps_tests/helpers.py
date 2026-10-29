"""Helpers for building board positions in deeps_tests."""

from __future__ import annotations

from engine.board import Board, Piece
from engine.constants import Kind, Player

# Immutable Piece singletons — Piece is a frozen dataclass.
WM = Piece(Player.WHITE, Kind.MAN)
WK = Piece(Player.WHITE, Kind.KING)
BM = Piece(Player.BLACK, Kind.MAN)
BK = Piece(Player.BLACK, Kind.KING)


def make_board(
    pieces: dict[int, Piece],
    turn: Player = Player.WHITE,
    poisoned: dict[Player, bool] | None = None,
) -> Board:
    """Construct a Board from a mapping of {square: Piece}."""
    squares: list[Piece | None] = [None] * 64
    for sq, piece in pieces.items():
        squares[sq] = piece
    board = Board(squares=squares, turn=turn)
    if poisoned is not None:
        board.poisoned = dict(poisoned)
    return board