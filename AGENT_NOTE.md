# AGENT_NOTE.md — working notes

Scratch notes for future agent sessions. Different from `AGENT.md`: that is the
handoff document for humans (architecture, invariants). This file is the
"don't rediscover this the hard way" list. Keep it short, dated, and delete
entries that stop being true.

Last updated: 2026-11-01 (toolbx env correction: Node is available; AGENT.md now
requires reading/writing this file on every start and every commit).

## Environment (this machine)

- **2026-11-01: the shell is a Fedora toolbx, and it has Node.** `node v22.23.1`,
  `npm 10.9.8`, `npx` all in `/usr/bin` (`container=oci`). `web/node_modules`
  and `web/dist` already exist, so `cd web && npm run build` works here. The old
  "no node anywhere" entry described the host Silverblue session, not the box —
  check `container=` before trusting environment notes. The toolbx shares
  `$HOME` and the host network namespace, so a server bound inside is reachable
  at `localhost:<port>` from the host browser.
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

## Measured 2026-11-01: polling traffic

- `backend.log.txt` (5.5 min, 2 tabs, 1 live game): 555x `GET /games/{id}`,
  67x `POST /lobby/heartbeat?busy=true`, 29x `GET /lobby/status`, 6x
  `POST /games/{id}/moves`. Game poll is **600 ms** (`useGame.ts`),
  lobby poll 1.5 s, heartbeat 5 s.
- `GameRecord.state()` costs ~1.9 ms and ~2.2 KB JSON on the opening position;
  that is ~0.3% of one core per tab at 600 ms, so the wall-clock cost is small —
  the damage is the request/log volume and the 600 ms worst-case latency before
  you see the opponent's move (that is the "sluggish" feeling).
- Polling is redundant for your *own* actions: `POST .../moves` already returns
  the new state; the poll exists only to learn about the opponent.

## 2026-11-01: Step 0 polling changes (done)

- `GameRecord.version` + `touch()` bump on every mutation; `GameRecord.derived()`
  caches `legal_moves`/`freeze_map` keyed on `version`. **Any new store method
  that mutates must call `record.touch()`** or pollers will not see it (and the
  `legal_moves`/`freeze` cache will go stale).
- `GET /games/{id}?after=<version>` returns `{"changed": false, "version": n}`
  when nothing changed; full state otherwise carries `"changed": true` and
  `"version"`.
- Client: `useGame` uses an adaptive `setTimeout` loop (700 ms when it is the
  opponent's turn, 3000 ms on yours) instead of a fixed 600 ms interval, and
  sends `?after=`. `useLobby` heartbeats every 10 s while in a game (was 5 s).
- Tests for all of this live in `tests/test_polling.py`.
- ruff now reports 6 findings, all pre-existing (the 5 listed above plus SIM300
  in `tests/test_geometry.py:90`).

## 2026-11-01: post-Step-0 log analysis (`backend.log.txt`)

- 80 lines total, 4 moves, 9 heartbeats, 67 `GET /games/{id}?after=N`.
  Per source: 51 polls from `127.0.0.1:36456` vs 11+5 from `10.232.231.67`.
  47 of the 67 polls carried `after=10`, i.e. the position had not changed.
- **47 stale polls for 4 moves is not "~1 poll per 3 s"** — the losing/turn-holder
  tab is polling at roughly double the expected rate. Prime suspect: React
  `StrictMode` (`web/src/main.tsx`) double-invokes effects in dev, so two
  poll loops can overlap for the first frames; the cleanup aborts the old
  controller but a `setTimeout` chain that has already rescheduled survives
  until its `cancelled` flag is checked. Not yet proven — Step 1 removes the
  mechanism entirely.
- The *terminal* noise is mostly uvicorn's access log, not load. Run dev with
  `--no-access-log` (`--log-level warning`) when you don't want to read it.
- Real server cost of a stale poll is now tiny (a version compare, no board
  serialization); it is bandwidth/connection churn, not CPU.

## 2026-11-01: Step 1a — server-sent events (done)

- `GET /games/{id}/events` (`engine/api/events.py`) pushes full state on every
  `GameRecord.version` change and `: keepalive` every 15 s. The client uses
  `fetch` + a stream reader (`api.streamGame`), **not** `EventSource`, because
  the per-tab token has to go in a header.
- `engine/api/realtime.py` `Broadcaster` is **in-process only**: sync handlers
  run in Starlette's threadpool, so waiters are `threading.Condition`, and the
  version is re-checked under the condition lock (a publish between "read
  state" and "wait" must not be lost). Multi-worker needs Redis pub/sub behind
  the same publish/subscribe contract.
- **Notification lives in the store, not in the model**: only
  `InMemoryGameStore._changed()` bumps the version *and* publishes. A new
  repository must do the same; `GameRecord.touch()` alone no longer notifies
  anyone. `create` deliberately does not publish.
- `remember_name()` no longer bumps the version — `join` decides whether the
  name actually changed and publishes then. Don't reintroduce the bump in the
  model or every join publishes twice.
- Tests: `tests/test_realtime.py` (broadcaster, store publishing, stream
  first frame, push-after-move, 404). Note the SSE frame is `data: …\n\n`;
  `iter_lines()` yields the blank separator, so skip empties in tests.
- Verified 2026-11-01: `uv run pytest tests` → **114 passed**, mypy clean,
  ruff unchanged at 6 pre-existing findings, `npm run build` clean.

## 2026-11-01: three gameplay fixes

- **Stalemate is a loss, not a draw.** `rules.winner()` returns the opponent when
  the side to move has pieces but no legal move; `is_draw()` is now only "both
  sides empty". So `state.is_draw` is almost always false — check `winner`.
- **`rematch/decline` is per seat**: `decline_rematch(game_id, token)` clears only
  the caller's flag. The old version wiped both, so B's decline erased A's
  request and A never saw the prompt. `GameOverCard` also keys the prompt off
  the opponent's flag now.
- **Leaving forfeits.** `POST /games/{id}/leave` marks `left[color]` and sets
  `GameRecord.forfeit` to the other side when the game was still running; `state`
  folds it into `winner`. `left` is now on the wire.
- The client fires the leave beacon from the `useGame` cleanup effect with
  `keepalive: true`. **Consequence: a page refresh also forfeits** — if that is
  unwanted, move the beacon to `pagehide` and only for real unloads.
- Verified 2026-11-01: `uv run pytest tests` → **118 passed**, mypy clean, ruff
  unchanged (5 pre-existing), `npm run build` clean.

## Open threads

- ~~Frontend build unverified after matchmaking~~ — verified 2026-11-01 in the
  toolbx: `cd web && npm run build` clean, and `uv run pytest tests -q` → all
  passed (only the Starlette/httpx deprecation warning).
- ~~`uv.lock` was not regenerated for the redis extra~~ — it is in the lock
  (`redis 8.1.0`, `uv.lock:935`) and `uv run --extra redis` works. The lobby
  store has still never run against a real server: no `redis-server`, and no
  `podman`/`docker` in this toolbx (`podman: command not found`).
- **`--workers 4` is only half-safe**: Redis shares the *lobby*, but games live
  in `InMemoryGameStore`, so each worker has its own game dict. Multi-worker
  matchmaking pairs players into games the other worker cannot see.
- `InMemoryGameStore.play` still accepts moves from unseated tokens (see
  `AGENT.md` known issues).
- Lobby polling is 1.5s; if that feels chatty, Redis pub/sub is the upgrade
  path (documented in `MATCHMAKING.md`).

## How to use this file

Read it first, then `AGENT.md`, then only the files you actually need. When you
learn something that cost you more than one turn, add a line here with the date.
When a fact stops being true, delete it — stale notes are worse than none.
