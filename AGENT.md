# AGENT.md — handoff notes

Read this first when picking the project up again.

## What this is
A pure-Python checkers engine for a **custom variant** (forced captures, frozen
pieces, poisoned home rows, voluntary death — see `SPEC.txt`), plus a FastAPI
HTTP layer and a React + Tailwind single-page client. No database: games live in
process memory and vanish when the server restarts.

## Layout

### Engine (Python 3.12, no runtime deps beyond FastAPI/pydantic)
| File | Responsibility |
| --- | --- |
| `engine/board.py` | `Board` + `Piece` dataclasses, `apply`/`undo`, death squares |
| `engine/geometry.py` | Square math, home rows, promotion squares, static death squares |
| `engine/legality.py` | `legal_moves`, `check_legal`, `freeze_map` |
| `engine/moves.py` | Raw move generation (quiet, captures, multi-captures) |
| `engine/notation.py` | `Move` dataclass + JSON round-trip |
| `engine/rules.py` | `winner` / `is_draw` |
### Storage (`engine/storage/`)
| File | Responsibility |
| --- | --- |
| `storage/base.py` | `GameRepository` protocol — the contract every backend implements |
| `storage/models.py` | `GameRecord` (seats, names, history, rematch), `color_for`, `clean_name` |
| `storage/errors.py` | `StorageError`, `GameNotFound`, `GameFull`, `NotASeat`, `NotYourTurn` |
| `storage/memory.py` | `InMemoryGameStore` — default backend |

### API (`engine/api/`)
| File | Responsibility |
| --- | --- |
| `api/application.py` | `create_app(repository=..., serve_spa=...)` factory |
| `api/routes.py` | Thin endpoints over `GameRepository`, all wrapped in `translate()` |
| `api/schemas.py` | Pydantic wire models (`BoardModel`, `MoveModel`, ...) |
| `api/deps.py` | `TokenHeader`, `NameHeader`, `Repository` dependency |
| `api/errors.py` | `STATUS_FOR` + `translate()` mapping storage/engine errors to HTTP |
| `api/__init__.py` | Exposes `app` and `create_app` for `uvicorn engine.api:app` |

**Where to add things.** New persistence work (users, logs, game history)
belongs in `engine/storage/`: extend `GameRepository`, add a SQL/remote backend
next to `memory.py`, and select it in `create_app`. Routes must never import a
concrete store — only `Repository`. New HTTP concerns (auth, pagination) go in
`engine/api/deps.py` and `engine/api/errors.py`, not in the store.

Status mapping lives in `STATUS_FOR` in `engine/api/errors.py`. Add a new
storage exception there, don't sprinkle `HTTPException` through the store.

### Web (`web/`, React 19 + Tailwind v4 + Vite)
| File | Responsibility |
| --- | --- |
| `src/api.ts` | fetch wrapper, per-tab token + nickname, `ApiError` |
| `src/types.ts` | wire types mirrored from the API |
| `src/theme.tsx` | board palettes + `ThemeProvider`/`useTheme`; re-exports `PieceArt` |
| `src/pieceArt.tsx` | the four SVG piece sets (single owner of all artwork) |
| `src/lib/board.ts` | `orderFor` (orientation), `squareName`, `FILES` |
| `src/lib/format.ts` | `timeText` clock formatting |
| `src/lib/sound.ts` | `cue()` WebAudio blips |
| `src/lib/clipboard.ts` | `copyText()` with execCommand fallback |
| `src/hooks/useGame.ts` | **all** game state: polling, auto-join, actions, sounds |
| `src/components/GameScreen.tsx` | layout only; composes the hook + pieces below |
| `src/components/Board.tsx` | grid, highlights, piece slots |
| `src/components/PlayerCard.tsx` | name / connection / clock |
| `src/components/MoveList.tsx` | move history rows |
| `src/components/GameOverCard.tsx` | result modal + rematch |
| `src/components/CopyButton.tsx` | copy with "Copied!" feedback |
| `src/components/Lobby.tsx` | landing page + appearance customizer |

Rule of thumb: components render, hooks own state, `lib/` is pure.

## Invariants that are easy to break

- **Orientation.** White starts on ranks 5–7, Black on 0–2. `orderFor` renders
  White 0→7 and Black 7→0 so each player's own back row is at the *bottom*.
  Do not "fix" this by swapping the loops.
- **Piece sizing.** `.board-grid` declares both `grid-template-columns` **and**
  `grid-template-rows`. Without the rows, an SVG's intrinsic size stretches a
  rank and kings look bigger than men. Pieces render inside `.piece-slot`
  (`position:absolute; inset:6%; overflow:hidden`).
- **Per-tab identity.** Token and nickname live in `sessionStorage`; two tabs
  are two players. Never move the nickname back to `localStorage`.
- **Auto-join.** `useGame` joins when exactly one seat is free. If you add
  spectators, keep that condition.
- **Game over.** `state.game_over` gates the modal; moves are still accepted by
  the server after a result, so keep the UI blocked rather than relying on the
  API to refuse.
- **Rematch.** Both seats must flag; the server then resets the board and clears
  history. Undo clears pending flags.

## Commands

```sh
uv run pytest tests -q        # backend tests (63 passing)
cd web && npm run build       # tsc --noEmit + vite build
uv run uvicorn engine.api:app --port 8000   # serves web/dist at /
cd web && npm run dev         # Vite on :5173, proxies /games to :8000
```

## Open question: sync or async storage

`GameRepository` is currently synchronous and `GameRecord` holds a live
`Board` object in memory. That is fine for `InMemoryGameStore`, but a real
database backend has to pick a side, and the answer changes every route:

- **Stay sync** — use a sync driver (e.g. `psycopg`) and implement the same
  nine methods. Routes stay `def`, FastAPI runs them in a threadpool, and
  `Board` is serialized to JSON on write / rebuilt on read. Least churn;
  simplest to review.
- **Go async** — change `GameRepository` to `async def`, switch routes to
  `async def`, and use an async driver (`asyncpg` / SQLAlchemy async). Better
  under load and for a serverless backend, but it touches every handler,
  `translate()` and the tests.

Decide before adding the first real backend; the two paths don't mix well.

## Known issues / next steps

- `deeps_tests/` was folded into `tests/` (its unique board/geometry/moves/
  invariant cases now live there) and deleted; bare `pytest` collects cleanly.
- `InMemoryGameStore.play` allows a move from an unseated token (spectator),
  which makes it effectively a shared-seat game. Tighten if that's not wanted.
- No persistence: restarting uvicorn loses every game.
- `GameScreen.tsx` still holds the layout markup (~200 lines); splitting the
  side panel out is the next natural cut.
- No frontend tests. `vitest` + `@testing-library/react` would be the first add.

## Git

Repo was initialised in this workspace (it did not exist before), then pushed
to **https://github.com/dilaferaw/engine** (public, branch `master`).

- `origin` is set to that URL. **All commits were rewritten** to author and
  committer `Dilaferaw <dilaferaw@gmail.com>` (earlier commits were made with
  no git identity configured and landed as `dscli <dscli@localhost>`). Every
  SHA changed in that rewrite, so old SHA references in notes or clones are
  dead — re-clone or `git fetch && git reset --hard origin/master`.
- Branch `pre-engine-skeleton` holds the original placeholder commit that was
  on the remote before this codebase was force-pushed over `master`. The local
  branch `backup/pre-rewrite-20261031032813` is a pre-rewrite safety copy; both
  are disposable once you're confident.
- A fresh clone needs `npm install` in `web/`: `web/node_modules` used to be
  tracked and was untracked in "Stop tracking web/node_modules". `.gitignore`
  now ignores `node_modules/` and `web/dist/`.

### Checking it still works

```sh
git fetch origin --prune && git status --short --branch  # expect clean, no ahead/behind
uv run pytest tests -q                                   # expect 63 passed
cd web && npm run build                                  # tsc --noEmit + vite build
```

Last verified 2026-10-31: local `master` == `origin/master`, 63 tests pass
(one Starlette `httpx` deprecation warning, harmless), frontend build clean.
Commit the AGENT.md edits only when you intend to publish them.
