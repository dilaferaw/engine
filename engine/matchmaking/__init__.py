"""Matchmaking: presence, a waiting queue, invites and match outcomes.

``LobbyStore`` (``store``) is the state contract with an in-process default;
``RedisLobbyStore`` (``redis_store``) shares the same state between workers.
``LobbyService`` (``service``) owns every matchmaking rule. The HTTP surface
lives in ``engine.api.lobby_routes``.
"""

from engine.matchmaking.errors import InviteGone, LobbyError
from engine.matchmaking.models import Invite, LobbyStatus, Match, Queued
from engine.matchmaking.service import LobbyService, default_lobby_store
from engine.matchmaking.store import LobbyStore, MemoryLobbyStore

__all__ = [
    "Invite",
    "InviteGone",
    "LobbyError",
    "LobbyService",
    "LobbyStatus",
    "LobbyStore",
    "Match",
    "MemoryLobbyStore",
    "Queued",
    "default_lobby_store",
]
