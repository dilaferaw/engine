from engine.moves import (
    capture_sequences,
    captures_multi,
    captures_single,
    king_quiet_moves,
    man_quiet_moves,
    quiet_moves,
)
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


def test_king_quiet_slides_all_directions() -> None:
    b = make_board(white_kings=[27], black=[63])
    # NE stops before 63, which holds the black man.
    expected = {
        36, 45, 54,
        34, 41, 48,
        20, 13, 6,
        18, 9, 0,
    }
    assert {m.to_sq for m in king_quiet_moves(b, 27)} == expected


def test_quiet_moves_dispatch_on_kind() -> None:
    b = make_board(white=[27], white_kings=[36], black=[63])
    assert quiet_moves(b, 27) == man_quiet_moves(b, 27)
    assert quiet_moves(b, 36) == king_quiet_moves(b, 36)


def test_captured_piece_still_blocks_king_return_slide() -> None:
    # A5: the captured victim stays on the board until the sequence ends, so a
    # king that captures at 45 cannot slide back through it to reach 27.
    b = make_board(black_kings=[36], white=[45, 27])
    via_45 = [m for m in capture_sequences(b, 36) if 45 in m.captures]
    assert via_45, "king must be able to capture 45"
    assert all(m.length == 1 for m in via_45)


def test_capture_may_land_on_promotion_square() -> None:
    b = make_board(white=[18], black=[9])
    assert captures_single(b, 18) == [Move(18, 0, [9], False)]
