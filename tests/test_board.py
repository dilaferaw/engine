import json

import pytest

from engine.board import Board, Piece, is_death_square
from engine.constants import Kind, Player
from engine.legality import legal_moves
from engine.moves import king_quiet_moves
from engine.notation import Move
from engine.rules import winner
from tests.helpers import make_board


def test_setup_has_twelve_pieces_per_side_on_correct_squares() -> None:
    b = Board.setup()
    assert b.pieces(Player.WHITE) == [41, 43, 45, 47, 48, 50, 52, 54, 57, 59, 61, 63]
    assert b.pieces(Player.BLACK) == [0, 2, 4, 6, 9, 11, 13, 15, 16, 18, 20, 22]
    assert b.turn is Player.WHITE


def test_board_serialization_roundtrips_and_is_json_safe() -> None:
    b = make_board(white=[9], black_kings=[63], poisoned={Player.BLACK: True})
    d = b.to_dict()
    json.dumps(d)
    assert Board.from_dict(d).to_dict() == d


def test_move_serialization_roundtrips() -> None:
    m = Move(45, 9, [36, 18], True)
    assert Move.from_dict(m.to_dict()) == m
    assert m.length == 2


def test_move_rejects_bad_squares() -> None:
    with pytest.raises(ValueError):
        Move(0, 64)
    with pytest.raises(ValueError):
        Move(5, 5)


def test_starting_position_has_seven_quiet_moves_for_white() -> None:
    assert len(legal_moves(Board.setup())) == 7


def test_apply_then_undo_restores_position_and_flips_turn() -> None:
    b = Board.setup()
    before = b.to_dict()
    b.apply(legal_moves(b)[0])
    assert b.turn is Player.BLACK
    b.undo()
    assert b.to_dict() == before


def test_undo_on_empty_history_raises() -> None:
    with pytest.raises(IndexError):
        Board.setup().undo()


def test_apply_rejects_illegal_move() -> None:
    with pytest.raises(ValueError):
        Board.setup().apply(Move(41, 25))


def test_voluntary_death_removes_piece_and_loses_last_piece() -> None:
    b = make_board(white=[9], black=[63])
    move = next(m for m in legal_moves(b) if m.to_sq == 2)
    assert move.dies
    b.apply(move)
    assert b.piece_at(2) is None and b.piece_at(9) is None
    assert b.turn is Player.BLACK
    assert winner(b) is Player.BLACK
    b.undo()
    assert b.piece_at(9) == Piece(Player.WHITE, Kind.MAN)


def test_promotion_alone_poisons_nobody_and_undo_restores_the_man() -> None:
    b = make_board(white=[9], black=[63])
    move = next(m for m in legal_moves(b) if m.to_sq == 0)
    assert not move.dies
    b.apply(move)
    assert b.piece_at(0) == Piece(Player.WHITE, Kind.KING)
    assert not any(b.poisoned.values())
    assert not is_death_square(0, b)
    b.undo()
    assert b.piece_at(9) == Piece(Player.WHITE, Kind.MAN)


def test_king_leaving_promotion_square_poisons_opponent_home_row() -> None:
    b = make_board(white_kings=[0], black=[63])
    b.apply(Move(0, 9))
    assert b.poisoned == {Player.WHITE: False, Player.BLACK: True}
    assert all(is_death_square(s, b) for s in (0, 2, 4, 6))
    b.undo()
    assert not any(b.poisoned.values())


def test_is_death_square_follows_poison_flags() -> None:
    b = make_board()
    assert is_death_square(2, b) and is_death_square(57, b)
    assert not is_death_square(0, b) and not is_death_square(63, b)
    b.poisoned[Player.BLACK] = True
    assert is_death_square(0, b) and not is_death_square(63, b)
    b.poisoned[Player.WHITE] = True
    assert is_death_square(63, b)


def test_black_king_leaving_a1_poisons_nobody() -> None:
    b = make_board(white=[63], black_kings=[0], turn=Player.BLACK)
    b.apply(Move(0, 9))
    assert not any(b.poisoned.values())


def test_king_that_left_promotion_square_dies_if_it_returns() -> None:
    b = make_board(white_kings=[9], black=[63], poisoned={Player.BLACK: True})
    back = next(m for m in king_quiet_moves(b, 9) if m.to_sq == 0)
    assert back.dies


def test_promotion_squares_are_safe_landings_until_their_side_is_poisoned() -> None:
    b = make_board(white=[63], black_kings=[9], turn=Player.BLACK)
    assert not next(m for m in king_quiet_moves(b, 9) if m.to_sq == 0).dies
    b2 = make_board(white_kings=[54], black=[0])
    assert not next(m for m in king_quiet_moves(b2, 54) if m.to_sq == 63).dies
