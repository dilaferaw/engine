"""Reference-driven tests for engine.moves."""

from __future__ import annotations

from engine.board import Board
from engine.constants import Player
from engine.moves import (
    capture_sequences,
    captures_multi,
    captures_single,
    king_quiet_moves,
    man_quiet_moves,
    quiet_moves,
)
from deeps_tests.helpers import BM, BK, WM, WK, make_board


def test_man_quiet_only_forward() -> None:
    # White man at 27 (rank 3, file 3). Forward is SE/SW.
    # SE = (4, 2) = 20; SW = (2, 2) = 18. Backward NE/NW = 36/34 empty.
    board = make_board({27: WM})
    targets = {m.to_sq for m in man_quiet_moves(board, 27)}
    assert targets == {20, 18}


def test_king_quiet_slides_all_directions() -> None:
    board = make_board({27: WK})
    targets = {m.to_sq for m in king_quiet_moves(board, 27)}
    # NE: 36, 45, 54, 63
    # NW: 34, 41, 48
    # SE: 20, 13, 6
    # SW: 18, 9, 0
    expected = {
        36, 45, 54, 63,
        34, 41, 48,
        20, 13, 6,
        18, 9, 0,
    }
    assert targets == expected


def test_quiet_moves_dispatch() -> None:
    board = make_board({27: WM, 36: WK})
    assert quiet_moves(board, 27) == man_quiet_moves(board, 27)
    assert quiet_moves(board, 36) == king_quiet_moves(board, 36)


def test_man_captures_in_all_four_directions() -> None:
    # NE victim at 36, land 45
    board = make_board({27: WM, 36: BM})
    assert any(m.captures == [36] for m in capture_sequences(board, 27))
    # NW victim at 34, land 41
    board = make_board({27: WM, 34: BM})
    assert any(m.captures == [34] for m in capture_sequences(board, 27))
    # SE victim at 20, land 13
    board = make_board({27: WM, 20: BM})
    assert any(m.captures == [20] for m in capture_sequences(board, 27))
    # SW victim at 18, land 9
    board = make_board({27: WM, 18: BM})
    assert any(m.captures == [18] for m in capture_sequences(board, 27))


def test_king_cannot_jump_two_adjacent_pieces() -> None:
    # King at 0, two adjacent white men on the NE diagonal.
    board = make_board({0: BK, 9: WM, 18: WM})
    seqs = capture_sequences(board, 0)
    # Nothing capturable because the landing behind 9 is occupied.
    assert all(not m.captures for m in seqs)


def test_length_1_captures_are_returned_unfiltered() -> None:
    board = make_board({27: WM, 36: BM})
    singles = captures_single(board, 27)
    multis = captures_multi(board, 27)
    assert len(singles) == 1
    assert singles[0].captures == [36]
    assert multis == []


def test_A5_captured_piece_blocks_king_return_slide() -> None:
    # King at 36, white at 45 (NE, capturable) and at 27 (SW).
    # After capturing 45 and landing on 54 or 63, the captured piece at 45
    # still blocks the SW return. Without A5 the king could slide through 45
    # and reach 27 for a length-2 chain. That must NOT happen here.
    board = make_board({36: BK, 45: WM, 27: WM})
    seqs = capture_sequences(board, 36)
    via_45 = [m for m in seqs if 45 in m.captures]
    assert via_45, "king must be able to capture 45"
    for m in via_45:
        assert m.length == 1, f"A5 violated: {m}"


def test_capture_chain_ends_on_death_square() -> None:
    # White poisoned -> 63 is death. King at 0, victim at 9.
    # Flying capture can land on 18/27/36/45/54 or 63.
    # Landing on 63 must mark dies=True.
    board = make_board(
        {0: WK, 9: BM},
        turn=Player.WHITE,
        poisoned={Player.WHITE: True, Player.BLACK: False},
    )
    seqs = capture_sequences(board, 0)
    death_seqs = [m for m in seqs if m.dies]
    assert death_seqs, "expected a dies=True landing at 63"
    assert all(m.to_sq == 63 for m in death_seqs)
    assert all(m.captures == [9] for m in death_seqs)


def test_capture_requires_empty_landing_beyond_victim() -> None:
    board = make_board({27: WM, 36: BM, 45: BM})
    seqs = capture_sequences(board, 27)
    # The victim at 36 has no landing because 45 is occupied.
    # But capturing from 27 NE is impossible; and no other captures exist.
    assert all(m.captures != [36] for m in seqs)