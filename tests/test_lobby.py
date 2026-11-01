"""Matchmaking: two creators pair up, invites prompt idle players."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from engine.api import create_app
from engine.matchmaking import LobbyService, MemoryLobbyStore
from engine.storage import InMemoryGameStore


def _client() -> TestClient:
    return TestClient(create_app(serve_spa=False))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with _client() as c:
        yield c


def _head(token: str, name: str | None = None) -> dict[str, str]:
    headers = {"X-Player-Token": token}
    if name:
        headers["X-Player-Name"] = name
    return headers


def _status(client: TestClient, token: str) -> dict[str, object]:
    resp = client.get("/lobby/status", headers=_head(token))
    assert resp.status_code == 200
    return resp.json()


def test_heartbeat_requires_token(client: TestClient) -> None:
    assert client.post("/lobby/heartbeat").status_code == 400


def test_idle_by_default(client: TestClient) -> None:
    client.post("/lobby/heartbeat", headers=_head("alice"))
    assert _status(client, "alice") == {
        "state": "idle",
        "game_id": None,
        "invites": [],
    }


def test_two_creates_pair_into_one_game(client: TestClient) -> None:
    client.post("/lobby/heartbeat", headers=_head("alice"))
    client.post("/lobby/heartbeat", headers=_head("bob"))
    first = client.post("/lobby/create", headers=_head("alice")).json()
    assert first["state"] == "waiting"
    second = client.post("/lobby/create", headers=_head("bob")).json()
    assert second["state"] == "matched"
    alice = _status(client, "alice")
    assert alice["state"] == "matched"
    assert alice["game_id"] == second["game_id"]
    state = client.get(
        f"/games/{alice['game_id']}", headers=_head("bob")
    ).json()
    assert state["seats"] == {"WHITE": True, "BLACK": True}
    # Whoever presses create second takes the empty game's first seat.
    assert state["your_color"] == "WHITE"
    alice_state = client.get(
        f"/games/{alice['game_id']}", headers=_head("alice")
    ).json()
    assert alice_state["your_color"] == "BLACK"


def test_create_invites_idle_players(client: TestClient) -> None:
    client.post("/lobby/heartbeat", headers=_head("alice"))
    client.post("/lobby/heartbeat", headers=_head("bob", "Bob"))
    client.post("/lobby/create", headers=_head("alice", "Alice"))
    invites = _status(client, "bob")["invites"]
    assert isinstance(invites, list) and len(invites) == 1
    invite = invites[0]
    assert invite["from_token"] == "alice"
    assert invite["from_name"] == "Alice"


def test_accept_sends_both_players_to_the_game(client: TestClient) -> None:
    client.post("/lobby/heartbeat", headers=_head("alice"))
    client.post("/lobby/heartbeat", headers=_head("bob"))
    client.post("/lobby/create", headers=_head("alice"))
    invite = _status(client, "bob")["invites"][0]
    accepted = client.post(
        f"/lobby/invites/{invite['invite_id']}/accept", headers=_head("bob")
    ).json()
    assert accepted["state"] == "matched"
    alice = _status(client, "alice")
    assert alice["state"] == "matched"
    assert alice["game_id"] == accepted["game_id"]


def test_decline_removes_invite(client: TestClient) -> None:
    client.post("/lobby/heartbeat", headers=_head("alice"))
    client.post("/lobby/heartbeat", headers=_head("bob"))
    client.post("/lobby/create", headers=_head("alice"))
    invite = _status(client, "bob")["invites"][0]
    resp = client.post(
        f"/lobby/invites/{invite['invite_id']}/decline", headers=_head("bob")
    )
    assert resp.status_code == 204
    assert _status(client, "bob")["state"] == "idle"


def test_stale_invite_is_gone_after_cancel(client: TestClient) -> None:
    client.post("/lobby/heartbeat", headers=_head("alice"))
    client.post("/lobby/heartbeat", headers=_head("bob"))
    client.post("/lobby/create", headers=_head("alice"))
    invite = _status(client, "bob")["invites"][0]
    client.post("/lobby/cancel", headers=_head("alice"))
    resp = client.post(
        f"/lobby/invites/{invite['invite_id']}/accept", headers=_head("bob")
    )
    assert resp.status_code == 410


def test_busy_players_are_not_invited(client: TestClient) -> None:
    client.post("/lobby/heartbeat?busy=true", headers=_head("alice"))
    client.post("/lobby/heartbeat", headers=_head("bob"))
    client.post("/lobby/create", headers=_head("bob"))
    assert _status(client, "alice")["state"] == "idle"


def test_busy_heartbeat_stops_waiting(client: TestClient) -> None:
    client.post("/lobby/heartbeat", headers=_head("alice"))
    client.post("/lobby/create", headers=_head("alice"))
    client.post("/lobby/heartbeat?busy=true", headers=_head("alice"))
    assert _status(client, "alice")["state"] == "idle"


def test_leave_forgets_queue_and_invites(client: TestClient) -> None:
    client.post("/lobby/heartbeat", headers=_head("alice"))
    client.post("/lobby/heartbeat", headers=_head("bob"))
    client.post("/lobby/create", headers=_head("alice"))
    client.post("/lobby/leave", headers=_head("bob"))
    client.post("/lobby/heartbeat", headers=_head("carol"))
    assert _status(client, "bob")["state"] == "idle"
    assert _status(client, "carol")["invites"] == []


def test_service_with_injected_store() -> None:
    games = InMemoryGameStore()
    store = MemoryLobbyStore()
    lobby = LobbyService(games, store)
    assert lobby.status("alice").state == "idle"
    assert lobby.create("alice", "Alice").state == "waiting"
    assert lobby.leave("alice") is None
    assert len(games) == 0
