import pytest

from engine.constants import Player
from engine.geometry import (
    NE,
    STATIC_DEATH_SQUARES,
    SW,
    death_squares,
    file_of,
    forward_directions,
    home_row,
    is_playable,
    is_valid_square,
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


def test_square_index_layout_corners() -> None:
    assert square(0, 0) == 0
    assert square(7, 7) == 63
    assert file_of(63) == 7
    assert rank_of(63) == 7


def test_square_rejects_off_board_file_or_rank() -> None:
    with pytest.raises(ValueError):
        square(-1, 0)
    with pytest.raises(ValueError):
        square(0, 8)


def test_is_valid_square_bounds() -> None:
    assert is_valid_square(0)
    assert is_valid_square(63)
    assert not is_valid_square(-1)
    assert not is_valid_square(64)
    assert not is_valid_square("0")


def test_playable_parity_examples() -> None:
    assert is_playable(0)
    assert is_playable(63)
    assert not is_playable(1)
    assert not is_playable(8)


def test_forward_directions_are_opposite() -> None:
    assert forward_directions(Player.WHITE) == ((1, -1), (-1, -1))
    assert forward_directions(Player.BLACK) == ((1, 1), (-1, 1))


def test_promotion_squares_are_corners() -> None:
    assert promotion_square(Player.WHITE) == 0
    assert promotion_square(Player.BLACK) == 63


def test_home_rows_explicit() -> None:
    assert home_row(Player.WHITE) == frozenset({57, 59, 61, 63})
    assert home_row(Player.BLACK) == frozenset({0, 2, 4, 6})


def test_static_death_squares_set() -> None:
    assert STATIC_DEATH_SQUARES == frozenset({2, 4, 6, 57, 59, 61})


def test_step_off_board_returns_none() -> None:
    assert step(0, (-1, -1)) is None
    assert step(63, (1, 1)) is None
    assert step(0, (1, 1)) == 9
