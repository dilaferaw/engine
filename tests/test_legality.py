from engine.legality import freeze_map, is_frozen, legal_moves
from engine.notation import Move
from tests.helpers import make_board


def test_mutual_freeze_freezes_both_pieces() -> None:
    f = freeze_map(make_board(white=[27], black=[18]))
    assert f[27] and f[18]


def test_frozen_piece_excluded_from_legal_moves() -> None:
    b = make_board(white=[27, 50], black=[18, 63])
    f = freeze_map(b)
    assert f[27] and not f[50]
    moves = legal_moves(b)
    assert moves and all(m.from_sq == 50 for m in moves)


def test_single_capture_is_illegal_so_no_moves_remain() -> None:
    assert legal_moves(make_board(white=[27], black=[18])) == []


def test_max_capture_rule_filters_shorter_sequences() -> None:
    b = make_board(white=[45], black=[36, 18, 38])
    assert legal_moves(b) == [Move(45, 9, [36, 18], False)]


def test_ties_for_max_length_are_all_returned() -> None:
    b = make_board(white=[45], black=[36, 18, 38, 22])
    assert sorted(m.to_sq for m in legal_moves(b)) == [9, 13]


def test_voluntary_death_moves_are_legal_quiet_moves() -> None:
    moves = legal_moves(make_board(white=[9], black=[63]))
    assert {(m.to_sq, m.dies) for m in moves} == {(0, False), (2, True)}


def test_is_frozen_agrees_with_freeze_map() -> None:
    b = make_board(white=[27, 50], black=[18, 63])
    assert all(is_frozen(b, sq) == f for sq, f in freeze_map(b).items())
