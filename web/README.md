# Frontend — Custom Checkers

React 19 + Tailwind v4 + Vite. Read this before touching anything; the stack
is deliberately dependency-light, which makes it look different from most
React projects you have seen. That is a choice, not an accident or neglect.

## Running it in development

The frontend and the API are **two separate processes**. The frontend alone is
not a working app: every screen talks to the FastAPI backend.

**Terminal 1 — the API (must be running first):**

```sh
# from the repo root
uv run uvicorn engine.api:app --port 8000 --host 127.0.0.1
```

Check it answered: `curl localhost:8000/health` should return JSON.

**Terminal 2 — the frontend:**

```sh
cd web
npm install      # first time only
npm run dev      # http://localhost:5173
```

Open **http://localhost:5173** — not port 8000. In dev, Vite serves the app and
forwards `/health`, `/games` and `/lobby` to port 8000 (see `vite.config.ts`).

Two browser tabs are two players. Both tabs can point at 5173.

### If something "doesn't work"

- **Blank page or console error about a fetch returning HTML**: a request hit
  Vite instead of the API. Confirm the backend is up on 8000, and that the path
  is listed in the `proxy` block in `vite.config.ts`. If you add a new API
  prefix, add it there too.
- **Port 8000 already in use**: another project may hold it. Check with
  `ss -ltnp | grep :8000`.
- **Changes to `src/` appear in dev but not in the browser at port 8000**: that
  is expected. See "the production bundle" below.

## Why this looks unlike other React projects

Each of these is deliberate. Ask before "modernising" any of them — several are
load-bearing.

**No React Router.** Routing is hand-written in `src/App.tsx`: it reads
`window.location.hash` (`#/game/<id>`), listens for `hashchange`, and picks
`<GameScreen>` or `<Lobby>`. It is ~20 lines and there are exactly two screens.
A router would add a dependency to replace twenty lines.

**No axios, no React Query, no SWR.** All HTTP lives in `src/api.ts` as plain
`fetch` calls behind small typed functions. Components never call `fetch`
directly. If you need a new endpoint, add it there.

**No `EventSource` for the live game feed.** The game updates arrive over
Server-Sent Events, but `streamGame()` reads `response.body` manually. That is
on purpose: `EventSource` cannot send the nickname header and cannot be aborted
cleanly. The manual reader is why `src/hooks/useGame.ts` contains retry logic, a
stall watchdog and a generation counter — read the comments there before
changing it. A dropped connection that is not noticed leaves the board frozen
with no error, which is the bug class that code exists to prevent.

**No `tailwind.config.js`.** This is Tailwind **v4**, wired in as a Vite plugin
(`@tailwindcss/vite`). Configuration lives in CSS, not JS. Utility classes are
used directly in JSX; global styles and the `.piece-slot` / `.board-grid` rules
are in `src/index.css`.

**No component library.** Buttons, cards and modals are local components with
Tailwind classes.

**No global state library.** State is either local `useState`, a custom hook
(`useGame`, `useLobby`), or the theme context in `src/theme.tsx`.

## The production bundle (the trap that costs sessions)

In production the FastAPI backend serves a **prebuilt** copy of this app from
`web/dist`. Editing files in `src/` does nothing for a user hitting port 8000
until you rebuild:

```sh
cd web && npm run build     # runs tsc --noEmit, then vite build
```

So if a bug "persists after the fix", check whether you are looking at a stale
bundle before debugging code. `npm run dev` does not have this problem — it
compiles on the fly. This asymmetry is why a fix can look broken in one place
and correct in the other.

`web/dist` is generated and not tracked in git.

## Where things live

| Path | What it is |
|---|---|
| `src/main.tsx` | Entry point; mounts `<App>` inside `<ThemeProvider>` |
| `src/App.tsx` | Hash router: lobby or game |
| `src/api.ts` | Every HTTP and SSE call |
| `src/hooks/useGame.ts` | Game state, SSE connection, reconnect/watchdog |
| `src/hooks/useLobby.ts` | Lobby polling/matchmaking state |
| `src/components/Board.tsx` | The playable board |
| `src/components/RulesPanel.tsx` | Rules reference and its mini-boards |
| `src/components/GameScreen.tsx` | In-game layout |
| `src/components/Lobby.tsx` | Pre-game screen |
| `src/theme.tsx` | Board colour themes and piece set |
| `src/pieceArt.tsx` | SVG piece artwork |
| `src/lib/board.ts` | Square naming and display ordering |

## Conventions that matter

- **Square indexing is engine-side**: `a1 = 0`, `h8 = 63`, row-major. Use
  `orderFor()` from `src/lib/board.ts` to lay out a board — do not compute
  display order yourself. A rank-only flip is a mirror image and silently
  inverts every square colour. That bug has already happened once.
- **Only dark squares are playable**, i.e. `(file + rank) % 2 === 0`.
- **SVG gradient ids must be unique per instance**; `pieceArt.tsx` uses
  `useId()`. Duplicate ids make pieces paint with no fill.
- **A page refresh forfeits the current game** (leave beacon on unmount). Do not
  test by refreshing mid-game and report it as a bug.
- **`npm run build` before reporting a production bug as fixed.**

## Where the project is going

See `../milestones.md` at the repo root for the planned versions (AI opponent,
persistence and history, ratings) and the seams each one introduces. If you are
adding a feature, check whether it is already scheduled and which layer it is
meant to live in.
