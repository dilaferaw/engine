"""Game endpoints. Each handler is a thin wrapper over the repository."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, status

from engine.api.deps import NameHeader, Repository, TokenHeader
from engine.api.errors import translate
from engine.api.schemas import BoardModel, GameCreated, MoveModel, board_from_model
from engine.board import Board

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/games", status_code=201, response_model=GameCreated)
def create_game(
    repo: Repository,
    board: Annotated[BoardModel | None, Body()] = None,
    token: TokenHeader = None,
    name: NameHeader = None,
) -> GameCreated:
    with translate():
        parsed = Board.setup() if board is None else board_from_model(board)
        game_id, _ = repo.create(parsed, token, name)
        return GameCreated(game_id=game_id)


@router.get("/games")
def list_games(repo: Repository) -> list[str]:
    return repo.ids()


@router.get("/games/{game_id}")
def get_game(
    repo: Repository,
    game_id: str,
    token: TokenHeader = None,
    after: int | None = None,
) -> dict[str, Any]:
    """Current state, or a tiny ``{"changed": false}`` when ``after`` is stale.

    Polling clients send the ``version`` they already hold; an unchanged game
    then costs a few bytes and no board/legal-move serialization.
    """
    with translate():
        record = repo.require(game_id)
        if after is not None and record.version == after:
            return {"changed": False, "version": record.version}
        return {"changed": True, **record.state(game_id, token)}


@router.get("/games/{game_id}/moves")
def get_legal_moves(repo: Repository, game_id: str) -> list[dict[str, Any]]:
    with translate():
        moves: list[dict[str, Any]] = repo.require(game_id).state(
            game_id, None
        )["legal_moves"]
        return moves


@router.post("/games/{game_id}/join")
def join_game(
    repo: Repository,
    game_id: str,
    token: TokenHeader = None,
    name: NameHeader = None,
) -> dict[str, Any]:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing X-Player-Token",
        )
    with translate():
        return repo.join(game_id, token, name).state(game_id, token)


@router.post("/games/{game_id}/moves")
def play_move(
    repo: Repository, game_id: str, move: MoveModel, token: TokenHeader = None
) -> dict[str, Any]:
    with translate():
        return repo.play(game_id, token, move.to_move()).state(game_id, token)


@router.post("/games/{game_id}/undo")
def undo_move(
    repo: Repository, game_id: str, token: TokenHeader = None
) -> dict[str, Any]:
    with translate():
        return repo.undo(game_id).state(game_id, token)


@router.post("/games/{game_id}/rematch")
def request_rematch(
    repo: Repository, game_id: str, token: TokenHeader = None
) -> dict[str, Any]:
    with translate():
        return repo.request_rematch(game_id, token).state(game_id, token)


@router.post("/games/{game_id}/rematch/decline")
def decline_rematch(
    repo: Repository, game_id: str, token: TokenHeader = None
) -> dict[str, Any]:
    with translate():
        return repo.decline_rematch(game_id, token).state(game_id, token)


@router.post("/games/{game_id}/leave")
def leave_game(
    repo: Repository, game_id: str, token: TokenHeader = None
) -> dict[str, Any]:
    """Give up this seat; the opponent wins if the game was still running."""
    with translate():
        return repo.leave(game_id, token).state(game_id, token)


@router.delete("/games/{game_id}", status_code=204)
def delete_game(repo: Repository, game_id: str) -> None:
    with translate():
        repo.delete(game_id)
