"""Freeze map and legal move generation. Implements R6 and R7."""

from __future__ import annotations

from engine.board import Board
from engine.moves import capture_sequences, quiet_moves
from engine.notation import Move


def _is_frozen(sequences: list[Move]) -> bool:
    """True iff every capture available to a piece is a single one (R6.1)."""
    return bool(sequences) and all(m.length == 1 for m in sequences)


def is_frozen(board: Board, sq: int) -> bool:
    """True iff the piece on sq is frozen this turn. Implements R6.1, R6.6."""
    return _is_frozen(capture_sequences(board, sq))


def freeze_map(board: Board) -> dict[int, bool]:
    """Frozen status per occupied square, recomputed each call (R6.1-R6.6)."""
    return {
        sq: is_frozen(board, sq)
        for sq, piece in enumerate(board.squares)
        if piece is not None
    }


def legal_moves(board: Board) -> list[Move]:
    """All legal moves for the side to move. Implements R7.1, R3.2-R3.4, R3.8, R6.2.

    Single pass over the mover's pieces: each piece's capture sequences are
    computed once and reused for both the freeze test and the capture list.
    """
    captures: list[Move] = []
    movable: list[int] = []
    for sq in board.pieces(board.turn):
        sequences = capture_sequences(board, sq)
        if _is_frozen(sequences):
            continue  # R6.2, R3.8: frozen pieces never move
        movable.append(sq)
        captures.extend(m for m in sequences if m.length >= 2)  # R3.1
    if captures:  # R3.2 forced, R3.3 max rule, R3.4 ties
        best = max(m.length for m in captures)
        return [m for m in captures if m.length == best]
    return [m for sq in movable for m in quiet_moves(board, sq)]  # R4.3


def check_legal(board: Board, move: Move) -> None:
    """Raise ValueError naming the violated rule if move is not legal (section 14)."""
    legal = legal_moves(board)
    if move in legal:
        return
    piece = board.squares[move.from_sq]
    if piece is None:
        raise ValueError(f"R7.1: no piece on {move.from_sq}")
    if piece.player is not board.turn:
        raise ValueError("R7.3: piece does not belong to the side to move")
    if is_frozen(board, move.from_sq):
        raise ValueError("R6.2: frozen piece cannot move")
    if legal and legal[0].length > 0:
        if move.length == 0:
            raise ValueError("R3.2: captures are forced")
        raise ValueError("R3.1/R3.3: not a legal maximal multi-capture")
    raise ValueError("R2/R4: move is not a legal move in this position")
