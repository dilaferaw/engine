from engine.constants import Player
from engine.geometry import (
    NE,
    SW,
    death_squares,
    file_of,
    home_row,
    is_playable,
    promotion_square,
    rank_of,
    square,
    step,
)


def test_square_index_roundtrips_file_and_rank() -> None:
    for sq in range(64):
        assert square(file_of(sq), rank_of(sq)) == sq


def test_a1_and_h8_are_dark_and_there_are_32_playable_squares() -> None:
    assert is_playable(0) and is_playable(63)
    assert sum(is_playable(s) for s in range(64)) == 32


def test_step_stops_at_board_edge() -> None:
    assert step(0, SW) is None
    assert step(0, NE) == 9
    assert step(31, NE) is None


def test_death_squares_identity_holds_for_both_players() -> None:
    for p in (Player.WHITE, Player.BLACK):
        other = Player.BLACK if p is Player.WHITE else Player.WHITE
        assert death_squares(p) | {promotion_square(p)} == home_row(other)
    assert death_squares(Player.WHITE) == {2, 4, 6}
    assert death_squares(Player.BLACK) == {57, 59, 61}
