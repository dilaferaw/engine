"""Game records and the value objects shared by every storage backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.board import Board
from engine.legality import freeze_map, legal_moves
from engine.rules import is_draw, winner

COLORS = ("WHITE", "BLACK")

Seat = dict[str, str | None]


def fresh_seats() -> Seat:
    return {"WHITE": None, "BLACK": None}


def fresh_names() -> dict[str, str | None]:
    return {"WHITE": None, "BLACK": None}


def fresh_rematch() -> dict[str, bool]:
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

    def remember_name(self, token: str | None, name: str | None) -> None:
        cleaned = clean_name(name)
        color = color_for(self.seats, token)
        if cleaned is not None and color is not None:
            self.names[color] = cleaned

    def reset(self) -> None:
        """Start a fresh game with the same seats and names."""
        self.board = Board.setup()
        self.history = []
        self.rematch = fresh_rematch()

    def seat_of(self, token: str | None) -> str | None:
        return color_for(self.seats, token)

    def state(self, game_id: str, token: str | None) -> dict[str, Any]:
        """Serialize for the wire, from the perspective of ``token``."""
        result = winner(self.board)
        return {
            "game_id": game_id,
            "board": self.board.to_dict(),
            "legal_moves": [m.to_dict() for m in legal_moves(self.board)],
            "freeze": {
                str(sq): frozen for sq, frozen in freeze_map(self.board).items()
            },
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
        }
