"""FastAPI REST interface over the checkers engine.

Run with ``uvicorn engine.api:app`` or ``python -m engine.api``.
Games are held in memory per application instance.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from engine.api_schemas import BoardModel, GameCreated, MoveModel, board_from_model
from engine.board import Board
from engine.store import GameFull, GameNotFound, GameStore, NotASeat, NotYourTurn


TokenHeader = Annotated[str | None, Header(alias="X-Player-Token")]
NameHeader = Annotated[str | None, Header(alias="X-Player-Name")]


STATUS_FOR: dict[type[Exception], int] = {
    GameNotFound: 404,
    GameFull: 409,
    NotASeat: 403,
    NotYourTurn: 403,
    IndexError: 409,
    KeyError: 400,
    TypeError: 400,
    ValueError: 400,
}


@contextmanager
def translate() -> Iterator[None]:
    """Map store and engine exceptions onto HTTP errors."""
    try:
        yield
    except HTTPException:
        raise
    except Exception as exc:
        status = next(
            (code for kind, code in STATUS_FOR.items() if isinstance(exc, kind)),
            None,
        )
        if status is None:
            raise
        detail = "unknown game" if isinstance(exc, GameNotFound) else str(exc)
        raise HTTPException(status_code=status, detail=detail) from exc


def create_app() -> FastAPI:
    """Build a FastAPI application with its own in-memory game store."""
    app = FastAPI(title="Checkers Engine API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    games = GameStore()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/games", status_code=201, response_model=GameCreated)
    def create_game(
        board: Annotated[BoardModel | None, Body()] = None,
        token: TokenHeader = None,
        name: NameHeader = None,
    ) -> GameCreated:
        with translate():
            parsed = Board.setup() if board is None else board_from_model(board)
            game_id, _ = games.create(parsed, token, name)
            return GameCreated(game_id=game_id)

    @app.get("/games")
    def list_games() -> list[str]:
        return games.ids()

    @app.get("/games/{game_id}")
    def get_game(game_id: str, token: TokenHeader = None) -> dict[str, Any]:
        with translate():
            return games.require(game_id).state(game_id, token)

    @app.get("/games/{game_id}/moves")
    def get_legal_moves(game_id: str) -> list[dict[str, Any]]:
        with translate():
            return games.require(game_id).state(game_id, None)["legal_moves"]

    @app.post("/games/{game_id}/join")
    def join_game(
        game_id: str, token: TokenHeader = None, name: NameHeader = None
    ) -> dict[str, Any]:
        if not token:
            raise HTTPException(status_code=400, detail="missing X-Player-Token")
        with translate():
            return games.join(game_id, token, name).state(game_id, token)

    @app.post("/games/{game_id}/moves")
    def play_move(
        game_id: str, move: MoveModel, token: TokenHeader = None
    ) -> dict[str, Any]:
        with translate():
            return games.play(game_id, token, move.to_move()).state(game_id, token)

    @app.post("/games/{game_id}/undo")
    def undo_move(game_id: str, token: TokenHeader = None) -> dict[str, Any]:
        with translate():
            return games.undo(game_id).state(game_id, token)

    @app.post("/games/{game_id}/rematch")
    def request_rematch(game_id: str, token: TokenHeader = None) -> dict[str, Any]:
        with translate():
            return games.request_rematch(game_id, token).state(game_id, token)

    @app.post("/games/{game_id}/rematch/decline")
    def decline_rematch(game_id: str, token: TokenHeader = None) -> dict[str, Any]:
        with translate():
            return games.decline_rematch(game_id).state(game_id, token)

    @app.delete("/games/{game_id}", status_code=204)
    def delete_game(game_id: str) -> None:
        with translate():
            games.delete(game_id)

    dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app)
