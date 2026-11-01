"""Lobby errors, translated to HTTP by ``engine.api.errors``."""

from __future__ import annotations


class LobbyError(Exception):
    """Base class for matchmaking failures."""


class InviteGone(LobbyError):
    """The invite no longer exists, or its sender stopped waiting."""
