from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from engine.api import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


def _new_game(client: TestClient) -> str:
    resp = client.post("/games")
    assert resp.status_code == 201
    return resp.json()["game_id"]


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_game_uses_starting_position(client: TestClient) -> None:
    game_id = _new_game(client)
    state = client.get(f"/games/{game_id}").json()
    assert state["board"]["turn"] == "WHITE"
    assert state["winner"] is None
    assert state["is_draw"] is False
    assert len(state["legal_moves"]) == 7
    assert state["board"]["squares"][41] == {"player": "WHITE", "kind": "MAN"}


def test_create_game_from_board(client: TestClient) -> None:
    squares = [None] * 64
    squares[27] = {"player": "WHITE", "kind": "MAN"}
    squares[28] = {"player": "BLACK", "kind": "MAN"}
    resp = client.post(
        "/games",
        json={
            "squares": squares,
            "turn": "WHITE",
            "poisoned": {"WHITE": False, "BLACK": False},
        },
    )
    assert resp.status_code == 201
    game_id = resp.json()["game_id"]
    state = client.get(f"/games/{game_id}").json()
    assert state["board"]["squares"][27] == {"player": "WHITE", "kind": "MAN"}


def test_create_game_rejects_bad_board(client: TestClient) -> None:
    resp = client.post(
        "/games",
        json={
            "squares": [None] * 63,
            "turn": "WHITE",
            "poisoned": {"WHITE": False, "BLACK": False},
        },
    )
    assert resp.status_code == 422


def test_unknown_game_is_404(client: TestClient) -> None:
    assert client.get("/games/nope").status_code == 404
    resp = client.post("/games/nope/moves", json={"from_sq": 0, "to_sq": 1})
    assert resp.status_code == 404


def test_list_games(client: TestClient) -> None:
    first = _new_game(client)
    second = _new_game(client)
    assert set(client.get("/games").json()) == {first, second}


def test_legal_moves_endpoint(client: TestClient) -> None:
    game_id = _new_game(client)
    moves = client.get(f"/games/{game_id}/moves").json()
    assert {m["from_sq"] for m in moves} == {41, 43, 45, 47}


def test_play_move_updates_state(client: TestClient) -> None:
    game_id = _new_game(client)
    resp = client.post(
        f"/games/{game_id}/moves",
        json={"from_sq": 41, "to_sq": 32, "captures": [], "dies": False},
    )
    assert resp.status_code == 200
    state = resp.json()
    assert state["board"]["turn"] == "BLACK"
    assert state["board"]["squares"][41] is None
    assert state["board"]["squares"][32] == {"player": "WHITE", "kind": "MAN"}


def test_play_illegal_move_is_400(client: TestClient) -> None:
    game_id = _new_game(client)
    resp = client.post(
        f"/games/{game_id}/moves",
        json={"from_sq": 36, "to_sq": 45, "captures": [], "dies": False},
    )
    assert resp.status_code == 400


def test_play_move_with_out_of_range_square_is_422(client: TestClient) -> None:
    game_id = _new_game(client)
    resp = client.post(f"/games/{game_id}/moves", json={"from_sq": 0, "to_sq": 99})
    assert resp.status_code == 422


def test_undo_restores_previous_position(client: TestClient) -> None:
    game_id = _new_game(client)
    before = client.get(f"/games/{game_id}").json()
    client.post(
        f"/games/{game_id}/moves",
        json={"from_sq": 41, "to_sq": 32, "captures": [], "dies": False},
    )
    resp = client.post(f"/games/{game_id}/undo")
    assert resp.status_code == 200
    assert resp.json()["board"] == before["board"]


def test_undo_without_history_is_409(client: TestClient) -> None:
    game_id = _new_game(client)
    assert client.post(f"/games/{game_id}/undo").status_code == 409


def test_delete_game(client: TestClient) -> None:
    game_id = _new_game(client)
    assert client.delete(f"/games/{game_id}").status_code == 204
    assert client.get(f"/games/{game_id}").status_code == 404


def test_join_assigns_second_seat(client: TestClient) -> None:
    game_id = client.post(
        "/games", headers={"X-Player-Token": "alice"}
    ).json()["game_id"]
    alice = client.get(f"/games/{game_id}", headers={"X-Player-Token": "alice"}).json()
    assert alice["seats"] == {"WHITE": True, "BLACK": False}
    assert alice["your_color"] == "WHITE"
    bob = client.post(
        f"/games/{game_id}/join", headers={"X-Player-Token": "bob"}
    )
    assert bob.status_code == 200
    assert bob.json()["your_color"] == "BLACK"
    assert bob.json()["seats"] == {"WHITE": True, "BLACK": True}


def test_join_rejects_full_game(client: TestClient) -> None:
    game_id = client.post(
        "/games", headers={"X-Player-Token": "alice"}
    ).json()["game_id"]
    client.post(f"/games/{game_id}/join", headers={"X-Player-Token": "bob"})
    resp = client.post(f"/games/{game_id}/join", headers={"X-Player-Token": "carol"})
    assert resp.status_code == 409


def test_move_rejected_out_of_turn(client: TestClient) -> None:
    game_id = client.post(
        "/games", headers={"X-Player-Token": "alice"}
    ).json()["game_id"]
    client.post(f"/games/{game_id}/join", headers={"X-Player-Token": "bob"})
    resp = client.post(
        f"/games/{game_id}/moves",
        json={"from_sq": 41, "to_sq": 32, "captures": [], "dies": False},
        headers={"X-Player-Token": "bob"},
    )
    assert resp.status_code == 403


def test_rematch_resets_after_both_accept(client: TestClient) -> None:
    game_id = client.post(
        "/games", headers={"X-Player-Token": "alice"}
    ).json()["game_id"]
    client.post(f"/games/{game_id}/join", headers={"X-Player-Token": "bob"})
    client.post(
        f"/games/{game_id}/moves",
        json={"from_sq": 41, "to_sq": 32},
        headers={"X-Player-Token": "alice"},
    )
    first = client.post(
        f"/games/{game_id}/rematch", headers={"X-Player-Token": "alice"}
    ).json()
    assert first["rematch"] == {"WHITE": True, "BLACK": False}
    assert first["move_count"] == 1
    second = client.post(
        f"/games/{game_id}/rematch", headers={"X-Player-Token": "bob"}
    ).json()
    assert second["move_count"] == 0
    assert second["rematch"] == {"WHITE": False, "BLACK": False}
    assert second["board"]["turn"] == "WHITE"
    assert second["board"]["squares"][41] == {"player": "WHITE", "kind": "MAN"}


def test_rematch_requires_a_seat(client: TestClient) -> None:
    game_id = client.post(
        "/games", headers={"X-Player-Token": "alice"}
    ).json()["game_id"]
    resp = client.post(
        f"/games/{game_id}/rematch", headers={"X-Player-Token": "eve"}
    )
    assert resp.status_code == 403


def test_decline_rematch_clears_requests(client: TestClient) -> None:
    game_id = client.post(
        "/games", headers={"X-Player-Token": "alice"}
    ).json()["game_id"]
    client.post(f"/games/{game_id}/join", headers={"X-Player-Token": "bob"})
    client.post(
        f"/games/{game_id}/rematch", headers={"X-Player-Token": "alice"}
    )
    cleared = client.post(
        f"/games/{game_id}/rematch/decline", headers={"X-Player-Token": "bob"}
    ).json()
    assert cleared["rematch"] == {"WHITE": False, "BLACK": False}


def test_forced_multi_capture_is_the_only_legal_move(client: TestClient) -> None:
    squares = [None] * 64
    squares[41] = {"player": "WHITE", "kind": "MAN"}
    squares[34] = {"player": "BLACK", "kind": "MAN"}
    squares[20] = {"player": "BLACK", "kind": "MAN"}
    game_id = client.post(
        "/games",
        json={
            "squares": squares,
            "turn": "WHITE",
            "poisoned": {"WHITE": False, "BLACK": False},
        },
    ).json()["game_id"]
    moves = client.get(f"/games/{game_id}/moves").json()
    assert len(moves) == 1
    assert moves[0]["from_sq"] == 41
    assert moves[0]["to_sq"] == 13
    assert moves[0]["captures"] == [34, 20]
