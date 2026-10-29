"""FastAPI REST interface over the checkers engine.

Run with ``uvicorn engine.api:app`` or ``python -m engine.api``.
Games are held in memory per application instance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from engine.board import Board
from engine.constants import Kind, Player
from engine.legality import freeze_map, legal_moves
from engine.notation import Move
from engine.rules import is_draw, winner


class PieceModel(BaseModel):
    """A piece on the board."""

    player: Player
    kind: Kind


class BoardModel(BaseModel):
    """Serialized board accepted by ``POST /games``."""

    squares: list[PieceModel | None] = Field(min_length=64, max_length=64)
    turn: Player = Player.WHITE
    poisoned: dict[str, bool] = Field(
        default_factory=lambda: {"WHITE": False, "BLACK": False}
    )


class MoveModel(BaseModel):
    """A move as sent by clients."""

    from_sq: int = Field(ge=0, le=63)
    to_sq: int = Field(ge=0, le=63)
    captures: list[int] = Field(default_factory=list)
    dies: bool = False

    def to_move(self) -> Move:
        """Convert to the engine's Move dataclass."""
        return Move(
            from_sq=self.from_sq,
            to_sq=self.to_sq,
            captures=list(self.captures),
            dies=self.dies,
        )


class GameCreated(BaseModel):
    """Response for game creation."""

    game_id: str


def _board_from_model(model: BoardModel) -> Board:
    raw = model.model_dump(mode="json")
    return Board.from_dict(raw)


Seat = dict[str, str | None]


def _fresh_seats() -> Seat:
    return {"WHITE": None, "BLACK": None}


def _fresh_names() -> dict[str, str | None]:
    return {"WHITE": None, "BLACK": None}


def _clean_name(name: str | None) -> str | None:
    if name is None:
        return None
    trimmed = name.strip()[:24]
    return trimmed or None


def _color_for(seats: Seat, token: str | None) -> str | None:
    if not token:
        return None
    for color, holder in seats.items():
        if holder == token:
            return color
    return None


def _state(
    game_id: str,
    board: Board,
    seats: Seat | None = None,
    token: str | None = None,
    names: dict[str, str | None] | None = None,
    history: list[dict[str, Any]] | None = None,
    rematch: dict[str, bool] | None = None,
) -> dict[str, Any]:
    result = winner(board)
    seats = seats if seats is not None else _fresh_seats()
    names = names if names is not None else _fresh_names()
    moves = list(history or [])
    rematch = rematch if rematch is not None else {"WHITE": False, "BLACK": False}
    over = result is not None or is_draw(board)
    return {
        "game_id": game_id,
        "board": board.to_dict(),
        "legal_moves": [m.to_dict() for m in legal_moves(board)],
        "freeze": {str(sq): frozen for sq, frozen in freeze_map(board).items()},
        "winner": result.value if result is not None else None,
        "is_draw": is_draw(board),
        "seats": {color: holder is not None for color, holder in seats.items()},
        "your_color": _color_for(seats, token),
        "names": {color: names.get(color) for color in ("WHITE", "BLACK")},
        "history": moves,
        "move_count": len(moves),
        "game_over": over,
        "rematch": {color: rematch[color] for color in ("WHITE", "BLACK")},
    }


def _get(games: dict[str, Board], game_id: str) -> Board:
    board = games.get(game_id)
    if board is None:
        raise HTTPException(status_code=404, detail=f"unknown game {game_id}")
    return board


TokenHeader = Annotated[str | None, Header(alias="X-Player-Token")]
NameHeader = Annotated[str | None, Header(alias="X-Player-Name")]


def create_app() -> FastAPI:
    """Build a FastAPI application with its own in-memory game store."""
    app = FastAPI(title="Checkers Engine API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    games: dict[str, Board] = {}
    seats: dict[str, Seat] = {}
    names: dict[str, dict[str, str | None]] = {}
    history: dict[str, list[dict[str, Any]]] = {}
    rematches: dict[str, dict[str, bool]] = {}

    def remember_name(game_id: str, token: str | None, name: str | None) -> None:
        cleaned = _clean_name(name)
        color = _color_for(seats[game_id], token)
        if cleaned is not None and color is not None:
            names[game_id][color] = cleaned

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/games", status_code=201, response_model=GameCreated)
    def create_game(
        board: Annotated[BoardModel | None, Body()] = None,
        token: TokenHeader = None,
        name: NameHeader = None,
    ) -> GameCreated:
        if board is None:
            parsed = Board.setup()
        else:
            try:
                parsed = _board_from_model(board)
            except (KeyError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        game_id = uuid4().hex
        games[game_id] = parsed
        game_seats = _fresh_seats()
        if token:
            game_seats[parsed.turn.value] = token
        seats[game_id] = game_seats
        names[game_id] = _fresh_names()
        history[game_id] = []
        rematches[game_id] = {"WHITE": False, "BLACK": False}
        remember_name(game_id, token, name)
        return GameCreated(game_id=game_id)

    @app.post("/games/{game_id}/join")
    def join_game(
        game_id: str, token: TokenHeader = None, name: NameHeader = None
    ) -> dict[str, Any]:
        board = _get(games, game_id)
        if not token:
            raise HTTPException(status_code=400, detail="missing X-Player-Token")
        game_seats = seats[game_id]
        if _color_for(game_seats, token) is None:
            free = next((c for c, h in game_seats.items() if h is None), None)
            if free is None:
                raise HTTPException(status_code=409, detail="game is full")
            game_seats[free] = token
        remember_name(game_id, token, name)
        return _state(
            game_id,
            board,
            game_seats,
            token,
            names[game_id],
            history[game_id],
            rematches[game_id],
        )

    @app.get("/games")
    def list_games() -> list[str]:
        return list(games)

    @app.get("/games/{game_id}")
    def get_game(game_id: str, token: TokenHeader = None) -> dict[str, Any]:
        return _state(
            game_id,
            _get(games, game_id),
            seats[game_id],
            token,
            names[game_id],
            history[game_id],
            rematches[game_id],
        )

    @app.get("/games/{game_id}/moves")
    def get_legal_moves(game_id: str) -> list[dict[str, Any]]:
        return [m.to_dict() for m in legal_moves(_get(games, game_id))]

    @app.post("/games/{game_id}/moves")
    def play_move(
        game_id: str, move: MoveModel, token: TokenHeader = None
    ) -> dict[str, Any]:
        board = _get(games, game_id)
        color = _color_for(seats[game_id], token)
        if color is not None and color != board.turn.value:
            raise HTTPException(status_code=403, detail="not your turn")
        parsed = move.to_move()
        try:
            board.apply(parsed)
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        played = parsed.to_dict()
        played["player"] = color
        history[game_id].append(played)
        return _state(
            game_id,
            board,
            seats[game_id],
            token,
            names[game_id],
            history[game_id],
            rematches[game_id],
        )

    @app.post("/games/{game_id}/undo")
    def undo_move(game_id: str, token: TokenHeader = None) -> dict[str, Any]:
        board = _get(games, game_id)
        try:
            board.undo()
        except IndexError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if history[game_id]:
            history[game_id].pop()
        rematches[game_id] = {"WHITE": False, "BLACK": False}
        return _state(
            game_id,
            board,
            seats[game_id],
            token,
            names[game_id],
            history[game_id],
            rematches[game_id],
        )

    @app.post("/games/{game_id}/rematch")
    def request_rematch(game_id: str, token: TokenHeader = None) -> dict[str, Any]:
        board = _get(games, game_id)
        color = _color_for(seats[game_id], token)
        if color is None:
            raise HTTPException(status_code=403, detail="not a player in this game")
        rematches[game_id][color] = True
        if all(rematches[game_id].values()):
            games[game_id] = Board.setup()
            history[game_id] = []
            rematches[game_id] = {"WHITE": False, "BLACK": False}
            board = games[game_id]
        return _state(
            game_id,
            board,
            seats[game_id],
            token,
            names[game_id],
            history[game_id],
            rematches[game_id],
        )

    @app.post("/games/{game_id}/rematch/decline")
    def decline_rematch(game_id: str, token: TokenHeader = None) -> dict[str, Any]:
        board = _get(games, game_id)
        rematches[game_id] = {"WHITE": False, "BLACK": False}
        return _state(
            game_id,
            board,
            seats[game_id],
            token,
            names[game_id],
            history[game_id],
            rematches[game_id],
        )

    @app.delete("/games/{game_id}", status_code=204)
    def delete_game(game_id: str) -> None:
        _get(games, game_id)
        del games[game_id]
        seats.pop(game_id, None)
        names.pop(game_id, None)
        history.pop(game_id, None)

    dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app)
