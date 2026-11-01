"""Wire models for the matchmaking endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LobbyInvite(BaseModel):
    """Someone waiting who would like to play with you."""

    invite_id: str
    from_token: str
    from_name: str | None


class LobbyStatusModel(BaseModel):
    """Mirror of :class:`engine.matchmaking.models.LobbyStatus`."""

    state: str
    game_id: str | None = None
    invites: list[LobbyInvite] = Field(default_factory=list)
