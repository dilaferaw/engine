"""Server-sent events: push game state to a player instead of polling.

One connection per open game tab. The stream sends the full state whenever
``GameRecord.version`` changes and a comment line every ``KEEPALIVE_S`` so
proxies do not drop an idle connection.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from engine.api.deps import Broadcaster, Repository, TokenHeader
from engine.api.errors import translate
from engine.storage.errors import GameNotFound

router = APIRouter()

KEEPALIVE_S = 15.0
SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
}


def _frame(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.get("/games/{game_id}/events")
def game_events(
    repo: Repository,
    broadcaster: Broadcaster,
    game_id: str,
    token: TokenHeader = None,
) -> StreamingResponse:
    """Stream this game's state on every change until the client goes away."""
    with translate():  # 404 before the response starts, not mid-stream
        repo.require(game_id)

    def stream() -> Iterator[str]:
        cond = broadcaster.subscribe(game_id)
        try:
            sent = -1
            while True:
                try:
                    record = repo.require(game_id)
                except GameNotFound:
                    return
                if record.version != sent:
                    sent = record.version
                    yield _frame(record.state(game_id, token))
                broadcaster.wait(game_id, cond, sent, KEEPALIVE_S)
                if broadcaster.versions(game_id) <= sent:
                    yield ": keepalive\n\n"
        finally:
            broadcaster.unsubscribe(game_id, cond)

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers=SSE_HEADERS
    )
