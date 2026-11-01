"""Request-scoped dependencies and shared header parameters."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Header, Request

from engine.api.realtime import Broadcaster as BroadcasterImpl
from engine.matchmaking import LobbyService
from engine.storage import GameRepository

TokenHeader = Annotated[str | None, Header(alias="X-Player-Token")]
NameHeader = Annotated[str | None, Header(alias="X-Player-Name")]

def get_repository(request: Request) -> GameRepository:
    """The active game repository, set by ``create_app`` on ``app.state``."""
    repo = getattr(request.app.state, "repository", None)
    if repo is None:  # pragma: no cover - misconfiguration, not user input
        raise RuntimeError("no game repository configured")
    return cast(GameRepository, repo)


Repository = Annotated[GameRepository, Depends(get_repository)]


def get_lobby(request: Request) -> LobbyService:
    """The active matchmaking service, set by ``create_app``."""
    lobby = getattr(request.app.state, "lobby", None)
    if lobby is None:  # pragma: no cover - misconfiguration, not user input
        raise RuntimeError("no matchmaking service configured")
    return cast(LobbyService, lobby)


Lobby = Annotated[LobbyService, Depends(get_lobby)]


def get_broadcaster(request: Request) -> BroadcasterImpl:
    """The change fan-out, set by ``create_app``."""
    return cast(BroadcasterImpl, request.app.state.broadcaster)


Broadcaster = Annotated[BroadcasterImpl, Depends(get_broadcaster)]
