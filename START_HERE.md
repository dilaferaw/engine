# START_HERE — agent entry point

Read this file first (it is short). Then read only the parts of the other
docs you actually need — see "Reading efficiently" below.

## What this project is

A **custom checkers variant**: pure-Python engine (`engine/`), FastAPI HTTP +
SSE layer (`engine/api/`), React + Tailwind + Vite SPA (`web/src/`). No
database — games live in process memory and vanish on restart. Two browser
tabs are two players (identity is a token in `sessionStorage`).

The rules are *not* standard checkers. Do not assume standard behaviour.
Source of truth: the game-rules specification the owner supplied (see
`AGENT_NOTE.md` and the rule comments in `engine/`). The three load-bearing
differences: **single captures are illegal**, **death squares kill on
landing**, **promoting poisons the opponent's whole home row**. Also:
**having no legal move on your turn is a LOSS, not a draw**
(`engine/rules.py`, enforced by `tests/test_rules.py`).

## Run / test

```sh
uv run uvicorn engine.api:app --port 8000 --host 0.0.0.0   # serves API + web/dist at /
uv run pytest tests -q                                     # backend tests
cd web && npm run build                                    # tsc --noEmit + vite build
```

`ztartupcmd.bash` holds the correct run line. **`startupcmd.bash` is broken**
(stray newline after `engine.`) — do not use it.

## Traps that have already cost someone a session

1. **The backend serves a prebuilt bundle.** `engine/api/application.py`
mounts `web/dist`. Editing `web/src/` changes nothing until you run
`cd web && npm run build`. If a frontend bug "persists after the fix", check
`stat` timestamps of `web/dist/index.html` vs the file you edited before
debugging anything.
2. **SVG gradient ids must be unique per instance.** `web/src/pieceArt.tsx`
uses `useId()` for this. Duplicate ids across two rendered copies of a board
make `url(#...)` resolve inside a hidden subtree, so pieces paint with **no
fill** (looks transparent, black and white indistinguishable). If artwork ever
looks blank, this is the first suspect.
3. **Port 8000 may be another project** (`~/Projects/nostalgia`). Check with
`ss -ltnp | grep :8000` before assuming the server failed.
4. **`web/node_modules` is huge.** Always grep with
`--exclude-dir=node_modules --exclude-dir=.venv`.

## Reading efficiently (required)

This repo has large generated/vendored trees. Never dump whole files or full
command output. Use targeted search first:

```sh
grep -rn "symbol" web/src engine tests --exclude-dir=node_modules --exclude-dir=.venv
rg -n "pattern" -g '!node_modules' -g '!.venv'        # if ripgrep is available
```

Then read only what you need:

- `head -40 file` / `tail -30 file` for shape and exports.
- `sed -n '120,180p' file` for the region a grep hit points at.
- the `read` tool with `offset` + `limit` for long files.
- `cmd | tail -15` for build/test output, never the full log.
- prefer `grep -nE "a|b|c"` over several separate greps.

Guideline: locate with grep, confirm with a 20–60 line window, and only read a
file end-to-end when you are about to rewrite it.

## Where things live (details in `AGENT.md`)

| Area | Path | Note |
| --- | --- | --- |
| Rules engine | `engine/board.py`, `moves.py`, `legality.py`, `rules.py` | rule numbers in comments (R2.6, R4.5, …) |
| Wire/serialization | `engine/storage/models.py` | `GameRecord.state(token)` builds the per-player payload |
| HTTP + SSE | `engine/api/routes.py`, `events.py`, `realtime.py` | state is serialized per subscriber, not broadcast |
| Frontend state | `web/src/hooks/useGame.ts`, `useLobby.ts` | all game state lives here |
| UI | `web/src/components/` | `Board.tsx` = grid/highlights, `RulesPanel.tsx` = rules copy + mini-board scenes |
| Piece artwork | `web/src/pieceArt.tsx` | single owner of all SVG art |

Rule of thumb: components render, hooks own state, `lib/` is pure.

## Other docs

- `AGENT.md` — full layout, invariants, storage design question, git history.
- `AGENT_NOTE.md` — dated scratch notes: environment quirks, traps, what was
  verified when. Append here when you learn something expensive.
- `MATCHMAKING.md`, `API_EXPLAINED.md` — deep dives, read on demand.

## When you finish a change

1. `cd web && npm run build` if anything under `web/src/` changed.
2. `uv run pytest tests -q` if anything under `engine/` changed.
3. Append one dated line to `AGENT_NOTE.md` for anything that cost more than
   one turn.
