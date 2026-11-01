# AGENT_NOTE.md — working notes

Scratch notes for future agent sessions. Different from `AGENT.md`: that is the
handoff document for humans (architecture, invariants). This file is the
"don't rediscover this the hard way" list. Keep it short, dated, and delete
entries that stop being true.

Last updated: 2026-11-01 (after the matchmaking change, commit `ceda2f9`).

## Environment (this machine)

- **No `node` / `npm` / `npx` anywhere on PATH.** `cd web && npm run build`
  cannot run here. Type-check the frontend by reading, and say plainly that the
  build was not verified. Do not waste turns hunting for a toolchain — checked
  `~/.nvm`, `/usr/local/bin`, `/opt`, all empty.
- Python is managed by `uv`; `python3` on PATH is 3.14 but the project venv is
  3.12. Always go through `uv run …`.
- `redis-server` is not installed and the `redis` package is not in the default
  venv. Matchmaking tests use `MemoryLobbyStore`; the Redis store is
  type-checked only. To actually exercise it: `uv sync --extra redis` plus a
  local `docker run --rm -p 6379:6379 redis:7`.
- Tests: `uv run pytest tests` → 94 passed (1 harmless Starlette/httpx
  deprecation warning). Lint: `uv run ruff check engine tests` — 5 *pre-existing*
  warnings remain (`constants.py` UP042 x2, long lines in `geometry.py`,
  `moves.py`, `rules.py`). Don't attribute them to your change.
- `uv run mypy engine` is strict and currently clean. Keep it that way.

## Commands worth remembering

```sh
uv run pytest tests -q                       # backend
uv run mypy engine && uv run ruff check engine tests
uv run uvicorn engine.api:app --port 8000    # serves web/dist at / if built
REDIS_URL=redis://localhost:6379/0 uv run --extra redis uvicorn engine.api:app --workers 4
```

## Where things are

- Engine rules: `engine/{board,geometry,legality,moves,notation,rules}.py`. Custom
  variant: forced captures, frozen pieces, poisoned home rows, voluntary death.
- Storage: `engine/storage/{base,memory,models,errors}.py`. `GameRepository`
  protocol; in-memory only (games die with the process).
- HTTP: `engine/api/` — `routes.py` (games), `lobby_routes.py` (/lobby),
  `deps.py` (headers + Repository/Lobby deps), `errors.py` (`STATUS_FOR`),
  `application.py` (`create_app(repository=…, lobby_store=…, serve_spa=…)`).
- Matchmaking: `engine/matchmaking/` — `store.py` (state, protocol +
  memory), `service.py` (all rules), `redis_store.py` (shared state). Design and
  Redis key map: `MATCHMAKING.md`.
- Frontend: `web/src/` — `hooks/useGame.ts` (board), `hooks/useLobby.ts`
  (heartbeat/poll/redirect), `components/Lobby.tsx`, `api.ts` (per-tab token in
  `sessionStorage`; two tabs = two players).

## Traps I hit (avoid repeating)

- `write_file` refuses to overwrite; use `apply_patch` for existing files. A
  failed `write_file` on `App.tsx` cost a turn.
- `engine/matchmaking/__init__.py` must re-export `LobbyStatus` (routes import
  it from the package). A forgotten export broke *all* API tests at collection.
- In matchmaking, the **second** player to press Create becomes **White** (they
  claim the empty game's first seat). Don't "fix" this without deciding who
  should get which colour.
- `redis-py` stubs return `bytes | str`; the store uses
  `Redis.from_url(..., decode_responses=True)` and `cast(...)` at call sites.
  Any new store method needs the same treatment to keep mypy strict clean.
- Matchmaking liveness is TTL-based (presence ~15s, invites ~30s, outcomes
  ~60s in `store.py`). A tab that stops heartbeating silently disappears — that
  is the feature, not a bug.
- Frontend `tsconfig` has `noUnusedLocals`/`noUnusedParameters`; an unused
  import is a build error, and there is no build here to catch it.

## Conventions

- Components render, hooks own state, `lib/` is pure.
- New storage exceptions go in `STATUS_FOR` (`engine/api/errors.py`), never
  `HTTPException` inside a store. Same for `InviteGone` → 410.
- Routes are thin wrappers over the repository/service; rules never live in
  routes.
- Commit messages: imperative subject, body explaining *why*. `AGENT.md` notes
  this repo rewrote history once to fix authorship (`Dilaferaw
  <dilaferaw@gmail.com>`); check `git config user.*` before committing if that
  matters.

## Open threads

- Frontend build unverified after matchmaking (no Node here).
- `uv.lock` was not regenerated for the new `[project.optional-dependencies]
  redis` extra.
- `InMemoryGameStore.play` still accepts moves from unseated tokens (see
  `AGENT.md` known issues).
- Lobby polling is 1.5s; if that feels chatty, Redis pub/sub is the upgrade
  path (documented in `MATCHMAKING.md`).

## How to use this file

Read it first, then `AGENT.md`, then only the files you actually need. When you
learn something that cost you more than one turn, add a line here with the date.
When a fact stops being true, delete it — stale notes are worse than none.
