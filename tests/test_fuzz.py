import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from engine.board import Board
from engine.constants import Player
from engine.geometry import STATIC_DEATH_SQUARES
from engine.legality import freeze_map, legal_moves
from engine.notation import Move
from engine.rules import winner


def _count(b: Board) -> int:
    return sum(1 for p in b.squares if p is not None)


def _independent_check(b: Board, m: Move) -> None:
    """Second, structurally independent legality check."""
    p = b.squares[m.from_sq]
    assert p is not None and p.player is b.turn
    assert b.squares[m.to_sq] is None
    assert len(set(m.captures)) == len(m.captures)
    for c in m.captures:
        v = b.squares[c]
        assert v is not None and v.player is not b.turn
    assert m.length == 0 or m.length >= 2
    if m.to_sq in STATIC_DEATH_SQUARES:
        assert m.dies


@pytest.mark.parametrize("seed", [1, 7, 42, 1234])
def test_poison_never_reverts_without_undo(seed: int) -> None:
    rng = random.Random(seed)
    board = Board.setup()
    prev_poison = dict(board.poisoned)
    for _ in range(60):
        moves = legal_moves(board)
        if not moves or winner(board) is not None:
            break
        before = board.to_dict()
        move = rng.choice(moves)
        board.apply(move)
        board.undo()
        assert board.to_dict() == before
        board.apply(move)
        for side in Player:
            if prev_poison[side]:
                assert board.poisoned[side]
        prev_poison = dict(board.poisoned)


@settings(max_examples=200, deadline=None)
@given(st.lists(st.integers(min_value=0, max_value=1000), max_size=60))
def test_random_playouts_preserve_invariants(choices: list[int]) -> None:
    board = Board.setup()
    for c in choices:
        if winner(board) is not None:
            break
        moves = legal_moves(board)
        if not moves:
            break
        assert len({m.length for m in moves}) == 1
        frozen = freeze_map(board)
        move = moves[c % len(moves)]
        assert not frozen[move.from_sq]
        _independent_check(board, move)
        before = board.to_dict()
        n_before = _count(board)
        dies = board.is_death_square(move.to_sq)
        board.apply(move)
        assert _count(board) <= n_before
        if dies:
            assert board.squares[move.to_sq] is None
        after = board.to_dict()
        board.undo()
        assert board.to_dict() == before
        board.apply(move)
        assert board.to_dict() == after
    assert board.turn in (Player.WHITE, Player.BLACK)
