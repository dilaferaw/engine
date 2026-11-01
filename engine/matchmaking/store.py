"""The lobby state contract and its in-process implementation.

Stores hold data only; every matchmaking rule lives in ``service.py``. The
in-process store is the default for development and tests, and is correct
only when one process serves every request. ``RedisLobbyStore`` implements
the same contract for multi-worker deployments.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Collection
from dataclasses import dataclass
from typing import Protocol

from engine.matchmaking.models import Invite, Match, Queued

PRESENCE_TTL = 15.0
INVITE_TTL = 30.0
OUTCOME_TTL = 60.0


class LobbyStore(Protocol):
    """Shared matchmaking state."""

    def touch(self, token: str, name: str | None, *, busy: bool) -> None:
        """Record a heartbeat; ``busy`` players are never invited."""

    def forget(self, token: str) -> None:
        """Drop all state for ``token``."""

    def available(self, exclude: Collection[str] = ()) -> list[Queued]:
        """Fresh, idle players other than ``exclude``."""

    def enqueue(self, token: str, name: str | None) -> None:
        """Append ``token`` to the waiting queue if absent."""

    def queued(self, token: str) -> Queued | None:
        """The queue entry for ``token``, if any."""

    def waiting(self) -> list[Queued]:
        """Every live queue entry, oldest first."""

    def release(self, token: str) -> bool:
        """Remove ``token`` from the queue; whether it was there."""

    def claim_other(self, token: str) -> Queued | None:
        """Atomically take the oldest live queue entry other than ``token``."""

    def invite(self, receiver: str, invite: Invite) -> None:
        """Deliver ``invite``, replacing any earlier one from that sender."""

    def inbox(self, token: str) -> list[Invite]:
        """Live invites addressed to ``token``."""

    def take_invite(self, token: str, invite_id: str) -> Invite | None:
        """Remove and return an invite, or ``None`` when it is gone."""

    def drop_invite(self, token: str, invite_id: str) -> bool:
        """Discard an invite; whether it existed."""

    def clear_invites(self, token: str) -> None:
        """Discard every invite addressed to ``token``."""

    def set_outcome(self, token: str, match: Match) -> None:
        """Record the game ``token`` was placed into."""

    def pop_outcome(self, token: str) -> Match | None:
        """Consume the recorded game, if any."""


@dataclass
class _Presence:
    name: str | None
    busy: bool
    seen: float


class MemoryLobbyStore:
    """Lobby state in a dict; valid for a single process only."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._presence: dict[str, _Presence] = {}
        self._queue: list[Queued] = []
        self._inbox: dict[str, dict[str, tuple[Invite, float]]] = {}
        self._outcomes: dict[str, tuple[Match, float]] = {}

    def _live_presence(self, token: str) -> _Presence | None:
        presence = self._presence.get(token)
        if presence is None:
            return None
        if self._clock() - presence.seen > PRESENCE_TTL:
            del self._presence[token]
            return None
        return presence

    def touch(self, token: str, name: str | None, *, busy: bool) -> None:
        self._presence[token] = _Presence(name, busy, self._clock())

    def forget(self, token: str) -> None:
        self._presence.pop(token, None)
        self.release(token)
        self.clear_invites(token)
        self._outcomes.pop(token, None)

    def available(self, exclude: Collection[str] = ()) -> list[Queued]:
        out: list[Queued] = []
        for token in list(self._presence):
            presence = self._live_presence(token)
            if presence is None or presence.busy or token in exclude:
                continue
            out.append(Queued(token, presence.name))
        return out

    def enqueue(self, token: str, name: str | None) -> None:
        self._queue = [q for q in self._queue if q.token != token]
        self._queue.append(Queued(token, name))

    def queued(self, token: str) -> Queued | None:
        return next((q for q in self._queue if q.token == token), None)

    def waiting(self) -> list[Queued]:
        self._queue = [q for q in self._queue if self._live_presence(q.token)]
        return list(self._queue)

    def release(self, token: str) -> bool:
        before = len(self._queue)
        self._queue = [q for q in self._queue if q.token != token]
        return len(self._queue) != before

    def claim_other(self, token: str) -> Queued | None:
        for index, entry in enumerate(self._queue):
            if entry.token == token or self._live_presence(entry.token) is None:
                continue
            del self._queue[index]
            return entry
        return None

    def invite(self, receiver: str, invite: Invite) -> None:
        box = self._inbox.setdefault(receiver, {})
        for key, (existing, _) in list(box.items()):
            if existing.from_token == invite.from_token:
                del box[key]
        box[invite.invite_id] = (invite, self._clock() + INVITE_TTL)

    def inbox(self, token: str) -> list[Invite]:
        box = self._inbox.get(token, {})
        now = self._clock()
        for key, (_, expires) in list(box.items()):
            if expires <= now:
                del box[key]
        if not box:
            self._inbox.pop(token, None)
            return []
        return [invite for invite, _ in box.values()]

    def take_invite(self, token: str, invite_id: str) -> Invite | None:
        self.inbox(token)
        box = self._inbox.get(token, {})
        entry = box.pop(invite_id, None)
        return entry[0] if entry else None

    def drop_invite(self, token: str, invite_id: str) -> bool:
        self.inbox(token)
        box = self._inbox.get(token, {})
        return box.pop(invite_id, None) is not None

    def clear_invites(self, token: str) -> None:
        self._inbox.pop(token, None)

    def set_outcome(self, token: str, match: Match) -> None:
        self._outcomes[token] = (match, self._clock() + OUTCOME_TTL)

    def pop_outcome(self, token: str) -> Match | None:
        entry = self._outcomes.pop(token, None)
        if entry is None or entry[1] <= self._clock():
            return None
        return entry[0]
