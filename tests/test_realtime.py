"""Step 1a: in-process broadcaster and the SSE game stream."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from engine.api import create_app
from engine.api.realtime import Broadcaster
from engine.storage.memory import InMemoryGameStore


def test_publish_wakes_waiting_stream() -> None:
    bus = Broadcaster()
    cond = bus.subscribe("g")
    woken = threading.Event()

    def watcher() -> None:
        bus.wait("g", cond, 0, 5.0)
        woken.set()

    thread = threading.Thread(target=watcher)
    thread.start()
    time.sleep(0.05)
    bus.publish("g", 1)
    assert woken.wait(2.0)
    thread.join(2.0)
    bus.unsubscribe("g", cond)


def test_wait_returns_immediately_for_already_seen_versions() -> None:
    bus = Broadcaster()
    cond = bus.subscribe("g")
    bus.publish("g", 3)
    start = time.monotonic()
    bus.wait("g", cond, 2, 5.0)
    assert time.monotonic() - start < 0.5
    bus.unsubscribe("g", cond)


def test_wait_times_out_without_a_publish() -> None:
    bus = Broadcaster()
    cond = bus.subscribe("g")
    start = time.monotonic()
    bus.wait("g", cond, 0, 0.05)
    assert time.monotonic() - start >= 0.05
    bus.unsubscribe("g", cond)


def test_unsubscribe_drops_the_game() -> None:
    bus = Broadcaster()
    cond = bus.subscribe("g")
    bus.publish("g", 2)
    bus.unsubscribe("g", cond)
    assert bus.versions("g") == 0


def test_versions_track_the_last_publish() -> None:
    bus = Broadcaster()
    assert bus.versions("g") == 0
    bus.publish("g", 7)
    assert bus.versions("g") == 7


def test_store_notifies_on_every_mutation() -> None:
    seen: list[tuple[str, int]] = []
    store = InMemoryGameStore(on_change=lambda gid, v: seen.append((gid, v)))
    game_id = ""
    from engine.board import Board
    from engine.notation import Move

    game_id, _ = store.create(Board.setup(), "alice", "Alice")
    store.join(game_id, "bob", "Bob")
    store.play(game_id, "alice", Move(41, 32))
    store.undo(game_id)
    store.request_rematch(game_id, "alice")
    store.decline_rematch(game_id, "alice")
    # create does not publish: no stream can be watching a brand-new id.
    assert [gid for gid, _ in seen] == [game_id] * 5
    versions = [v for _, v in seen]
    assert versions == sorted(set(versions))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


def _events(resp: object) -> Iterator[str]:
    return resp.iter_lines()  # type: ignore[attr-defined]


def test_events_streams_current_state_first(client: TestClient) -> None:
    game_id = client.post("/games").json()["game_id"]
    with client.stream("GET", f"/games/{game_id}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        line = next(resp.iter_lines())
        assert line.startswith("data: ")
        assert '"game_id"' in line


def test_events_pushes_after_a_move(client: TestClient) -> None:
    game_id = client.post("/games").json()["game_id"]
    with client.stream("GET", f"/games/{game_id}/events") as resp:
        lines = resp.iter_lines()
        first = next(lines)
        assert '"move_count": 0' in first or '"move_count":0' in first

        def move() -> None:
            time.sleep(0.2)
            client.post(
                f"/games/{game_id}/moves",
                json={"from_sq": 41, "to_sq": 32, "captures": [], "dies": False},
            )

        thread = threading.Thread(target=move)
        thread.start()
        pushed = next(line for line in lines if line.startswith("data: "))
        thread.join(2.0)
        assert pushed.startswith("data: ")
        assert '"move_count": 1' in pushed or '"move_count":1' in pushed


def test_events_unknown_game_is_404(client: TestClient) -> None:
    assert client.get("/games/nope/events").status_code == 404
