"""Every matchmaking rule, in one place.

A player who clicks *create* is first paired with anyone already waiting
(two clicks race into one game); otherwise they queue and every fresh,
idle player is invited. Accepting an invite seats both players in a new
game and records the game id for the creator, whose next status poll sends
them to the board. The store holds state only; this class owns the policy.
"""

from __future__ import annotations

from uuid import uuid4

from engine.board import Board
from engine.matchmaking.errors import InviteGone
from engine.matchmaking.models import Invite, LobbyStatus, Match, Queued
from engine.matchmaking.store import LobbyStore, MemoryLobbyStore
from engine.storage import GameRepository, clean_name


def default_lobby_store() -> LobbyStore:
    """Redis when ``REDIS_URL`` is set, otherwise process-local state."""
    import os

    url = os.environ.get("REDIS_URL")
    if url:
        from engine.matchmaking.redis_store import RedisLobbyStore

        return RedisLobbyStore.from_url(url)
    return MemoryLobbyStore()


class LobbyService:
    """Presence, waiting queue, invites and match creation."""

    def __init__(self, games: GameRepository, lobby: LobbyStore) -> None:
        self._games = games
        self._lobby = lobby

    def heartbeat(
        self, token: str, name: str | None, *, busy: bool
    ) -> None:
        """Refresh presence; busy players leave the queue and get no invites."""
        self._lobby.touch(token, clean_name(name), busy=busy)
        if busy:
            self._lobby.release(token)
            self._lobby.clear_invites(token)

    def status(self, token: str) -> LobbyStatus:
        """What the client should show; consumes a pending match, if any."""
        match = self._lobby.pop_outcome(token)
        if match is not None:
            return LobbyStatus("matched", match.game_id)
        if self._lobby.queued(token) is not None:
            return LobbyStatus("waiting")
        invites = tuple(
            invite
            for invite in self._lobby.inbox(token)
            if self._lobby.queued(invite.from_token) is not None
        )
        if invites:
            return LobbyStatus("invited", invites=invites)
        return LobbyStatus("idle")

    def create(self, token: str, name: str | None) -> LobbyStatus:
        """Pair with a waiting player, or queue and invite idle players."""
        name = clean_name(name)
        self._lobby.touch(token, name, busy=False)
        self._lobby.clear_invites(token)
        partner = self._lobby.claim_other(token)
        if partner is not None:
            self._match(Queued(token, name), partner)
        else:
            self._lobby.enqueue(token, name)
            waiting = {entry.token for entry in self._lobby.waiting()}
            for candidate in self._lobby.available(exclude=waiting | {token}):
                self._lobby.invite(
                    candidate.token,
                    Invite(uuid4().hex, token, name),
                )
        return self.status(token)

    def accept(
        self, token: str, invite_id: str, name: str | None
    ) -> LobbyStatus:
        """Join the sender's game; fails when they stopped waiting."""
        invite = self._lobby.take_invite(token, invite_id)
        sender = (
            self._lobby.queued(invite.from_token) if invite is not None else None
        )
        if invite is None or sender is None:
            raise InviteGone("invite is no longer available")
        self._match(sender, Queued(token, clean_name(name)))
        return self.status(token)

    def decline(self, token: str, invite_id: str) -> None:
        """Discard one invite; unknown ids are ignored."""
        self._lobby.drop_invite(token, invite_id)

    def cancel(self, token: str) -> LobbyStatus:
        """Stop waiting; invites already sent become stale on their own."""
        self._lobby.release(token)
        self._lobby.clear_invites(token)
        return self.status(token)

    def leave(self, token: str) -> None:
        """Drop all lobby state (closing the tab or entering a game)."""
        self._lobby.forget(token)

    def _match(self, creator: Queued, partner: Queued) -> None:
        """Seat both players in a fresh game and hand each the game id."""
        game_id, _ = self._games.create(Board.setup(), creator.token, creator.name)
        self._games.join(game_id, partner.token, partner.name)
        match = Match(game_id)
        for player in (creator, partner):
            self._lobby.release(player.token)
            self._lobby.clear_invites(player.token)
            self._lobby.touch(player.token, player.name, busy=True)
            self._lobby.set_outcome(player.token, match)
