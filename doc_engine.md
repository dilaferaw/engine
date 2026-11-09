# Checkers — The Game Engine, From Zero

> Third in the set: `doc.md` (HTTP layer), `doc_frontend.txt` (React), and this one.
> Written for someone new to game engines. Every claim is checked against the source in this repo.

After most sections there is a **Concurrency note** and/or an **AI note**. Those are the two things you asked about, and they belong next to the code they concern rather than in a pile at the end.

---

## 0. What a "game engine" actually is

Forget chess engines for a second. A game engine is four things:

1. a **data model** of the position — `Board`, `Piece`
2. a **rules function** — "what moves are legal here?"
3. a **transition function** — "apply this move, give me the new position"
4. a **termination check** — "has someone won?"

That is it. Everything else — AI, UI, networking — is built on top of those four. If you can answer "legal moves?", "apply one", "who won?", you have a game engine.

This engine is a **pure library**. It has zero knowledge of FastAPI, JSON, tokens, browsers or HTTP. You could import it in a Jupyter notebook and play a game by hand. That is a deliberate and very good property: it makes the engine testable in isolation, and it means the HTTP layer can be replaced without touching a single rule.

The whole engine is seven files and roughly 700 lines:

| File | Role |
|---|---|
| `engine/constants.py` | enums (`Player`, `Kind`), board size, who moves first |
| `engine/geometry.py` | square ↔ (file, rank), diagonals, death squares |
| `engine/notation.py` | the `Move` dataclass and its JSON form |
| `engine/board.py` | `Board`, `Piece`, apply/undo, death-square logic |
| `engine/moves.py` | quiet moves + the capture DFS |
| `engine/legality.py` | freeze rules, `legal_moves()`, `check_legal()` |
| `engine/rules.py` | `winner()` / `is_draw()` |

---

## 1. The data model — `Board` and `Piece`

### 1.1 Squares are integers 0..63

There is no 2D array and no `(x, y)` tuple anywhere in hot code. A square is one integer:

```python
sq   = rank * 8 + file      # a1 = 0, h1 = 7, a8 = 56, h8 = 63
file = sq % 8
rank = sq // 8
```

That is `geometry.py`. The reason is speed and simplicity: a list of 64 elements is a flat array, index arithmetic is one multiply, and there is no nested indexing to get wrong. `0` is a1 (bottom-left, from White's printed view), `63` is h8. Only dark squares are playable: `(file + rank) % 2 == 0`.

> **AI note:** flat integer indexing is exactly what you want for a search engine. Zobrist hashing (used later for transposition tables) is defined per square index, so this layout makes it trivial: `zobrist[sq][piece_kind]`.

### 1.2 `Piece` is immutable

```python
@dataclass(frozen=True)
class Piece:
    player: Player     # WHITE | BLACK
    kind: Kind         # MAN | KING
```

Frozen means you never mutate a piece; you replace it. That is a small but important decision: it makes `Board.copy()` cheap and safe (a shallow list copy is enough, because the pieces inside cannot change), and it removes a whole class of aliasing bugs.

Note what is **not** on the piece: "frozen" and "poisoned" are board state, not piece state. A piece is not permanently frozen — its mobility is derived from the position each turn. The docstring in `board.py` says this explicitly. If you ever cache "this piece is frozen" on the `Piece` object, you will have a bug.

### 1.3 `Board`

```python
@dataclass
class Board:
    squares:  list[Piece | None]                       # 64 entries
    turn:     Player = WHITE
    poisoned: dict[Player, bool] = {WHITE: False, BLACK: False}
    history:  list[tuple[list, Player, dict]]          # the UNDO STACK
```

Three fields matter for rules, and one for bookkeeping:

- `squares` — the position. `None` means empty.
- `turn` — whose move it is. White moves first (`STARTING_TURN`).
- `poisoned` — per-side flag: has this side's home row been poisoned yet? (Promotion poisons the *opponent's* row.) This is the variant's signature rule and it is just two booleans.
- `history` — the undo stack. **This is not the move list the UI shows.** Keep that distinction; it is the single most confusing thing in the codebase.

### 1.4 Two different "histories" — read this twice

There are two unrelated lists called history:

**`Board.history`** — in `engine/board.py`

A stack of **full position snapshots**, pushed by `apply()`, popped by `undo()`. Each entry is `(copy_of_squares, turn, copy_of_poisoned)`.

- Purpose: make `undo()` exact and O(1).
- Never leaves the engine.

**`GameRecord.history`** — in `engine/storage/models.py`

A list of **move dicts** (`from_sq`, `to_sq`, `captures`, `dies`, `player`).

- Purpose: the move list the UI renders, and the SSE payload.
- Appended by `InMemoryGameStore.play()`, not by the engine.

**Why two?** Because they answer different questions. Undo needs "restore the exact prior position"; the UI needs "what moves were played, in order, by whom". Storing only the move list and recomputing the position from scratch on undo would be slower and more error-prone; storing only snapshots would leave the client unable to show a move list without diffing boards.

> **Concurrency note:** because `apply()` mutates three fields of a shared object (`squares`, `turn`, `poisoned`) plus appends to `history`, a `Board` is **not thread-safe**. Two threads calling `apply()` on the same `Board` at the same time can interleave and produce a corrupt position. The engine assumes single-threaded, single-writer access. That is fine in principle — but see §9 for where the HTTP layer currently breaks that assumption.

> **AI note:** `Board.copy()` gives you a copy **without history** (it deliberately passes only the three rule fields). That is what you want at the root of a search: you do not care how you got here, only where you are. Inside the search, though, every `apply()` still pushes a snapshot onto history — see §7 for how to exploit that, and where it costs you.

---

## 2. Geometry — diagonals, home rows, death squares

`geometry.py` is 75 lines of pure functions. The important ones:

```python
step(sq, direction) -> int | None      # neighbour, or None off-board
forward_directions(player)             # (SE, SW) for White, (NE, NW) for Black
promotion_square(player)               # 0 for White (a1), 63 for Black (h8)
home_row(player)                       # the four dark squares of your back row
death_squares(player)                  # opponent home row MINUS your promotion square
```

Directions are `(d_file, d_rank)` tuples: `NE=(1,1)`, `NW=(-1,1)`, `SE=(1,-1)`, `SW=(-1,-1)`. `step()` is the only place that does bounds checking, so every other function composes it and cannot go off-board by accident.

### 2.1 The death squares, concretely

```python
STATIC_DEATH_SQUARES = death_squares(WHITE) | death_squares(BLACK)
```

Resolved to indices:

| Side | Promotion | Dies on |
|---|---|---|
| White | `a1 = 0` | `c1, e1, g1 = 2, 4, 6` |
| Black | `h8 = 63` | `b8, d8, f8 = 57, 59, 61` |

`is_death_square(sq, board)` is slightly richer than the constant: it returns `True` for the six static squares **always**, and additionally for any square on a home row whose `poisoned` flag is set. So after White promotes, all of rank 1 becomes lethal — including a1 itself — and the promoted king standing there is safe only because death triggers on *landing*, not on being there (§6).

> **AI note:** `death_squares` and `promotion_square` are tiny and pure, so an evaluation function can ask "how close is this man to promotion / to a death square" very cheaply. That matters more in this variant than material, because walking into a death square loses a piece for free.

---

## 3. The `Move` object

```python
@dataclass
class Move:
    from_sq:  int
    to_sq:    int
    captures: list[int] = []     # squares captured, IN ORDER
    dies:     bool = False       # does the mover die on landing?
```

That is the entire vocabulary of the engine. Everything — quiet move, jump, multi-jump, voluntary death, promotion — is expressed as one of these.

`__post_init__` validates the squares and rejects `from == to`. `to_dict()` / `from_dict()` are the JSON bridge. `length` is `len(captures)`, and it is used constantly by the max-capture rule.

**Why `captures` as a list and not a count?** Because the UI needs to highlight which squares were taken, and because a multi-jump's *order* is part of the move (you may need to know which piece blocked the path). `dies` is separate from `captures` because death is neutral — it is not a capture and gives no credit.

> **AI note:** `Move` is a value object, so `move in legal_moves` is a field comparison — which is what `check_legal` relies on. In a search, avoid that O(n) membership test; you generated the list, so iterate it.

---

## 4. Move generation, part 1 — quiet moves

`moves.py`. A quiet move is any move that captures nothing.

### 4.1 Men

```python
def man_quiet_moves(board, sq):
    for d in forward_directions(piece.player):     # only 2 directions
        to = step(sq, d)
        if to is None or board.squares[to] is not None:
            continue
        moves.append(Move(sq, to, [], is_death_square(to, board)))
```

Note what is allowed: landing on a death square as a quiet move **is legal**, and the move is marked `dies=True`. That is *voluntary death*, a legal pass-like move. It is not filtered out here; it is filtered by the freeze rule later.

### 4.2 Kings

```python
def king_quiet_moves(board, sq):
    for d in DIRECTIONS:                 # all 4 diagonals
        cur = step(sq, d)
        while cur is not None and board.squares[cur] is None:
            moves.append(Move(sq, cur, [], is_death_square(cur, board)))
            cur = step(cur, d)
```

A king slides until it hits something. Every empty square along the way is a legal destination. Again, death squares are included and marked.

> **Concurrency note:** both functions only READ the board. They are safe to call from any number of threads *as long as nobody is mutating that board*. The engine does not enforce that; the caller must.

> **AI note:** quiet moves are not generated if any capture exists (the forced-capture rule, §5.4). So in a capture position you skip this entire branch — a free pruning that most engines have to do by hand.

---

## 5. Move generation, part 2 — captures (the DFS)

This is the heart of the engine and the only genuinely tricky code. Read it slowly.

### 5.1 The shape of the problem

A capture sequence is a *path*: jump, land, maybe jump again from there, etc. The number of paths is not fixed — it depends on the position. So you cannot write two nested loops; you need a **depth-first search**.

```python
def dfs(pos):
    options = steps(pos)                    # every (victim, landing) from here
    if not options:
        if captured: results.append(Move(origin, pos, list(captured)))
        return
    for victim, land in options:
        captured.append(victim)
        if is_death_square(land, board):
            results.append(Move(origin, land, list(captured), dies=True))
        else:
            visited.add(land)
            dfs(land)                       # recurse
            visited.discard(land)
        captured.pop()                      # backtrack
```

`captured` is the path so far. `visited` prevents landing on the same square twice (which would let a king loop forever). When there are no further jumps, the path is recorded as a `Move`. That is classic backtracking.

### 5.2 How a step is found, for men vs kings

```
MAN:   victim = step(pos, d);  land = step(victim, d)
       require capturable(victim) and empty(land) and land not in visited

KING:  scan along d until the first OCCUPIED square
       if that square is capturable, it is the victim
       then land on ANY empty square beyond it along the same diagonal
```

So a king's "flying capture" is: slide, find the first piece, and if it is an enemy, every empty square past it is a landing option. Each landing is a separate branch of the DFS — which is why a king in an open position explodes the move count.

### 5.3 Three decisions encoded here (and why they matter)

- **Captured pieces stay on the board as blockers.** `occupied()` checks `board.squares[sq]`, and the DFS never removes the victim from the board — it only tracks it in `captured`. So a king cannot fly *through* a square whose piece was already captured earlier in the same sequence. This is decision **A5** in the spec and it is deliberate.
- **The origin square is empty but cannot be landed on again.** `visited` starts with `{origin}`, and `occupied()` special-cases `sq != origin`.
- **Death ends the sequence.** If a landing is lethal, the move is recorded immediately with `dies=True` and the DFS does not recurse. The pieces captured before that landing still count for the max-length rule (R3.5).

### 5.4 Why "single captures are illegal" produces freezing

`capture_sequences` happily returns sequences of length 1. It is the *caller* that decides what they mean:

```python
_is_frozen(sequences)  ==  sequences and all(m.length == 1)
```

A piece is **frozen** if it has captures but every one of them is a single one. Since single captures are not legal moves, such a piece has no legal capture and — because quiet moves are forbidden for frozen pieces — no legal move at all. That is the whole freezing rule, implemented in one line.

Note the subtlety: a piece with **no** capture sequences is *not* frozen (it can move quietly). A piece with one single capture and one double capture is not frozen either (`all()` is `False`) — it just must take the double.

> **Concurrency note:** `capture_sequences` is read-only with respect to the board and uses only local mutable state (`captured`, `visited`), so it is reentrant and thread-safe. This is the one part of the engine you can safely run in parallel on the same `Board` — which is exactly what a parallel AI search would want.

> **AI note:** this DFS is where 90% of your search time will go. Two practical consequences:
> 1. Cache it per position (a transposition table keyed by a Zobrist hash of `squares + turn + poisoned`). The same position recurs constantly.
> 2. In capture-rich positions the forced-max rule means the *legal* move list is usually 1–3 moves. That is a huge natural pruning advantage; lean on it.

---

## 6. Legality — putting it together

`legality.py` is 60 lines and defines the public rules API.

```python
def legal_moves(board) -> list[Move]:
    captures, movable = [], []
    for sq in board.pieces(board.turn):
        seqs = capture_sequences(board, sq)
        if _is_frozen(seqs):        continue          # frozen: no moves at all
        movable.append(sq)
        captures.extend(m for m in seqs if m.length >= 2)
    if captures:
        best = max(m.length for m in captures)
        return [m for m in captures if m.length == best]   # forced max
    return [m for sq in movable for m in quiet_moves(board, sq)]
```

Read the structure: **one pass** over the mover's pieces, compute each piece's capture sequences **once**, use that single result for both the freeze test and the capture list. That is a deliberate optimisation — the naive version would call `capture_sequences` twice per piece.

Then the rule cascade:

1. If any legal (multi-)capture exists → return only the **longest** ones. Ties are all returned; the player chooses.
2. Otherwise → all quiet moves of all non-frozen pieces.

So "captures are forced" and "max capture is mandatory" are not separate checks scattered around the codebase. They **fall out of the shape of this function**. That is good design: there is one place to change if the rule ever changes.

`check_legal(board, move)` is the validator used by `apply()`. It calls `legal_moves`, does `move in legal`, and if that fails it re-derives *why* to produce a specific error message (`"R3.2: captures are forced"`, etc.). Those messages end up as 400 responses through `translate()` in the API layer.

### 6.1 Cost

`legal_moves` is the expensive operation: O(pieces × branching of the capture DFS). For this game it is microseconds, but for AI it is the hot path.

> **Concurrency note:** `legal_moves` and `check_legal` are pure reads — safe to run concurrently on a board nobody is mutating. Note that `board.pieces(turn)` itself iterates all 64 squares, so it is O(64) before any rules work happens.

> **AI note:** call `legal_moves` **once per node**, not once per candidate move. The pattern `for m in legal_moves(board): ...` is correct. The anti-pattern is `for m in candidate_moves: check_legal(board, m)` — that regenerates the whole list for every candidate. `check_legal` is for validating *untrusted input from the network*, not for search.

---

## 7. Applying a move — the state transition

`Board.apply(move, validate=True)` is the only mutator. It does, in order:

1. `if validate: check_legal(self, move)` — may raise `ValueError`
2. sanity checks (piece exists, victims are enemies, target empty)
3. `dies = is_death_square(move.to_sq, self)` — **pre-move board!**
4. `self.history.append((list(squares), turn, dict(poisoned)))`
5. remove captured pieces
6. clear `from_sq`
7. if a **KING** left its promotion square → poison the opponent's home row
8. if not `dies`: place the piece on `to_sq` (promoting if it reached its promotion square)
9. `self.turn = other(self.turn)`

Several details are worth defending in a review:

- **Step 3 happens before step 5.** Death is decided by the landing square in the *pre-move* position. If you checked after removing captures, a poisoned row or a just-changed flag could give a different answer. Order matters.
- **Step 7 is the A2 decision.** A king *leaving* its promotion square poisons the opponent's row. The spec's original wording was about promotion, but the implementation uses "leaving" so that a king cannot sit on a live promotion square forever and then hop off after the row is poisoned. If you change this, you change a rule.
- **Step 8 is why a dying piece is not placed.** If `dies` is true, the piece is simply removed: it does not promote, it does not block, and the opponent gets no credit. That is the "death is neutral" rule expressed as one `if`.
- **Step 4 copies the whole position.** `list(self.squares)` is 64 pointers. That is the undo mechanism — see below.

### 7.1 Undo is a stack pop

```python
def undo(self):
    if not self.history: raise IndexError(...)
    self.squares, self.turn, self.poisoned = self.history.pop()
```

Because `apply` pushed a full snapshot, `undo` is one line and exactly correct — no reconstruction, no re-deriving poison flags, no possibility of drift.

### 7.2 The cost of that design

Each `apply` allocates a 64-element list plus a small dict. For a real game (hundreds of moves) that is nothing. For an AI search (millions of nodes) it is the dominant allocation. Two options when you get there:

- **Cheap now:** `board = original.copy()` at the root, then `apply(validate=False)` / `undo()` around each child. You still pay the snapshot, but you avoid `check_legal`.
- **Fast later:** a proper make/unmake that mutates and restores only the squares that changed (source, destination, victims, poison flag). Maybe 10–20 lines. Do this only if profiling says so.

> **Concurrency note:** `apply` is the **only** mutator, and it is not atomic. Two threads calling it on the same `Board` will interleave at the Python bytecode level. Since FastAPI runs `def` handlers in a threadpool (see `doc.md` §11), two simultaneous POSTs to the same game *can* reach `apply` concurrently. Nothing in `InMemoryGameStore` currently takes a lock. See §9.3 — this is a real bug, not a theoretical one.

> **AI note:** `apply(validate=False)` is your search workhorse. It skips `check_legal` — which is the expensive whole-list regeneration — while still performing the state transition correctly. Only use `validate=True` on the one move that came from the network. This single flag is probably a 5–10× speedup for a search loop.

---

## 8. Termination — `winner()` and `is_draw()`

```python
def winner(board):
    white, black = has_pieces(WHITE), has_pieces(BLACK)
    if white and not black: return WHITE
    if black and not white: return BLACK
    if white and black and not legal_moves(board): return other(board.turn)
    return None

def is_draw(board):
    return winner(board) is None and not white and not black
```

Three things to note:

- **No legal move is a LOSS for the side to move** (`other(board.turn)`), **not** a draw. `tests/test_rules.py` enforces this. It is a variant rule and it is the one most likely to be misremembered — the documentation in this project has been wrong about it twice.
- `is_draw` is essentially unreachable in normal play: it requires *both* sides to have zero pieces. It exists for completeness and for fuzz tests that reach weird positions.
- The function calls `legal_moves(board)`, which is the expensive call, but only after the cheap piece-count checks. That ordering is deliberate.

> **Concurrency note:** `winner()` is a pure read (it calls `legal_moves`, also pure). Safe to call concurrently.

> **AI note:** in a search you already generated the move list for the node, so do **not** call `winner()` — you would regenerate it. Check `if not moves:` using the list you have, and score the node as a loss for the side to move. Calling `winner()` per node is a classic accidental 2× slowdown.

---

## 9. How the API harnesses the engine

The engine knows nothing about HTTP. The bridge is exactly three layers, and no layer skips another:

```
engine/api/routes.py           parses JSON, calls the repository
    -> engine/storage/memory.py    owns the GameRecord, calls the engine
        -> engine/board.py         apply() mutates the Board
```

The only place engine objects appear in the API layer is at the boundary:

- **Inbound:** `MoveModel` (Pydantic) → `MoveModel.to_move()` → engine `Move`.
- **Outbound:** `GameRecord.state()` calls `board.to_dict()` and `legal_moves`, and hands back plain dicts. The engine's objects never escape as objects.

That conversion discipline is why you can rewrite the storage backend, or even serialize a game to SQLite, without touching the rules.

### 9.1 The call chain for one move

```
POST /games/{id}/moves  {from_sq, to_sq, captures, dies}
  -> play_move() in routes.py
  -> repo.play(game_id, token, move.to_move())
       color = color_for(seats, token)
       if color is not None and color != board.turn.value: raise NotYourTurn
       board.apply(move)                  # validate=True by default
       record.history.append({**move.to_dict(), "player": color})
       record.touch()                     # version += 1
       on_change(game_id, version)        # wake the SSE streams
  -> .state(game_id, token)               # serialize for THIS player
```

Note the engine's `ValueError("illegal move")` (or a rule-specific message from `check_legal`) is what becomes the HTTP 400 via `translate()`. The engine deliberately does not know what a status code is.

### 9.2 `legal_moves` is cached per version

`GameRecord.derived()` computes `legal_moves(board)` and `freeze_map(board)` once and caches them alongside `version`. Every `state()` call reuses them until the next mutation. This is why a 3 KB payload per move is cheap even though it contains ~30 legal moves: they were generated once, at mutation time, not per reader.

Worth being able to say out loud: **the engine has no cache of its own.** Caching is the *storage layer's* concern, keyed by the version it belongs to.

### 9.3 The concurrency gap (be honest about this)

`InMemoryGameStore.play()` does:

```python
record = self.require(game_id)
record.board.apply(move)         # mutates
record.history.append(played)    # mutates
record.touch()                   # version += 1
```

There is **no lock**. FastAPI runs these `def` handlers in a threadpool, so two requests for the same `game_id` can run this sequence on two threads. Possible outcomes:

- both validate against the same `board.turn` and both `apply` — one of them moves the wrong colour, or
- both bump `version` to the same value, or
- a state read in between sees a half-applied board.

In practice your users are two people taking turns, so the window is small. But it is a genuine race, not a theoretical one, and it is the first thing to fix if you ever open this to the public. The fix is ~3 lines: a `threading.Lock` per game (or one global lock) around the read-mutate-version sequence in `play`, `undo`, `join`, `leave`, `request_rematch`, `decline_rematch`. The engine does not need to change — it is the *caller* that must serialise access to a `Board`.

> **Concurrency note (the summary):**
> - Engine functions are pure/reentrant **except** `Board.apply` / `Board.undo`.
> - `Board` is single-writer.
> - The store does not currently enforce single-writer.
> - Fix belongs in the store, not the engine.

---

## 10. Concurrency and async — what actually helps, and what doesn't

You asked how to "better support concurrency by async or multithreading". Be clear about what each buys, because most of the obvious answers are wrong for this code.

### 10.1 Making the engine `async` would buy nothing

`async` helps when you are **waiting** on something external (network, disk, database). The engine never waits. `legal_moves` is pure CPU that finishes in microseconds. Writing `async def legal_moves` would add coroutine overhead and buy exactly zero concurrency, because there is nothing to yield to.

> The rule of thumb: **async is for I/O, threads/processes are for CPU.**

### 10.2 What async *does* help with — and it is not the engine

The real async win is the SSE stream (`doc.md` §11.2). Today each open tab parks a threadpool worker inside `cond.wait()`. Making `events.py` async (an `asyncio.Event` per subscriber, `async def` generator) turns each idle stream into a coroutine instead of a thread. That raises your ceiling from ~40 tabs to thousands. **That refactor does not touch the engine at all.**

### 10.3 Multithreading: where it helps and where it is a trap

- **Helps:** running N independent games' move generation in parallel. Each game has its own `Board`, so there is no shared state. This is embarrassingly parallel.
- **Helps a lot:** an AI search. Root-level parallelism (split the legal moves across workers) is straightforward and gives near-linear speedup up to core count.
- **Trap:** Python's GIL. Threads do not give you parallel CPU on CPython. For real parallel search you need `multiprocessing` or `concurrent.futures.ProcessPoolExecutor` — which means pickling the `Board` per task. That is fine (it is just a list and two dicts) but it is not free.
- **Trap:** sharing one `Board` between threads for "performance". Do not. Give each thread its own `copy()`. Copies are cheap because `Piece` is frozen.

### 10.4 The realistic upgrade path, in order

1. **Add a lock in the store** (correctness, ~3 lines). Do this first.
2. **Make the SSE generator async** (capacity, ~50 lines, engine untouched).
3. **Only then** consider parallel AI search with a process pool.

Notice that none of these three requires changing the rules engine. That is the payoff of keeping it a pure synchronous library: the concurrency story lives in the layers around it, where it belongs.

---

## 11. Building an AI opponent — a concrete plan

You asked for minimax or "something better suited". Here is the honest answer: for this game, **minimax with alpha-beta pruning** is the right starting point, and the variant's rules make it unusually effective. Do not start with neural networks; you will spend a month and lose to a 6-ply alpha-beta.

### 11.1 The four pieces you need

A search engine is tiny. You need:

| Piece | Status |
|---|---|
| `legal_moves(board)` | **already exists** — it is your move generator |
| `board.copy()` | **already exists** |
| `board.apply(m, validate=False)` / `board.undo()` | **already exists** |
| `evaluate(board, player) -> float` | **you write this** |

So 90% of the infrastructure is already in the engine. The missing piece is the evaluation function and the search loop.

### 11.2 Evaluation function — what to count

Start dumb, measure, then refine. A reasonable first version:

```
+100  per man
+300  per king
+     small bonus for advancing toward your promotion square
-     penalty for standing adjacent to a death square you could be pushed onto
+     bonus for each enemy piece that is frozen
+     small bonus for having the move (tempo)
```

Then return `score_for_white - score_for_black` (or negate for Black, depending on your convention — pick one and stick to it; **sign bugs are the #1 minimax bug**).

This variant gives you a genuinely interesting evaluation problem: material is not the whole story, because a piece can die for free on a death square and a frozen piece is worth less than an active one. That is exactly the kind of thing you can talk about in an interview.

### 11.3 The search — start here

```python
def negamax(board, depth, alpha, beta, player):
    moves = legal_moves(board)          # once per node
    if not moves:
        return -INF                     # no legal move = loss (variant rule!)
    if depth == 0:
        return evaluate(board, player)
    best = -INF
    for m in moves:
        board.apply(m, validate=False)  # skip the expensive check
        score = -negamax(board, depth-1, -beta, -alpha, other(player))
        board.undo()
        best = max(best, score)
        alpha = max(alpha, score)
        if alpha >= beta:
            break                       # alpha-beta cutoff
    return best
```

That is a working engine in ~15 lines. It will beat a beginner immediately at depth 4–6.

### 11.4 Why this variant is friendly to search

- **Forced max-capture collapses the branching factor.** In tactical positions the legal move list is often 1–3 moves. Alpha-beta loves that.
- **No legal move = loss, not draw.** Terminal detection is trivial and there are no repetition draws to worry about.
- **Death squares are visible in the move list** (`dies=True`), so the evaluation can see "this move kills my own piece" without extra work.
- **`Board.copy()` is cheap** because `Piece` is frozen.

### 11.5 What to add after the first version works

In order of payoff-per-hour:

1. **Iterative deepening** — search depth 1, 2, 3… keeping the best move from the previous depth to order moves first. Typically 2–3× fewer nodes.
2. **Move ordering** — try captures first (they are forced anyway), then moves that promote, then the rest. Alpha-beta is dramatically better with good ordering.
3. **Transposition table** — a dict keyed by a Zobrist hash of `(squares, turn, poisoned)`. The same position arises constantly. Watch out: the variant's undo stack means two paths to the same position are genuinely equivalent, so caching is sound.
4. **Time management** — search until a time budget expires rather than a fixed depth.
5. **Aspiration windows / killer moves** — advanced, only if you enjoy it.

### 11.6 Where it plugs into the API

The clean seam is a **bot player** implemented as a repository call or a background task:

- Add `engine/ai/search.py` with `best_move(board, depth) -> Move`.
- Add a `POST /games/{id}/bot-move` endpoint (or a flag on game creation) that calls `best_move` and then `repo.play(...)` exactly like a human move.
- Because the store already bumps `version` and notifies the broadcaster, the human's SSE stream updates automatically. **The frontend needs no changes at all** — a bot move is indistinguishable from a human move on the wire.

That last point is worth internalising: the engine/API seam is clean enough that adding an AI is **additive, not invasive**. If it were not, that would be a design smell worth fixing.

### 11.7 Timing reality check

A naive Python negamax at depth 6 on this game is roughly 10⁴–10⁵ nodes, which is well under a second. Depth 10 with alpha-beta and a transposition table is a few seconds. If you want faster, the options are, in order: better move ordering, then PyPy, then a compiled extension, then multiprocessing. **Do not reach for parallelism before you have measured** — most "slow search" is bad move ordering, not lack of cores.

---

## 12. File map and what to read in what order

To actually understand the engine, read in this order (each file only depends on earlier ones):

| # | File | Time | What it gives you |
|---|---|---|---|
| 1 | `engine/constants.py` | 2 min | enums, who moves first |
| 2 | `engine/geometry.py` | 5 min | squares, diagonals, death squares |
| 3 | `engine/notation.py` | 3 min | the `Move` object |
| 4 | `engine/board.py` | 10 min | state, apply/undo, death + poison |
| 5 | `engine/moves.py` | 15 min | quiet moves + the capture DFS |
| 6 | `engine/legality.py` | 5 min | freezing, `legal_moves`, `check_legal` |
| 7 | `engine/rules.py` | 2 min | `winner` / draw |

That is under an hour to read the whole thing, and after step 6 you can predict what every function does from its name.

**Tests worth reading alongside:** `tests/test_rules.py` (the variant rules), `tests/test_fuzz.py` (invariants over random games — it is what gives confidence that undo/apply are inverse).
