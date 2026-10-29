from engine.moves import captures_multi, captures_single, quiet_moves
from engine.notation import Move
from tests.helpers import make_board


def test_white_man_moves_toward_lower_ranks_only() -> None:
    b = make_board(white=[27], black=[63])
    assert {m.to_sq for m in quiet_moves(b, 27)} == {18, 20}


def test_black_man_moves_toward_higher_ranks_only() -> None:
    b = make_board(white=[63], black=[27])
    assert {m.to_sq for m in quiet_moves(b, 27)} == {34, 36}


def test_man_blocked_by_pieces_and_edge() -> None:
    assert quiet_moves(make_board(white=[27, 18, 20]), 27) == []
    assert {m.to_sq for m in quiet_moves(make_board(white=[32], black=[63]), 32)} == {
        25
    }


def test_single_capture_detected_forward_and_backward_but_not_multi() -> None:
    b = make_board(white=[27], black=[18])
    assert captures_single(b, 27) == [Move(27, 9, [18], False)]
    assert captures_multi(b, 27) == []
    b2 = make_board(white=[27], black=[36])
    assert captures_single(b2, 27) == [Move(27, 45, [36], False)]


def test_double_capture_is_found() -> None:
    b = make_board(white=[45], black=[36, 18])
    assert captures_multi(b, 45) == [Move(45, 9, [36, 18], False)]


def test_capture_sequence_ends_on_death_landing_and_counts_prior_captures() -> None:
    b = make_board(white=[27], black=[36, 52, 50])
    assert captures_multi(b, 27) == [Move(27, 59, [36, 52], True)]


def test_flying_king_may_land_on_any_empty_square_beyond_victim() -> None:
    b = make_board(white_kings=[0], black=[27])
    assert sorted(m.to_sq for m in captures_single(b, 0)) == [36, 45, 54, 63]
    assert captures_multi(b, 0) == []


def test_king_cannot_capture_through_a_second_piece() -> None:
    b = make_board(white_kings=[0], black=[27, 36])
    assert captures_single(b, 0) == [] and captures_multi(b, 0) == []


def test_king_double_capture_at_distance() -> None:
    b = make_board(white_kings=[0], black=[18, 34])
    got = {(m.to_sq, tuple(m.captures)) for m in captures_multi(b, 0)}
    assert got == {(41, (18, 34)), (48, (18, 34))}


def test_captured_piece_is_never_captured_twice() -> None:
    b = make_board(white_kings=[0], black=[27, 45])
    got = {(m.to_sq, tuple(m.captures)) for m in captures_multi(b, 0)}
    assert got == {(54, (27, 45)), (63, (27, 45))}


def test_capture_may_land_on_promotion_square() -> None:
    b = make_board(white=[18], black=[9])
    assert captures_single(b, 18) == [Move(18, 0, [9], False)]
