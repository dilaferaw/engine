# Checkers Engine

A custom-rules multiplayer checkers game, playable in the browser — no account needed.

**Live:** [checkers-engine.onrender.com](https://checkers-engine.onrender.com/)

> ⚠️ Hosted on Render's free tier, so the first request after a period of inactivity may take ~60 seconds while the server wakes up. An open game tab keeps it alive via SSE keepalives.

---

## What it is

This is an online two-player checkers game built on a custom rule variant that diverges meaningfully from standard checkers. The rules are explained in-app via an interactive rules panel, but the highlights are:

- **Death squares** — landing on certain squares destroys the piece; no capture credit is awarded.
- **Mandatory longest capture** — you must take the longest chain of captures available; picking a shorter one is illegal.
- **Single captures are illegal** — capturing exactly one piece is not a valid move. A piece whose only possible capture is a single one is *frozen* and cannot move at all.
- **Promotion poisoning** — when a man reaches its promotion square (a1 for White, h8 for Black), it poisons the opponent's entire home row, turning all four dark squares into death squares for the rest of the game.
- **Voluntary death** — stepping onto a death square is a legal move (a way to pass a turn).
- **One promotion square per side** — not the whole back row; only a1 (White) and h8 (Black) promote.

The standard rules that remain intact: 8×8 board, 12 pieces per side, men move one square forward diagonally (and capture backward), kings slide any distance diagonally, captures are compulsory.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Game engine | Pure Python 3.12, no runtime dependencies |
| Backend API | FastAPI + Uvicorn |
| Real-time updates | Server-Sent Events (SSE) |
| Matchmaking state | In-process (`MemoryLobbyStore`) or Redis |
| Frontend | React + TypeScript, bundled with Vite |
| Deployment | Render (single web service, free tier) |

---

## How it works

### Backend (`engine/`)

The backend is a FastAPI application that serves both the REST API and the compiled React SPA from `web/dist/`.

**Engine core** (no dependencies, fully typed):
- `board.py` — board state, move application, undo, promotion and poisoning logic
- `geometry.py` — square indexing, diagonal directions, death/promotion square definitions
- `moves.py` — move generation
- `legality.py` — legal move filtering, freeze detection, longest-capture enforcement
- `rules.py` — win and draw detection
- `notation.py` — `Move` dataclass with serialization

**API layer** (`engine/api/`):
- `routes.py` — game CRUD: create, join, play move, undo, rematch, leave
- `events.py` — SSE stream per game; pushes full state on every version change and a keepalive comment every 15 seconds so proxies don't drop idle connections
- `lobby_routes.py` — matchmaking: heartbeat, status, create, accept/decline invite, cancel
- `application.py` — app factory; wires storage, CORS, routers and the static SPA mount

**Matchmaking** (`engine/matchmaking/`):
- Players announce presence via a heartbeat endpoint. Clicking "find a game" either pairs you immediately with someone already waiting or queues you and sends invites to idle players. Both players are redirected to the new game once a match is accepted.
- State is kept in-process by default. Set `REDIS_URL` to share it across multiple workers.

**Storage** (`engine/storage/`):
- `base.py` defines the `GameRepository` interface.
- `memory.py` is the default in-memory implementation. A persistent database backend is not wired yet (see roadmap).

### Frontend (`web/`)

A React SPA that communicates with the backend over HTTP and SSE. Each browser tab gets its own session token (stored in `sessionStorage`), so two tabs in the same browser are treated as two separate players. The app uses hash-based routing — `#/game/<id>` — so deep-linking to a game works without a server-side router.

Key components:
- `Board.tsx` — interactive game board with legal move highlights and click-to-move
- `Lobby.tsx` — matchmaking UI: find a game, accept/decline invites
- `GameScreen.tsx` — game view: board, player cards, move list, game-over overlay
- `RulesPanel.tsx` — interactive rules reference with mini-board diagrams for every rule
- `api.ts` — typed API client, including SSE stream reader

---

## Running locally

**Requirements:** Python 3.12+, [uv](https://github.com/astral-sh/uv), Node.js 18+

```bash
# Clone and install Python deps
uv sync

# Build the frontend
cd web && npm install && npm run build && cd ..

# Start the server
uv run uvicorn engine.api:app --reload
```

Open [http://localhost:8000](http://localhost:8000). For frontend hot-reload during development, run `npm run dev` in `web/` and point it at the backend on port 8000.

**Environment variables** (see `.env.example`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `REDIS_URL` | unset | Shared matchmaking state across workers; in-process if unset |
| `ALLOWED_ORIGINS` | `localhost:5173` | Extra CORS origins for split deployments |

---

## Tests

```bash
uv run pytest
uv run pytest --cov      # with coverage report
```

The test suite uses pytest, httpx for API tests, and Hypothesis for property-based fuzz tests of the engine.

---

## Deployment

The project ships with a `render.yaml` blueprint. Import it on Render (New → Blueprint) and it creates a single free-tier web service. The build script (`scripts/build.sh`) installs Python deps with uv and compiles the React frontend; the backend then serves both the API and the SPA from the same origin, so no CORS configuration is needed in production.

One free-tier instance uses `MemoryLobbyStore` for matchmaking. Scaling to multiple instances requires a `REDIS_URL`.

---

## Roadmap

This is a work in progress. Coming up:

- **Persistent database** — game and player data currently live only in process memory and are lost on restart.
- **ELO ratings and leaderboards** — once the database is in place, ranked play and a public leaderboard.
- **AI opponent** — single-player mode against a bot to make this a fully self-contained game.
