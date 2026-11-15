"""Application factory: storage, CORS, routes and the static SPA."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from engine.api.events import router as events_router
from engine.api.lobby_routes import router as lobby_router
from engine.api.realtime import Broadcaster
from engine.api.routes import router
from engine.matchmaking import LobbyService, LobbyStore, default_lobby_store
from engine.storage import GameRepository, InMemoryGameStore

DEFAULT_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")


def _allowed_origins() -> list[str]:
    """CORS origins: ``ALLOWED_ORIGINS`` (comma-separated) plus the Render URL.

    In production the SPA is served from the same origin as the API, so CORS
    is only needed for split deployments (e.g. Vite dev on :5173 talking to a
    remote API). ``RENDER_EXTERNAL_URL`` is injected by Render automatically.
    """
    import os

    raw = os.environ.get("ALLOWED_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    render_url = os.environ.get("RENDER_EXTERNAL_URL")
    if render_url:
        origins.append(render_url)
    return origins or list(DEFAULT_ORIGINS)


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
        allow_origins=_allowed_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    broadcaster = Broadcaster()
    if repository is None:
        repository = InMemoryGameStore(on_change=broadcaster.publish)
    app.state.broadcaster = broadcaster
    app.state.repository = repository
    app.state.lobby = LobbyService(
        app.state.repository, lobby_store or default_lobby_store()
    )
    app.include_router(router)
    app.include_router(events_router)
    app.include_router(lobby_router)

    dist = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
    if serve_spa and dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")

    return app
