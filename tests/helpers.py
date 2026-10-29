"""Explicit board construction for unit tests."""

from collections.abc import Iterable

from engine.board import Board, Piece
from engine.constants import Kind, Player


def make_board(
    white: Iterable[int] = (),
    black: Iterable[int] = (),
    white_kings: Iterable[int] = (),
    black_kings: Iterable[int] = (),
    turn: Player = Player.WHITE,
    poisoned: dict[Player, bool] | None = None,
) -> Board:
    """Build a Board from explicit square sets."""
    squares: list[Piece | None] = [None] * 64
    for sq in white:
        squares[sq] = Piece(Player.WHITE, Kind.MAN)
    for sq in black:
        squares[sq] = Piece(Player.BLACK, Kind.MAN)
    for sq in white_kings:
        squares[sq] = Piece(Player.WHITE, Kind.KING)
    for sq in black_kings:
        squares[sq] = Piece(Player.BLACK, Kind.KING)
    board = Board(squares=squares, turn=turn)
    if poisoned:
        board.poisoned.update(poisoned)
    return board
