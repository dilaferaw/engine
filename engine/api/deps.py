"""Request-scoped dependencies and shared header parameters."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Header, Request

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
