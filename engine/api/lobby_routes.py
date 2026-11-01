"""Matchmaking endpoints: heartbeat, status, create, accept, decline.

Mounted under ``/lobby`` next to the game routes. Handlers stay thin; the
rules live in :class:`engine.matchmaking.service.LobbyService`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from engine.api.deps import Lobby, NameHeader, TokenHeader
from engine.api.errors import translate
from engine.api.lobby_schemas import LobbyInvite, LobbyStatusModel
from engine.matchmaking import LobbyStatus

router = APIRouter(prefix="/lobby", tags=["lobby"])


def _required(token: str | None) -> str:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing X-Player-Token",
        )
    return token


def _status(result: LobbyStatus) -> LobbyStatusModel:
    return LobbyStatusModel(
        state=result.state,
        game_id=result.game_id,
        invites=[
            LobbyInvite(
                invite_id=invite.invite_id,
                from_token=invite.from_token,
                from_name=invite.from_name,
            )
            for invite in result.invites
        ],
    )


@router.post("/heartbeat", status_code=204)
def heartbeat(
    lobby: Lobby,
    token: TokenHeader = None,
    name: NameHeader = None,
    busy: bool = False,
) -> None:
    """Announce that this tab is alive; ``busy`` means inside a game."""
    lobby.heartbeat(_required(token), name, busy=busy)


@router.get("/status", response_model=LobbyStatusModel)
def lobby_status(lobby: Lobby, token: TokenHeader = None) -> LobbyStatusModel:
    """Poll for invites and for the game a match placed you in."""
    return _status(lobby.status(_required(token)))


@router.post("/create", response_model=LobbyStatusModel)
def create(
    lobby: Lobby, token: TokenHeader = None, name: NameHeader = None
) -> LobbyStatusModel:
    """Join a waiting player, or wait and invite everyone who is idle."""
    with translate():
        return _status(lobby.create(_required(token), name))


@router.post("/invites/{invite_id}/accept", response_model=LobbyStatusModel)
def accept(
    lobby: Lobby,
    invite_id: str,
    token: TokenHeader = None,
    name: NameHeader = None,
) -> LobbyStatusModel:
    """Accept an invite; both players are then sent to the new game."""
    with translate():
        return _status(lobby.accept(_required(token), invite_id, name))


@router.post("/invites/{invite_id}/decline", status_code=204)
def decline(
    lobby: Lobby, invite_id: str, token: TokenHeader = None
) -> None:
    lobby.decline(_required(token), invite_id)


@router.post("/cancel", response_model=LobbyStatusModel)
def cancel(lobby: Lobby, token: TokenHeader = None) -> LobbyStatusModel:
    """Stop waiting for an opponent."""
    return _status(lobby.cancel(_required(token)))


@router.post("/leave", status_code=204)
def leave(lobby: Lobby, token: TokenHeader = None) -> None:
    """Forget this player entirely (they entered a game or left)."""
    lobby.leave(_required(token))
