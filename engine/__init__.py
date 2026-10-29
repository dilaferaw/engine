"""Custom checkers engine (stdlib only). See the implementation spec."""

from engine.board import Board, Piece, is_death_square
from engine.constants import Kind, Player, other
from engine.legality import freeze_map, legal_moves
from engine.notation import Move
from engine.rules import is_draw, winner

__all__ = [
    "Board",
    "Piece",
    "Kind",
    "Player",
    "Move",
    "other",
    "is_death_square",
    "freeze_map",
    "legal_moves",
    "winner",
    "is_draw",
]
