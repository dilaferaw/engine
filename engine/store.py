"""In-memory game store: seating, names, move history, rematch state.

Holds no HTTP concerns. The API layer maps the exceptions defined here onto
status codes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from engine.board import Board
from engine.legality import freeze_map, legal_moves
from engine.notation import Move
from engine.rules import is_draw, winner

COLORS = ("WHITE", "BLACK")

Seat = dict[str, str | None]


class GameNotFound(KeyError):
    """No game exists under the requested id."""


class GameFull(Exception):
    """Both seats are taken."""


class NotASeat(Exception):
    """The caller does not hold a seat in this game."""


class NotYourTurn(Exception):
    """The caller tried to move for the other side."""


def fresh_seats() -> Seat:
    return {"WHITE": None, "BLACK": None}


def fresh_names() -> dict[str, str | None]:
    return {"WHITE": None, "BLACK": None}


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
    rematch: dict[str, bool] = field(
        default_factory=lambda: {"WHITE": False, "BLACK": False}
    )

    def remember_name(self, token: str | None, name: str | None) -> None:
        cleaned = clean_name(name)
        color = color_for(self.seats, token)
        if cleaned is not None and color is not None:
            self.names[color] = cleaned

    def reset(self) -> None:
        """Start a fresh game with the same seats and names."""
        self.board = Board.setup()
        self.history = []
        self.rematch = {"WHITE": False, "BLACK": False}

    def state(self, game_id: str, token: str | None) -> dict[str, Any]:
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


class GameStore:
    """Process-local store of games, keyed by game id."""

    def __init__(self) -> None:
        self._games: dict[str, GameRecord] = {}

    def __len__(self) -> int:
        return len(self._games)

    def ids(self) -> list[str]:
        return list(self._games)

    def require(self, game_id: str) -> GameRecord:
        try:
            return self._games[game_id]
        except KeyError:
            raise GameNotFound(game_id) from None

    def create(
        self, board: Board, token: str | None, name: str | None
    ) -> tuple[str, GameRecord]:
        game_id = uuid4().hex
        record = GameRecord(board=board)
        if token:
            record.seats[board.turn.value] = token
        record.remember_name(token, name)
        self._games[game_id] = record
        return game_id, record

    def join(self, game_id: str, token: str, name: str | None) -> GameRecord:
        record = self.require(game_id)
        if color_for(record.seats, token) is None:
            free = next(
                (c for c, holder in record.seats.items() if holder is None), None
            )
            if free is None:
                raise GameFull
            record.seats[free] = token
        record.remember_name(token, name)
        return record

    def play(self, game_id: str, token: str | None, move: Move) -> GameRecord:
        record = self.require(game_id)
        color = color_for(record.seats, token)
        if color is not None and color != record.board.turn.value:
            raise NotYourTurn
        record.board.apply(move)
        played = move.to_dict()
        played["player"] = color
        record.history.append(played)
        return record

    def undo(self, game_id: str) -> GameRecord:
        record = self.require(game_id)
        record.board.undo()
        if record.history:
            record.history.pop()
        record.rematch = {"WHITE": False, "BLACK": False}
        return record

    def request_rematch(self, game_id: str, token: str | None) -> GameRecord:
        record = self.require(game_id)
        color = color_for(record.seats, token)
        if color is None:
            raise NotASeat
        record.rematch[color] = True
        if all(record.rematch.values()):
            record.reset()
        return record

    def decline_rematch(self, game_id: str) -> GameRecord:
        record = self.require(game_id)
        record.rematch = {"WHITE": False, "BLACK": False}
        return record

    def delete(self, game_id: str) -> None:
        self.require(game_id)
        del self._games[game_id]
