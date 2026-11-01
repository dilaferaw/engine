from engine.constants import Player
from engine.legality import legal_moves
from engine.rules import is_draw, winner
from tests.helpers import make_board


def test_winner_is_last_side_with_pieces() -> None:
    assert winner(make_board(white=[27], black=[])) is Player.WHITE
    assert winner(make_board(white=[], black=[27])) is Player.BLACK
    assert winner(make_board(white=[27], black=[63])) is None


def test_side_without_legal_moves_loses() -> None:
    board = make_board(white=[27], black=[18])
    assert legal_moves(board) == []
    assert winner(board) is Player.BLACK
    assert not is_draw(board)


def test_stuck_black_on_its_turn_gives_white_the_win() -> None:
    assert winner(make_board(white=[27], black=[18], turn=Player.BLACK)) is Player.WHITE


def test_win_takes_precedence_over_draw() -> None:
    assert not is_draw(make_board(white=[], black=[27]))


def test_position_with_moves_is_not_a_draw() -> None:
    assert not is_draw(make_board(white=[27], black=[63]))


def test_both_sides_empty_after_mover_dies_capturing_last_piece_is_a_draw() -> None:
    b = make_board(white=[27], black=[36, 52])
    move = legal_moves(b)[0]
    assert move.dies and move.length == 2
    b.apply(move)
    assert winner(b) is None
    assert is_draw(b)
