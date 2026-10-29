"""Reference-driven tests for engine.board."""

from __future__ import annotations

import pytest

from engine.board import Board, is_death_square
from engine.constants import Player
from engine.notation import Move
from tests.helpers import BM, BK, WM, WK, make_board


def test_setup_piece_counts_and_positions() -> None:
    board = Board.setup()
    white = set(board.pieces(Player.WHITE))
    black = set(board.pieces(Player.BLACK))
    # Dark squares on ranks 5-7 for White, 0-2 for Black.
    expected_white = {
        r * 8 + f
        for r in (5, 6, 7)
        for f in range(8)
        if (f + r) % 2 == 0
    }
    expected_black = {
        r * 8 + f
        for r in (0, 1, 2)
        for f in range(8)
        if (f + r) % 2 == 0
    }
    assert white == expected_white
    assert black == expected_black
    assert board.turn is Player.WHITE
    assert board.poisoned == {Player.WHITE: False, Player.BLACK: False}


def test_copy_is_independent() -> None:
    board = Board.setup()
    copy = board.copy()
    copy.squares[0] = BM
    assert board.squares[0] is None


def test_piece_at_validation() -> None:
    board = Board.setup()
    with pytest.raises(ValueError):
        board.piece_at(-1)
    with pytest.raises(ValueError):
        board.piece_at(64)


def test_board_invalid_length() -> None:
    with pytest.raises(ValueError):
        Board(squares=[None] * 63)


def test_undo_on_empty_history() -> None:
    board = Board.setup()
    with pytest.raises(IndexError):
        board.undo()


def test_apply_undo_restores_state() -> None:
    board = Board.setup()
    before = board.to_dict()
    move = Move(41, 34, [], False)  # White man at 41 (b6) SE to 34
    board.apply(move, validate=False)
    board.undo()
    assert board.to_dict() == before


def test_board_and_move_dict_roundtrip() -> None:
    board = Board.setup()
    restored = Board.from_dict(board.to_dict())
    assert restored.squares == board.squares
    assert restored.turn == board.turn
    assert restored.poisoned == board.poisoned
    assert restored.history == []

    m = Move(10, 14, [13], False)
    m2 = Move.from_dict(m.to_dict())
    assert m2 == m


def test_move_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        Move(-1, 5)
    with pytest.raises(ValueError):
        Move(0, 64)
    with pytest.raises(ValueError):
        Move(5, 5)


def test_63_not_death_before_poison() -> None:
    board = make_board({})
    assert is_death_square(63, board) is False
    board.poisoned[Player.WHITE] = True
    assert is_death_square(63, board) is True


def test_0_not_death_before_poison() -> None:
    board = make_board({})
    assert is_death_square(0, board) is False
    board.poisoned[Player.BLACK] = True
    assert is_death_square(0, board) is True


def test_static_death_squares_always_death() -> None:
    board = make_board({})
    for sq in (2, 4, 6, 57, 59, 61):
        assert is_death_square(sq, board) is True


def test_man_promotes_on_promotion_square() -> None:
    board = make_board({11: WM}, turn=Player.WHITE)
    # 11 (rank 1, file 3) SW -> 2 is a static death square.
    # SE -> 4 is a static death square.
    # Pick a non-death promotion: 1 -> 0 is not playable (file 1, rank 0 is odd).
    # Use 9 -> 0 instead (rank 1, file 1, playable).
    board = make_board({9: WM}, turn=Player.WHITE)
    board.apply(Move(9, 0, [], False))
    assert board.squares[0] is not None
    assert board.squares[0].kind.name == "KING"


def test_man_dies_on_death_square() -> None:
    board = make_board({11: WM}, turn=Player.WHITE)
    assert is_death_square(2, board) is True
    board.apply(Move(11, 2, [], True))
    assert board.squares[2] is None
    assert board.squares[11] is None


def test_king_leaving_63_poisons_white() -> None:
    board = make_board({63: BK}, turn=Player.BLACK)
    board.apply(Move(63, 54, [], False))
    assert board.poisoned[Player.WHITE] is True
    assert board.poisoned[Player.BLACK] is False


def test_king_leaving_0_poisons_black() -> None:
    board = make_board({0: WK}, turn=Player.WHITE)
    board.apply(Move(0, 9, [], False))
    assert board.poisoned[Player.BLACK] is True
    assert board.poisoned[Player.WHITE] is False