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
| `engine/store.py` | `GameStore`, `GameRecord`: seats, names, history, rematch. **No HTTP.** |
| `engine/api_schemas.py` | Pydantic wire models (`BoardModel`, `MoveModel`, ...) |
| `engine/api.py` | Thin FastAPI routes; `translate()` maps store errors to status codes |

Status mapping lives in `STATUS_FOR` in `engine/api.py`. Add a new store
exception there, don't sprinkle `HTTPException` through the store.

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

## Known issues / next steps

- `pytest` (no args) still fails collecting `deeps_tests/test_board.py`:
  it imports `BM, BK, WM, WK` from `tests/helpers.py`, which no longer exports
  them. Pre-existing, unrelated to the web work. Running `pytest tests` is clean.
- `engine/api.py` allows a move from an unseated token (spectator), which makes
  it effectively a shared-seat game. Tighten if that's not wanted.
- No persistence: restarting uvicorn loses every game.
- `GameScreen.tsx` still holds the layout markup (~200 lines); splitting the
  side panel out is the next natural cut.
- No frontend tests. `vitest` + `@testing-library/react` would be the first add.

## Git

Repo was initialised in this workspace (it did not exist before). Recent work:
`7909f0b` per-tab names / copy feedback / hide invites → *this* commit: API and
frontend refactor.
