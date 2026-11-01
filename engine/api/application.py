"""Application factory: storage, CORS, routes and the static SPA."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from engine.api.lobby_routes import router as lobby_router
from engine.api.routes import router
from engine.matchmaking import LobbyService, LobbyStore, default_lobby_store
from engine.storage import GameRepository, InMemoryGameStore

DEFAULT_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def create_app(
    repository: GameRepository | None = None,
    *,
    lobby_store: LobbyStore | None = None,
    serve_spa: bool = True,
) -> FastAPI:
    """Build the API, optionally with a custom repository and bundled SPA.

    Matchmaking shares its state through ``lobby_store``; the default is
    Redis when ``REDIS_URL`` is set, otherwise process-local state.
    """
    app = FastAPI(title="Checkers Engine API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(DEFAULT_ORIGINS),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.repository = repository or InMemoryGameStore()
    app.state.lobby = LobbyService(
        app.state.repository, lobby_store or default_lobby_store()
    )
    app.include_router(router)
    app.include_router(lobby_router)

    dist = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
    if serve_spa and dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")

    return app
