"""The storage interface the API depends on.

Every backend (in-memory today, SQL later) implements :class:`GameRepository`.
Routes never touch a concrete store, so swapping implementations is a one-line
change in ``engine.api.app``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from engine.board import Board
from engine.notation import Move
from engine.storage.models import GameRecord


@runtime_checkable
class GameRepository(Protocol):
    """Storage contract for games."""

    def ids(self) -> list[str]:
        """All known game ids."""

    def require(self, game_id: str) -> GameRecord:
        """Fetch a game or raise :class:`~engine.storage.errors.GameNotFound`."""

    def create(
        self, board: Board, token: str | None, name: str | None
    ) -> tuple[str, GameRecord]:
        """Persist a new game and seat ``token`` on the side to move."""

    def join(self, game_id: str, token: str, name: str | None) -> GameRecord:
        """Seat ``token`` in a free seat, or raise ``GameFull``."""

    def play(self, game_id: str, token: str | None, move: Move) -> GameRecord:
        """Apply a move, or raise ``NotYourTurn`` / engine errors."""

    def undo(self, game_id: str) -> GameRecord:
        """Undo the last move; raises ``IndexError`` when there is none."""

    def request_rematch(self, game_id: str, token: str | None) -> GameRecord:
        """Flag a seat ready; resets the game when both are ready."""

    def decline_rematch(self, game_id: str, token: str | None) -> GameRecord:
        """Clear this player's ready flag; the other flag is left alone."""

    def leave(self, game_id: str, token: str | None) -> GameRecord:
        """Mark ``token``'s seat gone; forfeits an unfinished game to the other."""

    def delete(self, game_id: str) -> None:
        """Remove a game, or raise ``GameNotFound``."""
