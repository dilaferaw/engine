"""Game records and the value objects shared by every storage backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.board import Board
from engine.constants import Player
from engine.legality import freeze_map, legal_moves
from engine.notation import Move
from engine.rules import is_draw, winner

COLORS = ("WHITE", "BLACK")

Seat = dict[str, str | None]


def fresh_seats() -> Seat:
    return {"WHITE": None, "BLACK": None}


def fresh_names() -> dict[str, str | None]:
    return {"WHITE": None, "BLACK": None}


def fresh_rematch() -> dict[str, bool]:
    return {"WHITE": False, "BLACK": False}


def fresh_left() -> dict[str, bool]:
    return {"WHITE": False, "BLACK": False}


def clean_name(name: str | None) -> str | None:
    if name is None:
        return None
    trimmed = name.strip()[:24]
    return trimmed or None


def color_for(seats: Seat, token: str | None) -> str | None:
    if not token:
        return None
    for color, holder in seats.items():
        if holder == token:
            return color
    return None


@dataclass
class GameRecord:
    """Everything the API needs to know about one game."""

    board: Board
    seats: Seat = field(default_factory=fresh_seats)
    names: dict[str, str | None] = field(default_factory=fresh_names)
    history: list[dict[str, Any]] = field(default_factory=list)
    rematch: dict[str, bool] = field(default_factory=fresh_rematch)
    left: dict[str, bool] = field(default_factory=fresh_left)
    forfeit: str | None = None
    version: int = 0
    _derived: tuple[int, list[Move], dict[int, bool]] | None = field(
        default=None, init=False, repr=False
    )

    def remember_name(self, token: str | None, name: str | None) -> None:
        cleaned = clean_name(name)
        color = color_for(self.seats, token)
        if cleaned is not None and color is not None and self.names[color] != cleaned:
            self.names[color] = cleaned

    def reset(self) -> None:
        """Start a fresh game with the same seats and names."""
        self.board = Board.setup()
        self.history = []
        self.rematch = fresh_rematch()
        self.left = fresh_left()
        self.forfeit = None
        self.touch()

    def touch(self) -> None:
        """Bump the version so pollers know something changed."""
        self.version += 1

    def derived(self) -> tuple[list[Move], dict[int, bool]]:
        """Legal moves and freeze map for this position, computed once.

        Polling asks for these repeatedly on unchanged positions; the cache is
        keyed on ``version``, so any mutation recomputes it.
        """
        if self._derived is None or self._derived[0] != self.version:
            self._derived = (
                self.version,
                legal_moves(self.board),
                freeze_map(self.board),
            )
        return self._derived[1], self._derived[2]

    def seat_of(self, token: str | None) -> str | None:
        return color_for(self.seats, token)

    def state(self, game_id: str, token: str | None) -> dict[str, Any]:
        """Serialize for the wire, from the perspective of ``token``."""
        result = winner(self.board)
        if result is None and self.forfeit is not None:
            result = Player(self.forfeit)
        moves, frozen = self.derived()
        return {
            "game_id": game_id,
            "version": self.version,
            "board": self.board.to_dict(),
            "legal_moves": [m.to_dict() for m in moves],
            "freeze": {str(sq): is_frozen for sq, is_frozen in frozen.items()},
            "winner": result.value if result is not None else None,
            "is_draw": is_draw(self.board),
            "seats": {
                color: holder is not None for color, holder in self.seats.items()
            },
            "your_color": color_for(self.seats, token),
            "names": {color: self.names.get(color) for color in COLORS},
            "history": list(self.history),
            "move_count": len(self.history),
            "game_over": result is not None or is_draw(self.board),
            "rematch": {color: self.rematch[color] for color in COLORS},
            "left": {color: self.left[color] for color in COLORS},
        }
