# Milestones — Custom Checkers

Written 2026-11-09. This is a **plan**, not a description of what exists.
Read `START_HERE.md` first for how the app works today.

## Versioning convention

- **MAJOR (`X.0`)** — the architecture changes: new persistence tier, new process
  model, new external dependency. Deployment shape changes with it.
- **MINOR (`X.Y`)** — a feature built on the architecture that already exists.
  Same deployment shape, same single image.
- **PATCH (`X.Y.Z`)** — fixes only, no new seams.

So the sequence is `1.0 → 1.1 → 2.0 → 2.1`. The gap is in *severity*, not in
numbering. `2.0` is the one that changes what the app is; `1.1` and `2.1` are
features that ride on the tier below them.

Every milestone ships a **git tag and an image tag with the same version**
(`v1.0.0`, `v1.1.0`, …) so a known-good image can be redeployed instantly.
Render's deploy-on-push is not a versioning strategy.

## Current state (start of planning)

- `master` is 4 commits ahead of `origin/master`, **not pushed**.
- No Docker image, no database, no auth. Games live in process memory.
- Serving is single-process (`--workers 1`) because of both the in-memory store
  and in-process SSE fan-out.
- `/health` already exists and is the health-check target.

---

## The four rules

These are what "easy to add, easy to deprecate" actually means here.

1. **Features are leaves; the core is the trunk.** Engine, store and broadcaster
   are core. AI, ratings and history are leaves that depend on core. Core never
   imports a leaf.
2. **A seam is introduced right before the feature that needs it, and not
   earlier.** Every abstraction listed below is one we will actually cross.
   Nothing speculative.
3. **One feature owns its tables, its routes and its UI folder.** This matters
   from `2.0` on: a feature that writes to core tables cannot be removed.
4. **Deprecating a feature = delete a directory, drop a router include, remove
   a UI route.** If removal requires editing core, the seam was wrong.

---

## 1.0 — Ship the thing

**Purpose.** Prove the deployment pipeline works with the app exactly as it is.
No new features. Every later failure should be attributable to that change, not
to "was this ever deployable?".

**Contents**

- `threading.Lock` around the store's read → validate → mutate → version-bump.
  Must span the *whole* sequence, not just the write.
- Multi-stage `Dockerfile`: build stage runs `npm run build`; runtime stage
  copies `engine/` and the built `web/dist`.
- `.dockerignore`: `node_modules`, `.venv`, `.git`, `web/dist`, `.pytest_cache`,
  `*.log`. Without this the image is ~1 GB and a stale local `dist` can shadow
  the freshly built one.
- `--workers 1`, `$PORT` from the environment, health check on `/health`
  (not `/healthz`).
- `engine/config.py` — one env-driven settings object, so later features have a
  home for flags instead of scattering `os.getenv`.
- `GameStore` protocol extracted from `InMemoryGameStore`, mirroring the
  `MemoryLobbyStore`/Redis split that already exists for matchmaking. No new
  implementation — just the interface.

**Seam introduced.** `GameStore` protocol. Cheap now, expensive to retrofit.

**Deployable.** Yes — Render free tier. Cold start ~50 s, spin-down wipes games.

**Scaling ceiling.** One instance, tens of concurrent players. The binding
constraint is SSE connections holding threadpool threads, not CPU.

**Deprecation.** Nothing to deprecate yet.

---

## 1.1 — AI opponent

**Purpose.** A second player type. Nothing about persistence changes.

**The decision that matters.** Model a game as **two seats**, each with a kind
(`HUMAN` or `BOT`) — not as "you versus a special AI mode". Small now, saves a
rewrite at `2.0`, because history and ratings need to record what they saw.

**Contents**

- `engine/ai/` — negamax + alpha-beta (see `doc_engine.txt` §11), with a hard
  per-move time budget. It **consumes** `engine/`; it never modifies it.
- Bot moves go through the same `apply_move` path a human POST uses. One rules
  implementation only — that is the point.
- Runs **in-process**. No extra service, no extra container, still
  `--workers 1`. Search is CPU work; the time budget is the throttle.
- UI: "Play the bot" in the lobby; difficulty = depth / time budget.

**Seam introduced.** `PlayerKind` / seat model; `engine/ai/` as a leaf.

**Deployable.** Yes — same image, same shape.

**Scaling ceiling.** Unchanged in shape; AI adds CPU per active bot game.

**Deprecation.** Delete `engine/ai/` and the bot-seat handling behind a flag.
Existing bot games remain readable in history **only if** history stores a
**denormalized opponent display name** rather than a foreign key into a bot
registry. Design that now, not at `2.0`.

---

## 2.0 — Persistence, identity, history

**Purpose.** The milestone that changes what the app *is*. This is the only one
where "just add a database" is not enough.

**Two things must land together, or the milestone buys no scaling:**

- `PostgresGameStore` behind the existing `GameStore` protocol. Games survive
  restarts; spin-downs stop being destructive.
- A **`Broadcaster` seam** — an interface with an in-process implementation,
  then an external one (Redis pub/sub or Postgres `LISTEN/NOTIFY`). **Without
  this, raising `--workers` above 1 silently breaks SSE**: players on different
  workers never hear each other's moves. Adding the database alone does *not*
lift the worker limit.

**Also here**

- **Identity as a dependency** — `get_current_player()` returning an anonymous
  id now, a real user later. Adding auth afterwards then touches no endpoint
  signature.
- **Users + auth** (OAuth or magic link; avoid passwords if possible).
- **History as append-only game records**, written on game end, owned by a
  `history` module with its own tables.

**Seam introduced.** `Broadcaster`; `get_current_player()`.

**Migration discipline.** Expand/contract only. Add nullable, backfill, switch
reads, drop later. Never a migration a rollback to `1.1` cannot survive.

**Deployable.** Yes, but this is the first milestone with a real rollback plan
requirement: the schema must tolerate running the previous image.

**Scaling ceiling.** With an external broadcaster, `workers > 1` and horizontal
instances become possible. That is the payoff.

**Deprecation.** History is a leaf with its own tables; removing it stops the
writes and drops one module.

---

## 2.1 — Ratings and reputation

**Purpose.** Derived data on top of history. Deliberately last: it is the only
milestone with no architectural risk, because it is queries over records that
already exist.

**Contents**

- Elo stored as **append-only rating events** (game → deltas), with the current
  rating a projection. Not a mutable counter — that makes recalculation,
  correction and deprecation all trivial.
- Reputation signals (games completed vs abandoned, disconnects) computed from
  the same event stream.
- Own module, own tables, own routes. Reads history through history's public
  read API; history never imports it.

**Seam introduced.** None. Pure consumer.

**Deployable.** Yes.

**Scaling ceiling.** Query load only.

**Deprecation.** The cleanest of all — stop writing events, keep the games.
Ratings disappear; nothing else notices.

---

## Summary

| Version | Ships | Seam introduced | Ceiling |
|---|---|---|---|
| **1.0** | Docker, store lock, config, `GameStore` protocol | `GameStore` | 1 instance, tens of players |
| **1.1** | AI opponent, seat model | `PlayerKind`, `engine/ai/` leaf | CPU per bot game |
| **2.0** | Postgres, auth, history | `Broadcaster`, `get_current_player()` | multi-worker / multi-instance |
| **2.1** | Elo, reputation | none | query load only |

## Deliberately not doing

- **No microservices.** The AI stays in-process. Splitting it answers a problem
  we do not have and adds a deployment surface.
- **No generic plugin system.** "Easy to add features" comes from module
  boundaries, not a registry. A registry is another thing to maintain.
- **No wrapping the engine.** It is pure, tested and the best-factored part of
  the codebase. The AI consumes it; nothing abstracts it.
- **No Elo before history.** Obvious, and still the ordering people get wrong
  because Elo feels like the fun part.

## Open decisions (need answers before the milestone starts)

1. **`1.1` seat model** — accept two seats with a kind (adds a little schema at
   `1.1`, saves a lot at `2.0`), or keep "AI mode" separate for simplicity?
2. **`2.0` broadcaster** — is the goal *games survive restarts* (database alone
   is enough, stay at one worker) or *serve more players* (database plus an
   external broadcaster, considerably more work)? These are very different
   sizes of milestone.
3. **`2.0` auth** — real accounts, or a persistent anonymous player id? Accounts
   are the single largest chunk of work in `2.0` and the easiest to defer.

**Recommendation:** `1.0` as scoped; `1.1` with the seat model; `2.0` scoped to
"survive restarts + persistent anonymous ids + history"; treat multi-worker as
its own later milestone once there is a concrete reason to need it.
