"""Step 0 polling: state cache and the ``?after=`` unchanged response."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from engine.api import create_app
from engine.board import Board
from engine.notation import Move
from engine.storage.memory import InMemoryGameStore
from engine.storage.models import GameRecord


def _record() -> GameRecord:
    record = GameRecord(board=Board.setup())
    record.seats["WHITE"] = "alice"
    record.seats["BLACK"] = "bob"
    return record


def test_derived_is_cached_until_touch() -> None:
    record = _record()
    moves, frozen = record.derived()
    again_moves, again_frozen = record.derived()
    assert moves is again_moves
    assert frozen is again_frozen


def test_touch_recomputes_derived() -> None:
    record = _record()
    before, _ = record.derived()
    record.board.apply(Move(41, 32))
    record.touch()
    after, _ = record.derived()
    assert after is not before
    assert all(m.from_sq != 41 for m in after)


def test_derived_tracks_board_mutation_after_touch() -> None:
    record = _record()
    assert len(record.derived()[0]) == 7
    record.board.apply(Move(41, 32))
    record.touch()
    assert {m.from_sq for m in record.derived()[0]} == {16, 18, 20, 22}


def test_state_exposes_version() -> None:
    record = _record()
    assert record.state("g", "alice")["version"] == 0


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _game(client: TestClient) -> tuple[str, str]:
    game_id = client.post("/games", headers={"X-Player-Token": "alice"}).json()[
        "game_id"
    ]
    client.post(f"/games/{game_id}/join", headers={"X-Player-Token": "bob"})
    return game_id, game_id


def test_get_game_without_after_marks_changed(client: TestClient) -> None:
    game_id, _ = _game(client)
    body = client.get(f"/games/{game_id}").json()
    assert body["changed"] is True
    assert "board" in body


def test_unchanged_poll_is_tiny(client: TestClient) -> None:
    game_id, _ = _game(client)
    version = client.get(f"/games/{game_id}").json()["version"]
    body = client.get(f"/games/{game_id}?after={version}").json()
    assert body == {"changed": False, "version": version}


def test_move_invalidates_after(client: TestClient) -> None:
    game_id, _ = _game(client)
    version = client.get(f"/games/{game_id}").json()["version"]
    client.post(
        f"/games/{game_id}/moves",
        json={"from_sq": 41, "to_sq": 32, "captures": [], "dies": False},
        headers={"X-Player-Token": "alice"},
    )
    body = client.get(f"/games/{game_id}?after={version}").json()
    assert body["changed"] is True
    assert body["move_count"] == 1
    assert body["version"] != version


def test_join_invalidates_after(client: TestClient) -> None:
    game_id = client.post("/games", headers={"X-Player-Token": "alice"}).json()[
        "game_id"
    ]
    version = client.get(f"/games/{game_id}").json()["version"]
    client.post(f"/games/{game_id}/join", headers={"X-Player-Token": "bob"})
    body = client.get(f"/games/{game_id}?after={version}").json()
    assert body["changed"] is True
    assert body["seats"] == {"WHITE": True, "BLACK": True}


def test_rematch_and_undo_bump_version(client: TestClient) -> None:
    game_id, _ = _game(client)
    client.post(
        f"/games/{game_id}/moves",
        json={"from_sq": 41, "to_sq": 32, "captures": [], "dies": False},
        headers={"X-Player-Token": "alice"},
    )
    first = client.post(
        f"/games/{game_id}/rematch", headers={"X-Player-Token": "alice"}
    ).json()
    stale = client.get(f"/games/{game_id}?after={first['version']}").json()
    assert stale["changed"] is False
    undone = client.post(f"/games/{game_id}/undo").json()
    assert undone["version"] > first["version"]
    assert client.get(f"/games/{game_id}?after={first['version']}").json()[
        "changed"
    ] is True


def test_after_on_unknown_game_is_404(client: TestClient) -> None:
    assert client.get("/games/nope?after=3").status_code == 404


def test_store_bumps_version_on_every_mutation() -> None:
    store = InMemoryGameStore()
    game_id, record = store.create(Board.setup(), "alice", "Alice")
    seen = [record.version]
    store.join(game_id, "bob", "Bob")
    seen.append(record.version)
    store.play(game_id, "alice", Move(41, 32))
    seen.append(record.version)
    store.undo(game_id)
    seen.append(record.version)
    store.request_rematch(game_id, "alice")
    seen.append(record.version)
    store.decline_rematch(game_id, "alice")
    seen.append(record.version)
    assert seen == sorted(set(seen))
