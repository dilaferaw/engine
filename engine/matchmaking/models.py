"""Value objects exchanged by the lobby store and service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Queued:
    """A player known to be waiting for an opponent."""

    token: str
    name: str | None


@dataclass(frozen=True)
class Invite:
    """An offer from a waiting player to another available player."""

    invite_id: str
    from_token: str
    from_name: str | None


@dataclass(frozen=True)
class Match:
    """A game both players were placed into."""

    game_id: str


@dataclass(frozen=True)
class LobbyStatus:
    """What the client should show right now."""

    state: str  # idle | waiting | invited | matched
    game_id: str | None = None
    invites: tuple[Invite, ...] = ()
