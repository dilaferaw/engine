"""Board state, apply/undo, death squares. Implements R1, R4, R5, sections 12-14."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.constants import NUM_SQUARES, STARTING_TURN, Kind, Player, other
from engine.geometry import (
    STATIC_DEATH_SQUARES,
    home_row,
    is_valid_square,
    promotion_square,
)
from engine.notation import Move


@dataclass(frozen=True)
class Piece:
    """A piece. Frozen/poisoned state is board state, not piece state (12)."""

    player: Player
    kind: Kind

    def to_dict(self) -> dict[str, str]:
        """JSON-safe dict (13)."""
        return {"player": self.player.value, "kind": self.kind.value}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Piece:
        """Rebuild from to_dict output (13)."""
        return cls(Player(d["player"]), Kind(d["kind"]))


def _fresh_poison() -> dict[Player, bool]:
    return {Player.WHITE: False, Player.BLACK: False}


@dataclass
class Board:
    """Single source of truth for a position (12)."""

    squares: list[Piece | None]
    turn: Player = STARTING_TURN
    poisoned: dict[Player, bool] = field(default_factory=_fresh_poison)
    history: list[tuple[list[Piece | None], Player, dict[Player, bool]]] = field(
        default_factory=list
    )

    def __post_init__(self) -> None:
        if len(self.squares) != NUM_SQUARES:
            raise ValueError(f"squares must have length {NUM_SQUARES}")

    @classmethod
    def setup(cls) -> Board:
        """Standard start (R1.2, 3.9, 21.3)."""
        squares: list[Piece | None] = [None] * NUM_SQUARES
        for rank in (5, 6, 7):
            for file in range(8):
                if (file + rank) % 2 == 0:
                    squares[rank * 8 + file] = Piece(Player.WHITE, Kind.MAN)
        for rank in (0, 1, 2):
            for file in range(8):
                if (file + rank) % 2 == 0:
                    squares[rank * 8 + file] = Piece(Player.BLACK, Kind.MAN)
        return cls(squares=squares, turn=STARTING_TURN)

    def copy(self) -> Board:
        """Copy of the position without history."""
        return Board(list(self.squares), self.turn, dict(self.poisoned))

    def piece_at(self, sq: int) -> Piece | None:
        """Piece on sq or None. Raises ValueError for an invalid square."""
        if not is_valid_square(sq):
            raise ValueError(f"square out of range 0..63: {sq!r}")
        return self.squares[sq]

    def pieces(self, player: Player) -> list[int]:
        """Sorted squares occupied by player."""
        return [
            sq
            for sq, p in enumerate(self.squares)
            if p is not None and p.player is player
        ]

    def is_death_square(self, sq: int) -> bool:
        """See module-level is_death_square (R4.5)."""
        return is_death_square(sq, self)

    def apply(self, move: Move, validate: bool = True) -> None:
        """Apply move, push history, flip turn.

        Implements R3, R4.1-R4.3, R5.1 and R5.2 (decision A2: a king leaving its
        promotion square poisons the opponent's home row).

        Raises ValueError if validate and the move is illegal (section 14).
        """
        if validate:
            from engine.legality import check_legal

            check_legal(self, move)
        piece = self.squares[move.from_sq]
        if piece is None:
            raise ValueError(f"no piece on from_sq {move.from_sq}")
        for c in move.captures:
            victim = self.squares[c]
            if victim is None or victim.player is piece.player:
                raise ValueError(f"R3: capture square {c} holds no enemy piece")
        if self.squares[move.to_sq] is not None:
            raise ValueError(f"to_sq {move.to_sq} is occupied")
        # R4.1: death is decided by the landing square in the pre-move position.
        dies = is_death_square(move.to_sq, self)
        self.history.append((list(self.squares), self.turn, dict(self.poisoned)))
        for c in move.captures:
            self.squares[c] = None
        self.squares[move.from_sq] = None
        if piece.kind is Kind.KING and move.from_sq == promotion_square(piece.player):
            self.poisoned[other(piece.player)] = True  # R5.2, A2: poison on leaving
        if not dies:
            promotes = piece.kind is Kind.MAN and move.to_sq == promotion_square(
                piece.player
            )
            self.squares[move.to_sq] = (
                Piece(piece.player, Kind.KING) if promotes else piece
            )  # R5.1
        self.turn = other(self.turn)

    def undo(self) -> None:
        """Reverse the last apply exactly. Raises IndexError on empty history (14)."""
        if not self.history:
            raise IndexError("undo() on empty history")
        self.squares, self.turn, self.poisoned = self.history.pop()

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe dict (13)."""
        return {
            "squares": [None if p is None else p.to_dict() for p in self.squares],
            "turn": self.turn.value,
            "poisoned": {
                "WHITE": self.poisoned[Player.WHITE],
                "BLACK": self.poisoned[Player.BLACK],
            },
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Board:
        """Rebuild from to_dict output; history is empty (13)."""
        return cls(
            squares=[None if p is None else Piece.from_dict(p) for p in d["squares"]],
            turn=Player(d["turn"]),
            poisoned={
                Player.WHITE: bool(d["poisoned"]["WHITE"]),
                Player.BLACK: bool(d["poisoned"]["BLACK"]),
            },
        )


def is_death_square(sq: int, board: Board) -> bool:
    """True iff landing on sq kills a piece now. Implements R4.5.

    A3 decision: promotion squares are NOT death until their side is poisoned.
    """
    if not is_valid_square(sq):
        raise ValueError(f"square out of range 0..63: {sq!r}")
    if sq in STATIC_DEATH_SQUARES:
        return True
    return any(
        board.poisoned[side] and sq in home_row(side)
        for side in (Player.WHITE, Player.BLACK)
    )
