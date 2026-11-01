# How the FastAPI layer works (`engine/api/`)

This guide explains the HTTP API in `engine/api/` for someone who already knows
the basics of FastAPI (routes, Pydantic models, dependency injection) and CRUD
with Postgres. It points out the parts that are **different from a typical
tutorial CRUD app**, because those are the parts that usually confuse people
reading this codebase.

---

## 1. The big picture

The API is a thin HTTP wrapper around a *game engine* (the rules of checkers)
and a *storage layer* (where games live). The API itself contains almost no
logic. Its jobs are:

1. Accept JSON from the client and turn it into Python objects (schemas).
2. Read the player's identity out of request headers (deps).
3. Call a storage object that does the actual work.
4. Turn Python exceptions into HTTP status codes (errors).

A typical request flows like this:

```
HTTP request
   -> FastAPI validates the body/headers (schemas.py, deps.py)
   -> route function in routes.py
   -> repo.<something>() in engine/storage/
   -> GameRecord.state() produces the JSON response
```

That's it. If you understand those four lines, you understand the API.

---

## 2. Where the app is built: `application.py`

If you're used to `app = FastAPI()` at the top of `main.py`, this codebase does
something slightly different: an **application factory**.

```python
def create_app(
    repository: GameRepository | None = None,
    *,
    serve_spa: bool = True,
) -> FastAPI:
    app = FastAPI(title="Checkers Engine API", version="0.1.0")
    app.add_middleware(CORSMiddleware, ...)
    app.state.repository = repository or InMemoryGameStore()
    app.include_router(router)
    ...
    return app
```

Why a function instead of a module-level `app`?

- **Testability.** Tests can call `create_app(repository=FakeRepo())` and pass in
a fake storage backend. No monkeypatching required.
- **Configurability.** The `serve_spa` flag lets you turn off serving the
frontend (useful in tests, or when the frontend is hosted separately).

### `app.state.repository`

This line is the most important one for understanding how the API is wired:

```python
app.state.repository = repository or InMemoryGameStore()
```

`app.state` is a plain bag of attributes attached to the FastAPI app. Anything
stored there can be read later from inside a request via `request.app.state`.

This is a common FastAPI pattern for **app-wide singletons** — the same idea as
a database connection pool, except here it's a repository object that holds the
games.

### CORS and the static SPA mount

```python
app.add_middleware(CORSMiddleware, allow_origins=list(DEFAULT_ORIGINS), ...)

dist = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
if serve_spa and dist.is_dir():
    app.mount("/", StaticFiles(directory=dist, html=True), name="web")
```

- CORS allows the Vite dev server (`localhost:5173`) to call the API directly
during development.
- The `StaticFiles` mount serves the built React app from `web/dist` at `/` in
production. **This is why the mount happens last** — routes registered before
the mount win, so `/games` still works. Anything not matching an API route falls
through to the SPA's `index.html`.

### `__init__.py` vs `__main__.py`

```python
# __init__.py
app = create_app()
```

A module-level `app` exists after all — but it's *built* by the factory. This is
what `uvicorn engine.api:app` imports. The factory itself is exported too, so
tests and `__main__.py` can build a custom one:

```python
# __main__.py
uvicorn.run(create_app())
```

So you have three ways to run it:

| Command | What it uses |
|---|---|
| `uvicorn engine.api:app` | The module-level `app` |
| `python -m engine.api` | `__main__.py` -> factory |
| `create_app(repository=...)` in a test | Custom repo |

---

## 3. Request dependencies: `deps.py`

This file defines the things every route needs, in a reusable form.

### Header parameters as type aliases

```python
TokenHeader = Annotated[str | None, Header(alias="X-Player-Token")]
NameHeader  = Annotated[str | None, Header(alias="X-Player-Name")]
```

This is just a *named* way to say "read the `X-Player-Token` header". FastAPI's
`Header` already works like `Query`/`Body`. The `Annotated` alias exists so
every route writes `token: TokenHeader = None` instead of repeating the long
`Annotated[str | None, Header(alias=...)]` type.

**Note:** this is *not* JWT authentication. There's no token verification, no
signature, no expiry. The token is just an opaque string the client generates
once and sends back to identify itself. The API trusts it as-is.

> **If you're coming from JWT auth:** imagine a `user_id` cookie that you never
> validate, you just look it up in a dict. That's the security model here. It's
> fine for a local game, not for anything sensitive.

### The repository dependency

```python
def get_repository(request: Request) -> GameRepository:
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        raise RuntimeError("no game repository configured")
    return cast(GameRepository, repo)

Repository = Annotated[GameRepository, Depends(get_repository)]
```

This is the flip side of `app.state.repository` in `application.py`. Instead of
each route receiving `Request` and digging into `app.state` itself, a dependency
fetches it and hands it over.

The `Repository` alias then lets routes write:

```python
def get_game(repo: Repository, game_id: str, ...):
```

FastAPI sees `Depends(get_repository)` inside the alias, runs it, and passes the
result as `repo`. Same mechanism as `Depends(get_db)` in a Postgres app — the
difference is that here it's a single object on `app.state` instead of a session
created per request.

---

## 4. Request/response shapes: `schemas.py`

These are ordinary Pydantic `BaseModel`s, but with a twist: two of them exist
purely to **translate** between the HTTP world and the engine's Python objects.

```python
class MoveModel(BaseModel):
    from_sq: int = Field(ge=0, le=63)
    to_sq: int = Field(ge=0, le=63)
    captures: list[int] = Field(default_factory=list)
    dies: bool = False

    def to_move(self) -> Move:
        return Move(
            from_sq=self.from_sq,
            to_sq=self.to_sq,
            captures=list(self.captures),
            dies=self.dies,
        )
```

Why not just use the engine's `Move` dataclass directly in the route signature?

Because engine objects are not designed for the wire. `MoveModel` gives you:

- **Validation.** `Field(ge=0, le=63)` rejects square numbers outside the board
with a 422 before any code runs.
- **Decoupling.** The engine can change `Move` without changing your HTTP
contract, and vice versa. `to_move()` is the only seam.

Same idea on the way in for boards:

```python
class BoardModel(BaseModel):
    squares: list[PieceModel | None] = Field(min_length=64, max_length=64)
    turn: Player = Player.WHITE
    poisoned: dict[str, bool] = ...

def board_from_model(model: BoardModel) -> Board:
    return Board.from_dict(model.model_dump(mode="json"))
```

`model_dump(mode="json")` converts enums (like `Player.WHITE`) into their string
values, because `Board.from_dict` expects plain JSON-style data.

### `GameCreated`

```python
class GameCreated(BaseModel):
    game_id: str
```

The only route with an explicit `response_model`. Every other route returns a
plain `dict`, because the shape is built by `GameRecord.state()` (see section 7).

---

## 5. The routes: `routes.py`

Every route is a **thin wrapper**. Look at the pattern:

```python
@router.post("/games/{game_id}/moves")
def play_move(
    repo: Repository, game_id: str, move: MoveModel, token: TokenHeader = None
) -> dict[str, Any]:
    with translate():
        return repo.play(game_id, token, move.to_move()).state(game_id, token)
```

That single line does four things:

1. `repo.play(...)` asks the storage layer to validate and apply the move.
2. `token` identifies who's asking (read from the header, not the body).
3. `move.to_move()` converts the request model to an engine object.
4. `.state(game_id, token)` serializes the resulting game back to JSON.

The route contains **no** rules logic, **no** storage logic, and **no** error
handling. All three live elsewhere. That's the point — if the API layer is thin,
you can swap out storage or change engine rules without touching routes.

### The one route with its own validation

```python
@router.post("/games/{game_id}/join")
def join_game(repo: Repository, game_id: str, token: TokenHeader = None, ...):
    if not token:
        raise HTTPException(status_code=400, detail="missing X-Player-Token")
    with translate():
        return repo.join(game_id, token, name).state(game_id, token)
```

Joining is the only action that *requires* a token (you can't claim a seat
without identifying yourself), so this route checks it explicitly before
calling storage.

### Route summary

| Method | Path | What it does |
|---|---|---|
| `GET` | `/health` | liveness check |
| `POST` | `/games` | create a game; body optional (`Board.setup()` if omitted) |
| `GET` | `/games` | list game ids |
| `GET` | `/games/{id}` | full state from caller's perspective |
| `GET` | `/games/{id}/moves` | just the legal moves |
| `POST` | `/games/{id}/join` | take a free seat |
| `POST` | `/games/{id}/moves` | play a move |
| `POST` | `/games/{id}/undo` | undo last move |
| `POST` | `/games/{id}/rematch` | flag ready for a rematch |
| `POST` | `/games/{id}/rematch/decline` | clear rematch flags |
| `DELETE` | `/games/{id}` | delete the game |

### A subtlety: `token: TokenHeader = None`

`TokenHeader` is `str | None`, so the parameter is *optional*. Routes that
require a token either check it by hand (`join_game`) or leave it to the storage
layer, which treats `None` as "anonymous spectator". For example, `play_move`
passes `token` straight to `repo.play`. Look at `memory.py`:

```python
def play(self, game_id: str, token: str | None, move: Move) -> GameRecord:
    record = self.require(game_id)
    color = color_for(record.seats, token)
    if color is not None and color != record.board.turn.value:
        raise NotYourTurn("not your turn")
    ...
```

If `token` is `None` (no header), `color_for` returns `None`, and the turn check
is skipped entirely. So an anonymous caller can move for either side. That's a
deliberate choice for a local game — but it's a good example of why you should
read the storage layer before assuming the API enforces anything.

---

## 6. Error translation: `errors.py`

Here's where the codebase departs most from tutorial FastAPI. Storage raises
Python exceptions (`GameNotFound`, `NotYourTurn`, `ValueError`, ...). Those must
become HTTP responses, but you don't want `try/except` all over your routes.

Instead there's a **mapping table**:

```python
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
```

...and a context manager that wraps a block of code:

```python
@contextmanager
def translate() -> Iterator[None]:
    try:
        yield
    except HTTPException:
        raise
    except Exception as exc:
        code = next(
            (s for kind, s in STATUS_FOR.items() if isinstance(exc, kind)), None
        )
        if code is None:
            raise
        raise HTTPException(status_code=code, detail=_detail(exc)) from exc
```

Breaking it down:

- `@contextmanager` turns a generator into something usable with `with`.
- `yield` is where the body of the `with` block runs.
- If the body raises, the `except` clauses catch it.
- `next((...), None)` walks the mapping table in order and finds the first
match via `isinstance`. Order matters: `GameNotFound` is also a `KeyError`, so
it must come first, which it does.
- `raise HTTPException(...) from exc` preserves the original exception as the
``__cause__``, so tracebacks stay useful.
- `except HTTPException: raise` lets routes' own `HTTPException`s pass through
untouched (like the one in `join_game`).

Why this design instead of FastAPI exception handlers? Because some routes
(`get_game`) call storage *and* serialize inside one expression, and you want
errors from either step translated. A `with` block scopes that neatly and makes
the intent obvious at the call site.

---

## 7. What the API actually returns

Almost every route ends with `.state(game_id, token)`. That method lives on
`GameRecord` in `engine/storage/models.py`:

```python
def state(self, game_id: str, token: str | None) -> dict[str, Any]:
    result = winner(self.board)
    return {
        "game_id": game_id,
        "board": self.board.to_dict(),
        "legal_moves": [m.to_dict() for m in legal_moves(self.board)],
        "freeze": {...},
        "winner": result.value if result is not None else None,
        "is_draw": is_draw(self.board),
        "seats": {color: holder is not None for color, holder in self.seats.items()},
        "your_color": color_for(self.seats, token),
        "names": {...},
        "history": list(self.history),
        "move_count": len(self.history),
        "game_over": ...,
        "rematch": {...},
    }
```

Two things worth noticing:

1. **It's per-caller.** `your_color` is computed from the token you sent. So the
same game looks different to the two players — each sees their own colour. This
is why `state()` takes a `token` argument instead of being a pure serializer.
2. **It's a plain dict**, not a Pydantic model. That's why most routes have no
`response_model` — there's nothing to declare. If you wanted stricter response
validation, you'd turn this into a `GameState` schema; the code doesn't because
it's already covered by tests.

---

## 8. The storage layer in one paragraph

You don't need to understand the engine, but you do need to understand the
storage contract, because **that's what routes talk to**.

`engine/storage/base.py` defines `GameRepository` as a `Protocol`:

```python
@runtime_checkable
class GameRepository(Protocol):
    def ids(self) -> list[str]: ...
    def require(self, game_id: str) -> GameRecord: ...
    def create(self, board, token, name) -> tuple[str, GameRecord]: ...
    def join(self, game_id, token, name) -> GameRecord: ...
    def play(self, game_id, token, move) -> GameRecord: ...
    def undo(self, game_id) -> GameRecord: ...
    def request_rematch(self, game_id, token) -> GameRecord: ...
    def decline_rematch(self, game_id) -> GameRecord: ...
    def delete(self, game_id) -> None: ...
```

A `Protocol` is Python's structural typing: "anything with these methods counts
as a `GameRepository`". No base class to inherit from, no registration. Compare
this to a `Repository` interface in Java or TypeScript.

This is the part that matters if you ever add a database: you write a
`PostgresGameStore` that implements these nine methods, then change one line in
`application.py`:

```python
app.state.repository = PostgresGameStore(pool)
```

Nothing else in `engine/api/` changes. That's why `routes.py` never imports
`InMemoryGameStore`.

### The default implementation

`engine/storage/memory.py` is the only implementation today:

```python
class InMemoryGameStore:
    def __init__(self) -> None:
        self._games: dict[str, GameRecord] = {}
```

Two consequences you should internalise:

1. **Data is lost on restart.** There's no database. If you're looking for the
Postgres code because your FastAPI experience says "there must be one", there
isn't — this is a pure in-memory toy.
2. **It's not thread-safe or multi-worker safe.** Two uvicorn workers would each
have their own `dict`. Fine for local play, not for production.

---

## 9. The identity model (and why it isn't auth)

Since you mentioned JWT, here's the direct comparison:

| JWT app | This app |
|---|---|
| Client sends `Authorization: Bearer <jwt>` | Client sends `X-Player-Token: <opaque string>` |
| Server verifies signature and expiry | Server does no verification |
| Token contains user id | Token *is* the identity |
| Server looks up user in DB | Server compares token against `record.seats` |
| A missing token -> 401 | A missing token -> spectator (mostly) |

The token is chosen by the client, not issued by the server. Whoever knows the
token can act as that player. There's no `login` route and no password. If you
want to add real auth, the natural place is `deps.py`: replace `TokenHeader` with
a `Depends(get_current_user)` that decodes a JWT and returns a user id, then use
that id as the token. Everything downstream keeps working, because storage only
cares that the token is *some* string identifying a seat.

---

## 10. Request flow, end to end

`POST /games/abc123/moves` with body `{"from_sq": 10, "to_sq": 15}` and header
`X-Player-Token: alice-token`:

1. **FastAPI** parses the JSON into a `MoveModel`. Bad square numbers -> 422.
2. **`get_repository`** runs because `repo: Repository` is in the signature.
It reads `request.app.state.repository` and returns the `InMemoryGameStore`.
3. **`TokenHeader`** reads `X-Player-Token` and passes `"alice-token"`.
4. **`play_move`** enters `with translate():` and calls
`repo.play("abc123", "alice-token", move.to_move())`.
5. **`InMemoryGameStore.play`** fetches the record, checks the token against
`seats`, raises `NotYourTurn` if it's the other player's turn, otherwise calls
`record.board.apply(move)` and appends to `history`.
6. If an exception escaped step 5, `translate` converts it: `NotYourTurn` -> 403,
`GameNotFound` -> 404, `ValueError` -> 400, etc.
7. Back in the route, `.state("abc123", "alice-token")` builds the response dict,
including `your_color: "WHITE"`.
8. FastAPI JSON-encodes that dict and returns 200.

---

## 11. Things that surprised me (checklist for reading)

- **There is no database.** The repository is a dict. `app.state.repository` is
the seam where a DB-backed one would go.
- **There is no authentication.** The token header is an unverified identifier.
- **Routes are one-liners.** If you're looking for business logic, it's not here.
It's in `engine/storage/memory.py` and the engine modules.
- **`app` is created by a factory**, but `engine/api:app` still works because
`__init__.py` calls the factory at import time.
- **The root path serves the frontend.** `StaticFiles` is mounted last so it
doesn't shadow API routes.
- **Most responses have no `response_model`.** The shape comes from
`GameRecord.state()`, a hand-built dict.
- **`translate()` is a context manager, not an exception handler.** It only
catches exceptions raised inside its `with` block.

---

## 12. Where to look next

- To understand a specific endpoint: `engine/api/routes.py` then the matching
method in `engine/storage/memory.py`.
- To see how a game is represented: `GameRecord` in
`engine/storage/models.py`.
- To swap storage: `engine/storage/base.py` is the only contract you must satisfy.
- To add auth: `engine/api/deps.py` is the only place identity is read.
