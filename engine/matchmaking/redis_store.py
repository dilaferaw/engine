"""Lobby state in Redis: shared queue, presence and invites.

This is the message-broker cache: every API worker reads and writes the
same keys, so a player can create a game on one worker and accept it on
another. Presence and invites are *cache entries with a TTL*; the queue is
a Redis list and ``claim_other`` is a Lua script so two concurrent creates
can never claim the same partner. See ``MATCHMAKING.md`` for the tour.
"""

from __future__ import annotations

import json
from collections.abc import Collection
from typing import TYPE_CHECKING, Any, cast

from engine.matchmaking.models import Invite, Match, Queued
from engine.matchmaking.store import INVITE_TTL, OUTCOME_TTL, PRESENCE_TTL

if TYPE_CHECKING:  # pragma: no cover - typing only, redis is optional
    from redis import Redis

_CLAIM_OTHER = """
local queue = KEYS[1]
local me = ARGV[1]
local prefix = ARGV[2]
for _, token in ipairs(redis.call('LRANGE', queue, 0, -1)) do
  if token ~= me then
    local busy = redis.call('HGET', prefix .. 'presence:' .. token, 'busy')
    if busy == '0' then
      redis.call('LREM', queue, 0, token)
      return token
    end
  end
end
return false
"""


def _invite_json(invite: Invite) -> str:
    return json.dumps(
        {
            "invite_id": invite.invite_id,
            "from_token": invite.from_token,
            "from_name": invite.from_name,
        }
    )


def _invite_from_json(raw: str) -> Invite:
    data: dict[str, Any] = json.loads(raw)
    return Invite(data["invite_id"], data["from_token"], data["from_name"])


class RedisLobbyStore:
    """The :class:`~engine.matchmaking.store.LobbyStore` contract on Redis."""

    def __init__(self, client: Redis, *, prefix: str = "lobby:") -> None:
        self._redis = client
        self._prefix = prefix

    @classmethod
    def from_url(cls, url: str, *, prefix: str = "lobby:") -> RedisLobbyStore:
        """Connect lazily so importing the package needs no redis install."""
        from redis import Redis

        return cls(Redis.from_url(url, decode_responses=True), prefix=prefix)

    def _key(self, kind: str, token: str = "") -> str:
        return f"{self._prefix}{kind}:{token}" if token else f"{self._prefix}{kind}"

    def touch(self, token: str, name: str | None, *, busy: bool) -> None:
        key = self._key("presence", token)
        pipe = self._redis.pipeline()
        pipe.hset(key, mapping={"name": name or "", "busy": "1" if busy else "0"})
        pipe.expire(key, int(PRESENCE_TTL) + 5)
        pipe.execute()

    def forget(self, token: str) -> None:
        pipe = self._redis.pipeline()
        pipe.delete(self._key("presence", token), self._key("invite", token))
        pipe.delete(self._key("outcome", token))
        pipe.lrem(self._key("queue"), 0, token)
        pipe.execute()

    def _presence(self, tokens: list[str]) -> dict[str, tuple[str | None, bool]]:
        pipe = self._redis.pipeline()
        for token in tokens:
            pipe.hgetall(self._key("presence", token))
        return {
            token: (data.get("name") or None, data.get("busy") == "1")
            for token, data in zip(tokens, pipe.execute(), strict=True)
        }

    def available(self, exclude: Collection[str] = ()) -> list[Queued]:
        tokens = [
            key[len(self._prefix) + len("presence:") :]
            for key in cast(
                "list[str]",
                self._redis.scan_iter(match=self._key("presence", "*")),
            )
        ]
        found = self._presence(tokens)
        return [
            Queued(token, name)
            for token, (name, busy) in found.items()
            if not busy and token not in exclude
        ]

    def enqueue(self, token: str, name: str | None) -> None:
        queue = self._key("queue")
        pipe = self._redis.pipeline()
        pipe.lrem(queue, 0, token)
        pipe.rpush(queue, token)
        pipe.execute()

    def queued(self, token: str) -> Queued | None:
        if self._redis.lpos(self._key("queue"), token) is None:
            return None
        name, busy = self._presence([token])[token]
        return None if busy else Queued(token, name)

    def waiting(self) -> list[Queued]:
        tokens = cast(
            "list[str]", self._redis.lrange(self._key("queue"), 0, -1)
        )  # decode_responses=True, so elements are str at runtime
        found = self._presence(tokens)
        return [
            Queued(token, name)
            for token, (name, busy) in found.items()
            if not busy
        ]

    def release(self, token: str) -> bool:
        return bool(self._redis.lrem(self._key("queue"), 0, token))

    def claim_other(self, token: str) -> Queued | None:
        claimed = self._redis.eval(
            _CLAIM_OTHER,
            1,
            self._key("queue"),
            token,
            self._prefix,
        )
        if not claimed:
            return None
        name, _ = self._presence([claimed])[claimed]
        return Queued(claimed, name)

    def invite(self, receiver: str, invite: Invite) -> None:
        key = self._key("invite", receiver)
        pipe = self._redis.pipeline()
        existing = cast("dict[str, str]", self._redis.hgetall(key))
        for field, raw in existing.items():
            if _invite_from_json(raw).from_token == invite.from_token:
                pipe.hdel(key, field)
        pipe.hset(key, invite.invite_id, _invite_json(invite))
        pipe.expire(key, int(INVITE_TTL) + 5)
        pipe.execute()

    def inbox(self, token: str) -> list[Invite]:
        raw = cast(
            "dict[str, str]",
            self._redis.hgetall(self._key("invite", token)),
        )
        return [_invite_from_json(value) for value in raw.values()]

    def take_invite(self, token: str, invite_id: str) -> Invite | None:
        key = self._key("invite", token)
        raw = cast("str | None", self._redis.hget(key, invite_id))
        if raw is None:
            return None
        self._redis.hdel(key, invite_id)
        return _invite_from_json(raw)

    def drop_invite(self, token: str, invite_id: str) -> bool:
        return bool(self._redis.hdel(self._key("invite", token), invite_id))

    def clear_invites(self, token: str) -> None:
        self._redis.delete(self._key("invite", token))

    def set_outcome(self, token: str, match: Match) -> None:
        self._redis.set(
            self._key("outcome", token),
            json.dumps({"game_id": match.game_id}),
            ex=int(OUTCOME_TTL) + 5,
        )

    def pop_outcome(self, token: str) -> Match | None:
        raw = self._redis.getdel(self._key("outcome", token))
        if raw is None:
            return None
        data: dict[str, Any] = json.loads(raw)
        return Match(data["game_id"])
