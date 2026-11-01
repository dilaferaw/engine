"""Process-local in-memory implementation of :class:`GameRepository`."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from engine.board import Board
from engine.notation import Move
from engine.rules import winner
from engine.storage.errors import GameFull, GameNotFound, NotASeat, NotYourTurn
from engine.storage.models import GameRecord, color_for, fresh_rematch

ChangeListener = Callable[[str, int], None]


class InMemoryGameStore:
    """Games held in a dict; lost when the process exits."""

    def __init__(self, on_change: ChangeListener | None = None) -> None:
        self._games: dict[str, GameRecord] = {}
        self.on_change = on_change

    def _changed(self, game_id: str, record: GameRecord) -> GameRecord:
        """Bump the version and tell any open event stream."""
        record.touch()
        if self.on_change is not None:
            self.on_change(game_id, record.version)
        return record

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
                raise GameFull("game is full")
            record.seats[free] = token
            record.remember_name(token, name)
            return self._changed(game_id, record)
        before = record.names.get(color_for(record.seats, token) or "")
        record.remember_name(token, name)
        if record.names.get(color_for(record.seats, token) or "") != before:
            self._changed(game_id, record)
        return record

    def play(self, game_id: str, token: str | None, move: Move) -> GameRecord:
        record = self.require(game_id)
        color = color_for(record.seats, token)
        if color is not None and color != record.board.turn.value:
            raise NotYourTurn("not your turn")
        record.board.apply(move)
        played = move.to_dict()
        played["player"] = color
        record.history.append(played)
        return self._changed(game_id, record)

    def undo(self, game_id: str) -> GameRecord:
        record = self.require(game_id)
        record.board.undo()
        if record.history:
            record.history.pop()
        record.rematch = fresh_rematch()
        return self._changed(game_id, record)

    def request_rematch(self, game_id: str, token: str | None) -> GameRecord:
        record = self.require(game_id)
        color = color_for(record.seats, token)
        if color is None:
            raise NotASeat("not a player in this game")
        record.rematch[color] = True
        record.rematch_declined = False
        if all(record.rematch.values()):
            record.reset()
        return self._changed(game_id, record)

    def decline_rematch(self, game_id: str, token: str | None) -> GameRecord:
        """Clear only this player's rematch flag; the other may still want one."""
        record = self.require(game_id)
        color = color_for(record.seats, token)
        if color is None:
            raise NotASeat("not a player in this game")
        other = "BLACK" if color == "WHITE" else "WHITE"
        if record.rematch[other]:
            # The opponent asked and this player refused: both clients head
            # back to the lobby.
            record.rematch_declined = True
        record.rematch[color] = False
        return self._changed(game_id, record)

    def leave(self, game_id: str, token: str | None) -> GameRecord:
        """Mark a seat gone; an unfinished game is forfeited to the other side."""
        record = self.require(game_id)
        color = color_for(record.seats, token)
        if color is None or record.left[color]:
            return record
        record.left[color] = True
        other_color = "BLACK" if color == "WHITE" else "WHITE"
        if not record.left[other_color] and winner(record.board) is None:
            record.forfeit = other_color
        return self._changed(game_id, record)

    def delete(self, game_id: str) -> None:
        self.require(game_id)
        del self._games[game_id]
