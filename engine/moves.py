"""Quiet moves and capture enumeration. Implements R2, R3, R4, R5."""

from __future__ import annotations

from engine.board import Board, Piece, is_death_square
from engine.constants import Kind
from engine.geometry import DIRECTIONS, forward_directions, is_valid_square, step
from engine.notation import Move


def _require_piece(board: Board, sq: int) -> Piece:
    if not is_valid_square(sq):
        raise ValueError(f"square out of range 0..63: {sq!r}")
    piece = board.squares[sq]
    if piece is None:
        raise ValueError(f"no piece on square {sq}")
    return piece


def man_quiet_moves(board: Board, sq: int) -> list[Move]:
    """Forward one-step moves of a man; landing on death is legal, dies=True.

    Implements R2.1, R2.5, R2.6, R4.3.
    """
    piece = _require_piece(board, sq)
    moves: list[Move] = []
    for d in forward_directions(piece.player):
        to = step(sq, d)
        if to is None or board.squares[to] is not None:
            continue
        moves.append(Move(sq, to, [], is_death_square(to, board)))
    return moves


def king_quiet_moves(board: Board, sq: int) -> list[Move]:
    """Sliding moves of a king in all four directions until blocked.

    Implements R2.3, R2.5, R2.6, R4.3, R5.3 (a king may leave its promotion square).
    """
    _require_piece(board, sq)
    moves: list[Move] = []
    for d in DIRECTIONS:
        cur = step(sq, d)
        while cur is not None and board.squares[cur] is None:
            moves.append(Move(sq, cur, [], is_death_square(cur, board)))
            cur = step(cur, d)
    return moves


def quiet_moves(board: Board, sq: int) -> list[Move]:
    """Quiet moves for whatever piece stands on sq."""
    piece = _require_piece(board, sq)
    if piece.kind is Kind.MAN:
        return man_quiet_moves(board, sq)
    return king_quiet_moves(board, sq)


def capture_sequences(board: Board, origin: int) -> list[Move]:
    """All maximal capture sequences (length >= 1) for the piece on origin.

    Implements R3.5-R3.7, R2.4.
    Decisions: A4 a king may land on any empty square beyond the victim; A5
    captured pieces stay on the board as blockers and cannot be captured twice;
    the origin square counts as empty but cannot be landed on again. A man that
    lands on its promotion square (a corner) has nowhere left to jump, so the
    sequence ends there naturally and needs no promotion special case.
    """
    piece = _require_piece(board, origin)
    results: list[Move] = []
    captured: list[int] = []
    visited: set[int] = {origin}

    def occupied(sq: int) -> bool:
        return sq != origin and board.squares[sq] is not None

    def capturable(sq: int) -> bool:
        p = board.squares[sq]
        return (
            sq != origin
            and p is not None
            and p.player is not piece.player
            and sq not in captured
        )

    def steps(pos: int) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for d in DIRECTIONS:
            if piece.kind is Kind.MAN:
                victim = step(pos, d)
                if victim is None:
                    continue
                land = step(victim, d)
                if land is None:
                    continue
                if capturable(victim) and not occupied(land) and land not in visited:
                    out.append((victim, land))
            else:
                cur = step(pos, d)
                found: int | None = None
                while cur is not None:
                    if occupied(cur):
                        if capturable(cur):
                            found = cur
                        break
                    cur = step(cur, d)
                if found is None:
                    continue
                land_sq = step(found, d)
                while land_sq is not None and not occupied(land_sq):
                    if land_sq not in visited:
                        out.append((found, land_sq))
                    land_sq = step(land_sq, d)
        return out

    def dfs(pos: int) -> None:
        options = steps(pos)
        if not options:
            if captured:
                results.append(Move(origin, pos, list(captured), False))
            return
        for victim, land in options:
            captured.append(victim)
            if is_death_square(land, board):
                # R3.5: sequence ends on a dying landing; prior captures still count.
                results.append(Move(origin, land, list(captured), True))
            else:
                visited.add(land)
                dfs(land)
                visited.discard(land)
            captured.pop()

    dfs(origin)
    return results


def captures_single(board: Board, sq: int) -> list[Move]:
    """Length-1 captures for one piece. DETECTION ONLY, never a legal move.

    Implements R3.1, R3.6, R6.1.
    """
    return [m for m in capture_sequences(board, sq) if m.length == 1]


def captures_multi(board: Board, sq: int) -> list[Move]:
    """Capture sequences of length >= 2 for one piece. Implements R3.1, R3.3, R3.5-R3.7."""
    return [m for m in capture_sequences(board, sq) if m.length >= 2]
