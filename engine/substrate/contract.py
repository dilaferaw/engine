"""
Substrate Contract — C00 STUB
=============================
Defines the exact interface the Substrate must expose (Project Bible §1).

This file contains ONLY types, enums, method signatures, and docstrings.
No implementation. C01 will deliver the real Substrate against this contract.

If a wrapper around a library (py-draughts / pydraughts) cannot expose one
of these hooks, the agent layers a wrapper on top. The library is an
implementation detail; this contract is not.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------
# Enums — string-valued so JSON is readable (§7).
# ---------------------------------------------------------------------------


class Player(str, Enum):
    WHITE = "white"
    BLACK = "black"

    def opponent(self) -> Player:
        """The other player."""
        ...


class PieceType(str, Enum):
    MAN = "man"
    KING = "king"


# ---------------------------------------------------------------------------
# Piece — immutable.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Piece:
    """A single piece. Immutable: no in-place mutation; replace instead."""

    player: Player
    type: PieceType


# ---------------------------------------------------------------------------
# RawMove — the raw substrate move. No variant logic.
# ---------------------------------------------------------------------------


@dataclass
class RawMove:
    """
    A substrate move. No death, no freeze, no poison knowledge.

    ATTRIBUTES
    ----------
    from_sq : int
        Origin square index (0..63).
    to_sq : int
        Final landing square index.
    captured : list[int]
        Squares of captured pieces, in capture order. Empty for quiet moves.
        NOTE: these are the squares the captured PIECES stood on — they are
        NOT landing squares. Landing squares are in `via`.
    via : list[int]
        ALL landing squares, in order. via[0] == from_sq, via[-1] == to_sq.
    promotes : bool
        True iff a MAN lands on its promotion square (see OPEN CONTRACT
        QUESTION below for multi-capture semantics).

    INVARIANTS — the substrate guarantees these; the variant may rely on them
    ------------------------------------------------------------------------
    I1. len(via) == len(captured) + 1
    I2. via[0] == from_sq and via[-1] == to_sq
    I3. captured[i] is the piece captured by the jump that LANDS on
        via[i + 1]. I.e. the landing produced by capturing captured[0] is
        via[1]; the landing produced by captured[1] is via[2]; and so on.
    I4. Capture length := len(captured) == len(via) - 1.
            quiet move        -> 0   via = [from, to]
            length-1 capture  -> 1   via = [from, landing]
            length-k capture  -> k   via = [from, L1, ..., Lk]
    I5. I1–I4 hold for kings. A flying king jump is still one capture and
        one landing; landing squares are not required to be adjacent to the
        jumped piece or to each other.

    WHY I3 MATTERS (variant, C05)
    -----------------------------
    Given a death landing at via[i] (i >= 1), the number of pieces captured
    STRICTLY BEFORE that landing is i - 1. I3 is what makes that count
    computable. Note the edge case i == 1 (death on the first landing):
    i - 1 == 0, i.e. an effective capture of length zero.

    WORKED EXAMPLES (schematic, squares not real)
    ---------------------------------------------
        Quiet move:        from_sq=10 to_sq=14  captured=[]       via=[10,14]
        Length-1 capture:  from_sq=10 to_sq=17  captured=[13]     via=[10,17]
        Length-2 capture:  from_sq=10 to_sq=24  captured=[13,19]  via=[10,17,24]
        King fly-capture:  from_sq=3  to_sq=30  captured=[16]     via=[3,30]

    to_dict / from_dict are JSON-safe; from_dict raises ValueError on
    malformed input (including violated I1).
    """

    from_sq: int
    to_sq: int
    captured: list[int]
    via: list[int]
    promotes: bool


# ---------------------------------------------------------------------------
# SubstrateBoard — the substrate. Knows nothing about the variant.
# ---------------------------------------------------------------------------


class SubstrateBoard:
    """
    Standard American checkers board. Exposes the §1 contract.

    Invariants the substrate maintains:
      - 8x8 dark-square board, standard 12v12 start (via .start()).
      - Men move/capture forward; kings slide / fly all four diagonals.
      - Capture sequences generated recursively. Length-1 sequences are
        returned unfiltered (mandatory — freeze detection needs them).
      - apply_raw performs movement, capture removal, and standard
        man->king promotion. It does NOT touch poison, freeze, or death.
      - Internal stack supports undo of apply_raw only.
    """

    def __init__(self) -> None: ...

    # -- construction ------------------------------------------------------

    @classmethod
    def start(cls) -> SubstrateBoard:
        """Standard 12v12 starting position. White to move."""
        ...

    @classmethod
    def from_pieces(cls, pieces: dict[int, Piece], turn: Player) -> SubstrateBoard:
        """Arbitrary position for tests. `turn` is the side to move."""
        ...

    def clone(self) -> SubstrateBoard:
        """Deep copy. Independent state and undo stack."""
        ...

    # -- inspection --------------------------------------------------------

    @property
    def turn(self) -> Player:
        """Side to move."""
        ...

    def piece_at(self, sq: int) -> Piece | None:
        """Piece at square, or None. Raises ValueError if sq out of 0..63."""
        ...

    def pieces(self, player: Player) -> list[tuple[int, Piece]]:
        """All (square, piece) pairs for `player`."""
        ...

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> dict:
        """JSON-safe snapshot (board, turn, undo stack may be omitted)."""
        ...

    @classmethod
    def from_dict(cls, d: dict) -> SubstrateBoard:
        """Inverse of to_dict. Raises ValueError on malformed input."""
        ...

    # -- move generation (raw, unfiltered by variant rules) ----------------

    def quiet_moves(self, sq: int) -> list[RawMove]:
        """
        Standard quiet moves for the piece at sq. Kings slide, men move
        forward. NO death handling, NO freeze; may include moves landing on
        squares the variant considers death.

        TURN-AGNOSTIC: generates for the piece at sq regardless of whose
        turn it is. Raises ValueError if sq is out of range or empty.
        """

    def captures(self, sq: int) -> list[RawMove]:
        """
        ALL capture sequences for the piece at sq, INCLUDING length-1
        sequences (len(captured) == 1, invariant I4). Length-1 sequences are
        mandatory for freeze detection; they are not filtered out even though
        standard checkers forbids them as moves.

        TURN-AGNOSTIC: generates for the piece at sq regardless of whose
        turn it is. This is required because freeze_map(board) is computed
        board-wide, over both sides' pieces, before capture generation for
        the side to move. Raises ValueError if sq is out of range or empty.
        """

    # -- apply / undo (no variant logic) -----------------------------------

    def apply_raw(self, move: RawMove) -> None:
        """
        Apply a RawMove: move piece, remove captured pieces, promote a MAN
        landing on its promotion square. Pushes state for undo. Does NOT
        touch poison flags or handle death removal.
        Raises ValueError on illegal move for current turn / position.
        """
        ...

    def undo(self) -> None:
        """Undo the last apply_raw. Raises ValueError if stack is empty."""
        ...
