"""Reference-driven tests for engine.geometry."""

from __future__ import annotations

import pytest

from engine.constants import Player
from engine.geometry import (
    STATIC_DEATH_SQUARES,
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


def test_square_index_layout() -> None:
    assert square(0, 0) == 0  # a1
    assert square(7, 7) == 63  # h8
    assert file_of(63) == 7
    assert rank_of(63) == 7


def test_square_rejects_off_board() -> None:
    with pytest.raises(ValueError):
        square(-1, 0)
    with pytest.raises(ValueError):
        square(0, 8)


def test_is_valid_square() -> None:
    assert is_valid_square(0)
    assert is_valid_square(63)
    assert not is_valid_square(-1)
    assert not is_valid_square(64)
    assert not is_valid_square(True)  # bool is int, but our values still fit


def test_playable_parity() -> None:
    assert is_playable(0)  # 0+0 even
    assert is_playable(63)  # 7+7 even
    assert not is_playable(1)  # 1+0 odd
    assert not is_playable(8)  # 0+1 odd


def test_forward_directions() -> None:
    assert forward_directions(Player.WHITE) == ((-1, -1), (1, -1))
    assert forward_directions(Player.BLACK) == ((1, 1), (-1, 1))


def test_promotion_squares() -> None:
    assert promotion_square(Player.WHITE) == 0
    assert promotion_square(Player.BLACK) == 63


def test_home_rows() -> None:
    assert home_row(Player.WHITE) == frozenset({57, 59, 61, 63})
    assert home_row(Player.BLACK) == frozenset({0, 2, 4, 6})


def test_death_squares_per_player() -> None:
    # opponent home row minus own promotion square
    assert death_squares(Player.WHITE) == frozenset({2, 4, 6})
    assert death_squares(Player.BLACK) == frozenset({57, 59, 61})
    assert STATIC_DEATH_SQUARES == frozenset({2, 4, 6, 57, 59, 61})


def test_step_off_board_returns_none() -> None:
    assert step(0, (-1, -1)) is None
    assert step(63, (1, 1)) is None
    assert step(0, (1, 1)) == 9