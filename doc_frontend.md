# Checkers — The Frontend, and the Question That Bothers Everyone

> Companion to `doc.md` (the FastAPI side). Written for someone who knows `useState` / `useEffect` / props but has not internalised how a React app is built and shipped.

Everything here is checked against this repo's config files.

---

## 1. The headline: React does not run on the server

This is the whole confusion, so let us kill it first.

FastAPI does **not** run React. FastAPI serves **one HTML file and one JavaScript file**. The browser downloads them, and *the browser* runs React.

Concretely, after `npm run build` the folder `web/dist/` contains:

```
web/dist/index.html                  ~630 bytes
web/dist/assets/index-XXXX.js        ~269 KB   (your entire app, minified)
web/dist/assets/index-XXXX.css       ~39 KB    (Tailwind output)
```

`engine/api/application.py` ends with:

```python
app.mount("/", StaticFiles(directory=dist, html=True), name="web")
```

That is it. That single line is the entire **"frontend hosted by FastAPI"** story. FastAPI's job is to be a file server for those three files, plus answer JSON on `/games` and `/lobby`.

So when you open `http://localhost:8000`, this happens:

```
browser  --GET /-->            FastAPI -> StaticFiles -> index.html
browser  parses <script src="/assets/index-XXXX.js">
browser  --GET /assets/...js--> FastAPI -> StaticFiles -> the bundle
browser  EXECUTES the bundle  -> React boots, draws the whole UI
React    --POST /games/... -->  FastAPI -> JSON
```

The server never renders a single pixel. There is no template engine, no server-side rendering, no Python in the page. If you disabled JavaScript, you would get an empty `<div id="root"></div>` and nothing else.

> **Why this is the same server and not two servers:** because one process is perfectly capable of handing out files and answering JSON. Splitting them would buy nothing except a CORS configuration.

---

## 2. The two modes: dev and production

There are two completely different setups, and mixing them up is the #1 source of "why is my change not showing".

### 2.1 Production (what you have been running)

```sh
npm run build            # tsc type-check, then vite builds web/dist
uvicorn engine.api:app   # FastAPI serves the API *and* web/dist
```

**One** process, **one** port (8000), **one** origin. Everything is same-origin, so no CORS, no proxy, no second server. `index.html` references `/assets/index-...js` with an absolute path, which works because the app is served from `/`.

> ⚠️ **Changing anything in `web/src` requires `npm run build` again.** FastAPI reads `web/dist` from disk on every request, so no restart is needed — but if you forget the build, you are looking at yesterday's JavaScript. This cost us a whole debugging session this week: a bug that had already been fixed kept appearing because the bundle predated the fix.

### 2.2 Development (`npm run dev`)

```sh
uvicorn engine.api:app --port 8000      # terminal 1: the API
cd web && npm run dev                   # terminal 2: Vite on :5173
```

Now the browser loads the UI from **Vite's** server, not FastAPI's. Vite serves the *source* files (not a bundle), transpiles TypeScript/JSX on the fly, and hot-reloads on save. FastAPI serves only JSON.

But then the page at `localhost:5173` would call `localhost:5173/games`, which is Vite, which has no idea what a game is. That is what the **proxy** in `vite.config.ts` fixes:

```ts
server: {
  port: 5173,
  proxy: {
    "/health": "http://127.0.0.1:8000",
    "/games":  "http://127.0.0.1:8000",
  },
},
```

Any request starting with `/games` is forwarded to uvicorn. The browser thinks it is talking to one server; Vite quietly relays. That is also why there is no CORS problem in dev even though two ports are involved.

> ⚠️ **Known gap:** `/lobby` is missing from that proxy list. In dev, the lobby polling would hit Vite and get `index.html` back instead of JSON, and `JSON.parse` would throw. If you want to work on matchmaking with `npm run dev`, add `"/lobby": "http://127.0.0.1:8000"`. Production is unaffected (same origin), which is why nobody noticed.

### 2.3 Why Vite needs a build step at all

Browsers do not understand JSX (`<Board />`) or TypeScript types, and your code is split across dozens of files with `import` statements. Vite:

1. transpiles TS + JSX to plain JavaScript,
2. resolves every `import` into one file (**bundling**),
3. runs Tailwind and emits one CSS file,
4. hashes the filenames (`index-CSwTAP9J.js`) so browsers cache them forever,
5. rewrites `index.html` to point at the hashed names.

`npm run build` is literally `tsc --noEmit && vite build`: a type-check that emits nothing, then the build. **A type error stops the whole thing.**

---

## 3. The source tree, and why it is split that way

```
web/index.html                 the ONE html file; contains <div id="root">
web/src/main.tsx               entry point: mounts <App/> into #root
web/src/App.tsx                which screen to show (lobby vs game)
web/src/types.ts               TS types mirroring the JSON from FastAPI
web/src/api.ts                 every fetch call, plus the SSE client
web/src/theme.tsx              board colours + piece set, via Context
web/src/pieceArt.tsx           all SVG artwork
web/src/lib/board.ts           square<->index math, orientation
web/src/lib/sound.ts           cue() blips
web/src/hooks/useGame.ts       ALL game state + the event stream
web/src/hooks/useLobby.ts      presence + invites
web/src/components/*.tsx       dumb-ish rendering
```

The rule the repo follows: **components render, hooks own state, `lib/` is pure**.

When you look for a bug, that split tells you where to look:

| Symptom | Look at |
|---|---|
| "The board shows the wrong highlight" | `Board.tsx` (render) or `useGame.ts` (data) |
| "The move is rejected" | `api.ts` or the backend |

---

## 4. Bootstrap: from empty div to a running app

```html
<!-- index.html -->
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

```tsx
// main.tsx
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
);
```

Four things to notice:

- `createRoot(...).render(<App/>)` is the entire **"React is running now"** moment.
- `ThemeProvider` wraps App, so any component can call `useTheme()` to get the current board palette / piece set. It is React Context, nothing magic.
- **`StrictMode` double-invokes effects in development only.** This is why a development build can open two event streams or fire two requests; the production bundle does not do it. Do not chase "duplicate request" bugs that only exist under `npm run dev` until you have ruled this out.
- The script tag says `/src/main.tsx`. In dev, Vite serves and compiles that. In production, `vite build` has already replaced it with `/assets/index-XXXX.js`. Same HTML file, different script — that is the only difference between the two modes from the HTML's point of view.

---

## 5. Routing without a router

There is no React Router. `App.tsx` decides what to show from the URL **hash**:

```tsx
const [gameId, setGameId] = useState<string | null>(() => gameIdFromHash());
// ...
return gameId ? <GameScreen key={gameId} .../> : <Lobby .../>;
```

So `#/game/abc123` opens a game and anything else shows the lobby. The hash is used because **the server never sees it**: `GET /` returns `index.html` regardless, so deep links work without any server-side route configuration. That is why the StaticFiles mount can use `html=True` and call it done.

`key={gameId}` is doing real work: React **unmounts and remounts** `GameScreen` when the id changes, so all game state from the previous game is thrown away.

---

## 6. State ownership — where everything lives

There are only two hooks with real logic, and understanding them means you understand the app.

### 6.1 `useLobby(busy, onMatch)`

Owns matchmaking presence. Two effects:

- a heartbeat every **5 s** (10 s while `busy`), so other players can see you;
- a status poll every **1.5 s** *only while idle* — inside a game it stops entirely and just heartbeats, so it does not compete with the game stream.

When the server says `state: "matched"`, it calls `onMatch(game_id)`, which `App` turns into a hash change. That is how accepting an invite teleports you into the game.

### 6.2 `useGame(gameId, onLeave)` — the important one

It owns: the game state, the selected square, errors, busy flags, elapsed time, and the event stream. It returns one object (`lastMove`, `yourColor`, `select`, …), and `GameScreen` is a pure rendering of it.

Two things to understand:

**(a) It derives, it does not store, "the opponent's last move".**

```ts
const opponentColor = yourColor === "BLACK" ? "WHITE" : "BLACK";
const lastMove = state
  ? ([...state.history].reverse().find(m => m.player === opponentColor) ?? null)
  : null;
```

This was a deliberate fix: storing a `lastMove` in state meant your own move briefly highlighted itself. Deriving from `history` means the highlight is always "the most recent move by the other side", which is what a player needs to see.

**(b) It owns the SSE connection** — covered in §7.

### 6.3 The rule that keeps this maintainable

Only `useGame` and `useLobby` call `api.*`. Components receive data as props and send intentions as callbacks (`onSquareClick`, `onLeave`). So when a server contract changes, you edit `api.ts` + one hook, not a dozen components.

---

## 7. The live connection (SSE) from the browser side

The server holds an HTTP response open and writes frames. On the client that means **you cannot use `EventSource`**, because it cannot send the `X-Player-Token` header. So `api.ts` reads the stream manually with `fetch` + `ReadableStream`:

```ts
const res = await fetch(`/games/${id}/events`, { signal, headers: {...} });
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
for (;;) {
  const { value, done } = await reader.read();
  if (done) return;
  onActivity?.();                       // any bytes = socket alive
  buffer += decoder.decode(value, { stream: true });
  let split = buffer.indexOf("\n\n");   // frames are separated by a blank line
  while (split >= 0) {
    const frame = buffer.slice(0, split);
    buffer = buffer.slice(split + 2);
    for (const line of frame.split("\n"))
      if (line.startsWith("data: ")) onState(JSON.parse(line.slice(6)));
    split = buffer.indexOf("\n\n");
  }
}
```

Points worth knowing:

- `TextDecoder({stream:true})` is **required**: a multi-byte character can be split across two chunks, and decoding each chunk independently would corrupt it.
- The `buffer` exists because a frame can arrive split across reads. You append, then look for the `\n\n` terminator, and keep the remainder.
- Lines starting with `:` (the keepalive comments) are ignored for data — but they **DO** call `onActivity`, because receiving them proves the socket is alive.

### 7.1 Reconnect, and the watchdog that matters

`useGame`'s stream effect handles three failure modes:

1. **Clean end / error** → reconnect with exponential backoff (0.3 s doubling to 5 s), reset to 0.3 s once bytes flow again.
2. **Tab hidden** → abort the stream (a hidden tab cannot paint; holding the socket wastes a server thread) and reconnect on `visibilitychange`.
3. **Silent death** → the case that caused *"the board doesn't update until I refresh"*. On Wi-Fi, a socket can die without any error event; `reader.read()` simply never resolves. The fix is a **watchdog**: if 32 s pass with no bytes (the server pings every 15 s), abort and reconnect.

There is also a **generation counter** (`gen`). Every new stream increments it, and an old stream's `.finally` only schedules a reconnect when its own `my === gen`. Without that, the visibility handler and the backoff timer could both open a connection, and every change would be applied twice.

### 7.2 What arrives is the FULL state, never a delta

Every `data:` frame is the complete game object — board, legal moves, history, flags. There is no "square 34 moved to 27" message. Consequences:

- Losing a frame is harmless; the next one is still complete.
- Reconnecting needs no catch-up protocol: the first frame is the current truth.
- The client can stay dumb. It replaces `state` and re-renders.
- Frames are ~2–3 KB, sent once per move, so the simplicity is affordable.

> If you ever wonder why `apply(next)` just calls `setState(next)` — this is why.

---

## 8. Rendering: how a click becomes a move

`Board.tsx` renders 64 `<button>`s in an order given by `orderFor(yourColor)` (so each player sees their own back row at the bottom). Each button is purely declarative:

```tsx
const isLast = lastMove && (lastMove.from_sq === sq || lastMove.to_sq === sq);
// ...
{isLast && <span className="absolute inset-0 bg-yellow-300/30" />}
```

Click flow:

```
click square 41
  -> Board calls onSquareClick(41)
  -> GameScreen passes it to select() from useGame
  -> select(): if something was already selected and 41 is a legal target,
     POST /games/{id}/moves; otherwise if square 41 holds your piece, select it
  -> the POST response is the new full state -> setState -> re-render
```

The highlight colours are all just absolutely-positioned spans inside the button, stacked in order. There is no canvas and no SVG board.

> ⚠️ **A lesson worth remembering** (it bit us this week): `pieceArt.tsx` draws each piece as an `<svg>` whose size comes from CSS classes `.piece-slot` / `.piece`. The SVGs are generated with a gradient whose `id` used to be a fixed string. When two boards rendered on one page, `url(#pc-w)` resolved to the gradient in the *hidden* copy, and pieces painted with no fill — looking transparent, with black and white indistinguishable. Fixed with `useId()` per instance. **If artwork ever looks blank, suspect duplicate SVG ids before CSS.**

---

## 9. Types and the wire contract

`types.ts` mirrors the JSON from `GameRecord.state()` **by hand**. There is no code generation; if the backend adds a field, the type does not know until you edit it. The important ones:

| Field | Type | Note |
|---|---|---|
| `GameState.board.squares` | `(Piece \| null)[64]` | |
| `GameState.history` | `MoveRecord[]` | includes `player` |
| `GameState.your_color` | `"WHITE" \| "BLACK" \| null` | per-caller |
| `GameState.version` | `number` | the change counter |

`your_color` is the **only** field that differs between the two players. `null` means **spectator** — and the UI uses that to show "Spectating" and disable selection rather than erroring.

---

## 10. Styling: Tailwind, and why the HTML looks like that

Tailwind is utility CSS compiled at build time: `className="flex gap-2 p-4"` becomes real CSS in `index-XXXX.css`. Classes that never appear in source are never emitted, which is why the CSS is 39 KB rather than a full framework.

`index.css` holds the handful of things that are awkward as utilities:

- `.board-grid` (the 8×8 grid, with **BOTH** `grid-template-columns` and `grid-template-rows` — dropping the rows makes kings render bigger than men),
- `.piece-slot` / `.piece` (SVG sizing),
- `.card`, `.btn-*`.

The arbitrary-value syntax you will see is Tailwind, not React:

```css
lg:max-w-[min(100%,calc(100dvh_-_15rem))]
```

…means "at lg breakpoint, cap width at the smaller of 100% or viewport height minus 15rem". **Underscores stand for spaces.** That specific one is what stops the square board overflowing vertically on a short desktop window.

---

## 11. Things that will bite you

1. **Forgot `npm run build`** → you are running yesterday's app. If a fix "does not work", check `web/dist` mtimes before reading code.
2. **Editing `web/dist` directly** → the next build overwrites it. Never do it.
3. **StrictMode double effects in dev** → duplicate streams/requests are a dev artefact.
4. **`/lobby` is missing from the dev proxy** → lobby testing under `npm run dev` fails until you add it (production is fine).
5. **Hashed filenames** → after a build, the old JS may still be cached. Hard-refresh (`Ctrl+Shift+R`) before concluding anything.
6. **Reloading mid-game forfeits** → `useGame`'s cleanup sends a leave beacon on unmount, so a refresh counts as leaving. Finish the game before you refresh.

---

## 12. File map

| File | Responsibility |
|---|---|
| `web/index.html` | the only HTML; `<div id="root">` + one script |
| `vite.config.ts` | dev port 5173 + proxy to :8000 |
| `package.json` | `dev` / `build` / `preview` scripts |
| `src/main.tsx` | `createRoot` + `ThemeProvider` + `App` |
| `src/App.tsx` | hash routing: lobby or game |
| `src/api.ts` | all fetches + the SSE reader |
| `src/types.ts` | hand-written mirror of the JSON contract |
| `src/theme.tsx` | board palettes, piece set, Context |
| `src/pieceArt.tsx` | all SVG artwork (uses `useId` for gradients) |
| `src/lib/board.ts` | `orderFor()`, `squareName()`, `FILES` |
| `src/lib/format.ts` | clock formatting |
| `src/lib/sound.ts` | WebAudio `cue()` |
| `src/lib/clipboard.ts` | copy with fallback |
| `src/hooks/useGame.ts` | game state + SSE + watchdog + actions |
| `src/hooks/useLobby.ts` | heartbeat + invite polling |
| `src/components/GameScreen.tsx` | layout only |
| `src/components/Board.tsx` | the 8×8 grid and all highlights |
| `src/components/RulesPanel.tsx` | rules copy + mini-board illustrations |
| `src/components/PlayerCard.tsx` | name / online / clock |
| `src/components/MoveList.tsx` | move history rows |
| `src/components/GameOverCard.tsx` | result modal + rematch |
| `src/components/CopyButton.tsx` | copy with feedback |
| `src/components/Lobby.tsx` | landing page, tabs, appearance picker |
