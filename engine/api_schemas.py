"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from engine.board import Board
from engine.constants import Kind, Player
from engine.notation import Move


class PieceModel(BaseModel):
    """A piece on the board."""

    player: Player
    kind: Kind


class BoardModel(BaseModel):
    """Serialized board accepted by ``POST /games``."""

    squares: list[PieceModel | None] = Field(min_length=64, max_length=64)
    turn: Player = Player.WHITE
    poisoned: dict[str, bool] = Field(
        default_factory=lambda: {"WHITE": False, "BLACK": False}
    )


class MoveModel(BaseModel):
    """A move as sent by clients."""

    from_sq: int = Field(ge=0, le=63)
    to_sq: int = Field(ge=0, le=63)
    captures: list[int] = Field(default_factory=list)
    dies: bool = False

    def to_move(self) -> Move:
        """Convert to the engine's Move dataclass."""
        return Move(
            from_sq=self.from_sq,
            to_sq=self.to_sq,
            captures=list(self.captures),
            dies=self.dies,
        )


class GameCreated(BaseModel):
    """Response for game creation."""

    game_id: str


def board_from_model(model: BoardModel) -> Board:
    """Build a Board from a client-supplied model."""
    return Board.from_dict(model.model_dump(mode="json"))
