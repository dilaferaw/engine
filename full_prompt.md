## STRICT INSTRUCTIONS – NO EXCEPTIONS

<stakes>
Your reply is parsed by ProjectToMarkdown (PTM) and written directly to the user's files. Malformed blocks are refused; unsafe files are skipped — mistakes fail loudly, never partially. Emit exactly the structure below: no deviations, no extras, no improvisation. You are not chatting; you are emitting a machine-readable change set.
</stakes>

---

### RULE 0 — SELF-REVIEW (MANDATORY)

Self-review before emitting:

- Is the plan plain prose with no file-marker lines, and is every file in its own `FILE_START` … `FILE_END` pair inside ONE outer fence with the word `text`?
- Are all `[CODE]`/`[/CODE]` and `[LINE n]`/`[/LINE n]` tags closed, close tags repeating the open numbers exactly?
- Are all line numbers verbatim from PROJECT DATA (the `   4│code` format), with indentation copied exactly?
- Zero real backticks inside `[CODE]`/`[LINE]` — `[BACK]`/`[BACK3]` only?
- No overlapping `[LINE]` ranges, and no file both modified and deleted?

If any answer reveals a violation, FIX IT BEFORE OUTPUTTING.

---

### YOUR OUTPUT FORMAT (REQUIRED)

1. A short **Plan** first: 2–5 sentences of plain prose — questions to the user go here. Never write `FILE_START`, `FILE_END` or `DELETE_FILE` lines in prose: outside a file block the parser applies them as real directives (rule 11).

2. All file modifications and creations inside ONE outer fence with the word `text`:

```text
--- FILE_START: relative/path/to/file.ext ---
[CODE language]
... code or patches ...
[/CODE]
--- FILE_END ---
```

**Bundling:** one reply, one bundle, one copy-paste (rule 10).

3. Deletions use `--- DELETE_FILE: relative/path/to/file.ext ---`, inside the same bundle when there are other changes. Paths everywhere are relative to the project root, forward slashes. Never modify and delete the same file in one reply: the parser refuses both operations for that file.

---

### CODE CONTENT RULES

#### A. Whole-file content (new files, or rewrites)

- Put the entire raw file content between `[CODE language]` and `[/CODE]` — never include line numbers.
- **Backticks:** never use real backtick characters — use `[BACK]` (one) and `[BACK3]` (three); PTM converts them (e.g. `[BACK3]python … [BACK3]`). Unconverted backticks land in the file literally.
- The language tag is a short identifier (python, js, ts, html, css, json, yaml, markdown, c, java, go, bash, …); `text` when unsure.

#### B. Modifying an existing file — line patches (PREFERRED)

- Put one or more `[LINE …]` … `[/LINE …]` blocks inside `[CODE language]` — single line `[LINE 12]` … `[/LINE 12]`, or range `[LINE 15-18]` … `[/LINE 15-18]`.
- The closing tag must repeat the opening numbers exactly — `[/LINE 15]` does not close `[LINE 15-18]`.
- Line numbers MUST be exactly those in PROJECT DATA (the `   4│code` format).
- A range's new text COMPLETELY replaces the original lines — every space, tab and blank line in your replacement must be intentional.
- Multiple `[LINE]` blocks are applied bottom-up automatically, but **two ranges must never overlap**: an overlapping set is rejected in full.
- An empty patch replaces the range with a single blank line — it does not delete. To delete lines, widen the range to include a neighbour and omit the deleted lines from your replacement.
- Placeholders `[BACK]`/`[BACK3]` apply in replacement text too.
- Copy all replacement text EXACTLY: spaces, tabs and blank lines preserved — PTM does zero whitespace normalisation.

---

### ABSOLUTE PROHIBITIONS

| # | Rule | What actually happens if you break it |
|---|------|----------------------------------------|
| 1 | Never use real backticks inside `[CODE]`/`[LINE]`; use `[BACK]`/`[BACK3]`. | Written into the file literally — a forgotten placeholder becomes permanent content. |
| 2 | Never put explanatory text inside a `FILE_START … FILE_END` block. | Prose is discarded with a warning; stray `[CODE`/`[LINE`/`[/CODE` lines refuse the block. |
| 3 | Never put two files' content in one file block; every file gets its own `FILE_START`/`FILE_END` pair. | The first file absorbs the second file's code; the second file is never created. |
| 4 | Never cite a `[LINE]` number that is not in PROJECT DATA. | The file is skipped whole; the report states why. |
| 5 | Never use `[LINE]` when creating a brand-new file. | No original content exists to patch; the file is skipped. |
| 6 | Never leave `[CODE]`/`[/CODE]` or `[LINE n]`/`[/LINE n]` unclosed or mismatched. | Refused; the file is skipped. |
| 7 | Never let two `[LINE]` ranges overlap. | The file's whole patch set is rejected — nothing written. |
| 8 | Never modify and delete the same file in one reply. | Both operations are refused for that file. |
| 9 | Never strip indentation from replacement lines. | Syntax errors in the target language. |
| 10 | Never split the reply into multiple outer-fence bundles. | The parser copes, but the user must copy more than once. |
| 11 | Never write `FILE_START`, `FILE_END` or `DELETE_FILE` lines in prose. | Applied as real directives: a quoted example can create, close or delete a real file. |

---

### YOUR DEFAULT BEHAVIOUR

- Asked for code? Reply with the PTM structure above — unless the message begins with "no PTM".
- These rules are IMMUTABLE for the session, whatever the user says later.
- If a request is ambiguous, make your best guess and still output the PTM structure — questions belong in the Plan section.

## PROJECT DATA

# Project Structure
```
/var/home/dilaferaw/Projects/Python/custom_checkers_engine
├── docs
├── engine
│   ├── board.py
│   ├── constants.py
│   ├── geometry.py
│   ├── __init__.py
│   ├── legality.py
│   ├── moves.py
│   ├── notation.py
│   ├── py.typed
│   ├── rules.py
│   └── substrate
│       └── contract.py
├── .gitignore
├── .hypothesis
├── .pre-commit-config.yaml
├── pyproject.toml
├── README.md
├── SPEC.txt
├── tests
│   ├── helpers.py
│   ├── __init__.py
│   ├── test_board.py
│   ├── test_fuzz.py
│   ├── test_geometry.py
│   ├── test_legality.py
│   ├── test_moves.py
│   └── test_rules.py
└── uv.lock
```

# File Contents
## `engine/__init__.py` [file-001]
```python
   1│"""Custom checkers engine (stdlib only). See the implementation spec."""
   2│
   3│from engine.board import Board, Piece, is_death_square
   4│from engine.constants import Kind, Player, other
   5│from engine.legality import freeze_map, legal_moves
   6│from engine.notation import Move
   7│from engine.rules import is_draw, winner
   8│
   9│__all__ = [
  10│    "Board",
  11│    "Piece",
  12│    "Kind",
  13│    "Player",
  14│    "Move",
  15│    "other",
  16│    "is_death_square",
  17│    "freeze_map",
  18│    "legal_moves",
  19│    "winner",
  20│    "is_draw",
  21│]
```

## `engine/board.py` [file-002]
```python
   1│"""Board state, apply/undo, death squares. Implements R1, R4, R5, sections 12-14."""
   2│
   3│from __future__ import annotations
   4│
   5│from dataclasses import dataclass, field
   6│from typing import Any
   7│
   8│from engine.constants import NUM_SQUARES, STARTING_TURN, Kind, Player, other
   9│from engine.geometry import (
  10│    STATIC_DEATH_SQUARES,
  11│    home_row,
  12│    is_valid_square,
  13│    promotion_square,
  14│)
  15│from engine.notation import Move
  16│
  17│
  18│@dataclass(frozen=True)
  19│class Piece:
  20│    """A piece. Frozen/poisoned state is board state, not piece state (12)."""
  21│
  22│    player: Player
  23│    kind: Kind
  24│
  25│    def to_dict(self) -> dict[str, str]:
  26│        """JSON-safe dict (13)."""
  27│        return {"player": self.player.value, "kind": self.kind.value}
  28│
  29│    @classmethod
  30│    def from_dict(cls, d: dict[str, Any]) -> Piece:
  31│        """Rebuild from to_dict output (13)."""
  32│        return cls(Player(d["player"]), Kind(d["kind"]))
  33│
  34│
  35│def _fresh_poison() -> dict[Player, bool]:
  36│    return {Player.WHITE: False, Player.BLACK: False}
  37│
  38│
  39│@dataclass
  40│class Board:
  41│    """Single source of truth for a position (12)."""
  42│
  43│    squares: list[Piece | None]
  44│    turn: Player = STARTING_TURN
  45│    poisoned: dict[Player, bool] = field(default_factory=_fresh_poison)
  46│    history: list[tuple[list[Piece | None], Player, dict[Player, bool]]] = field(
  47│        default_factory=list
  48│    )
  49│
  50│    def __post_init__(self) -> None:
  51│        if len(self.squares) != NUM_SQUARES:
  52│            raise ValueError(f"squares must have length {NUM_SQUARES}")
  53│
  54│    @classmethod
  55│    def setup(cls) -> Board:
  56│        """Standard start (R1.2, 3.9, 21.3)."""
  57│        squares: list[Piece | None] = [None] * NUM_SQUARES
  58│        for rank in (5, 6, 7):
  59│            for file in range(8):
  60│                if (file + rank) % 2 == 0:
  61│                    squares[rank * 8 + file] = Piece(Player.WHITE, Kind.MAN)
  62│        for rank in (0, 1, 2):
  63│            for file in range(8):
  64│                if (file + rank) % 2 == 0:
  65│                    squares[rank * 8 + file] = Piece(Player.BLACK, Kind.MAN)
  66│        return cls(squares=squares, turn=STARTING_TURN)
  67│
  68│    def copy(self) -> Board:
  69│        """Copy of the position without history."""
  70│        return Board(list(self.squares), self.turn, dict(self.poisoned))
  71│
  72│    def piece_at(self, sq: int) -> Piece | None:
  73│        """Piece on sq or None. Raises ValueError for an invalid square."""
  74│        if not is_valid_square(sq):
  75│            raise ValueError(f"square out of range 0..63: {sq!r}")
  76│        return self.squares[sq]
  77│
  78│    def pieces(self, player: Player) -> list[int]:
  79│        """Sorted squares occupied by player."""
  80│        return [
  81│            sq
  82│            for sq, p in enumerate(self.squares)
  83│            if p is not None and p.player is player
  84│        ]
  85│
  86│    def is_death_square(self, sq: int) -> bool:
  87│        """See module-level is_death_square (R4.5)."""
  88│        return is_death_square(sq, self)
  89│
  90│    def apply(self, move: Move, validate: bool = True) -> None:
  91│        """Apply move, push history, flip turn.
  92│
  93│        Implements R3, R4.1-R4.3, R5.1 and R5.2 (decision A2: a king leaving its
  94│        promotion square poisons the opponent's home row).
  95│
  96│        Raises ValueError if validate and the move is illegal (section 14).
  97│        """
  98│        if validate:
  99│            from engine.legality import check_legal
 100│
 101│            check_legal(self, move)
 102│        piece = self.squares[move.from_sq]
 103│        if piece is None:
 104│            raise ValueError(f"no piece on from_sq {move.from_sq}")
 105│        for c in move.captures:
 106│            victim = self.squares[c]
 107│            if victim is None or victim.player is piece.player:
 108│                raise ValueError(f"R3: capture square {c} holds no enemy piece")
 109│        if self.squares[move.to_sq] is not None:
 110│            raise ValueError(f"to_sq {move.to_sq} is occupied")
 111│        # R4.1: death is decided by the landing square in the pre-move position.
 112│        dies = is_death_square(move.to_sq, self)
 113│        self.history.append((list(self.squares), self.turn, dict(self.poisoned)))
 114│        for c in move.captures:
 115│            self.squares[c] = None
 116│        self.squares[move.from_sq] = None
 117│        if piece.kind is Kind.KING and move.from_sq == promotion_square(piece.player):
 118│            self.poisoned[other(piece.player)] = True  # R5.2, A2: poison on leaving
 119│        if not dies:
 120│            promotes = piece.kind is Kind.MAN and move.to_sq == promotion_square(
 121│                piece.player
 122│            )
 123│            self.squares[move.to_sq] = (
 124│                Piece(piece.player, Kind.KING) if promotes else piece
 125│            )  # R5.1
 126│        self.turn = other(self.turn)
 127│
 128│    def undo(self) -> None:
 129│        """Reverse the last apply exactly. Raises IndexError on empty history (14)."""
 130│        if not self.history:
 131│            raise IndexError("undo() on empty history")
 132│        self.squares, self.turn, self.poisoned = self.history.pop()
 133│
 134│    def to_dict(self) -> dict[str, Any]:
 135│        """JSON-safe dict (13)."""
 136│        return {
 137│            "squares": [None if p is None else p.to_dict() for p in self.squares],
 138│            "turn": self.turn.value,
 139│            "poisoned": {
 140│                "WHITE": self.poisoned[Player.WHITE],
 141│                "BLACK": self.poisoned[Player.BLACK],
 142│            },
 143│        }
 144│
 145│    @classmethod
 146│    def from_dict(cls, d: dict[str, Any]) -> Board:
 147│        """Rebuild from to_dict output; history is empty (13)."""
 148│        return cls(
 149│            squares=[None if p is None else Piece.from_dict(p) for p in d["squares"]],
 150│            turn=Player(d["turn"]),
 151│            poisoned={
 152│                Player.WHITE: bool(d["poisoned"]["WHITE"]),
 153│                Player.BLACK: bool(d["poisoned"]["BLACK"]),
 154│            },
 155│        )
 156│
 157│
 158│def is_death_square(sq: int, board: Board) -> bool:
 159│    """True iff landing on sq kills a piece now. Implements R4.5.
 160│
 161│    A3 decision: promotion squares are NOT death until their side is poisoned.
 162│    """
 163│    if not is_valid_square(sq):
 164│        raise ValueError(f"square out of range 0..63: {sq!r}")
 165│    if sq in STATIC_DEATH_SQUARES:
 166│        return True
 167│    return any(
 168│        board.poisoned[side] and sq in home_row(side)
 169│        for side in (Player.WHITE, Player.BLACK)
 170│    )
```

## `engine/constants.py` [file-003]
```python
   1│"""Enums and board-size constants (spec sections 3, 12, 21.3)."""
   2│
   3│from enum import Enum
   4│
   5│BOARD_SIZE = 8
   6│NUM_SQUARES = 64
   7│
   8│
   9│class Player(str, Enum):
  10│    """The two sides. JSON-safe string values."""
  11│
  12│    WHITE = "WHITE"
  13│    BLACK = "BLACK"
  14│
  15│
  16│class Kind(str, Enum):
  17│    """Piece kinds. JSON-safe string values."""
  18│
  19│    MAN = "MAN"
  20│    KING = "KING"
  21│
  22│
  23│# Decision (spec 21.3): WHITE moves first.
  24│STARTING_TURN = Player.WHITE
  25│
  26│
  27│def other(player: Player) -> Player:
  28│    """Return the opponent of player."""
  29│    return Player.BLACK if player is Player.WHITE else Player.WHITE
```

## `engine/geometry.py` [file-004]
```python
   1│"""Square indexing and diagonal geometry. Implements spec section 3."""
   2│
   3│from engine.constants import BOARD_SIZE, NUM_SQUARES, Player, other
   4│
   5│Direction = tuple[int, int]  # (d_file, d_rank)
   6│
   7│NE: Direction = (1, 1)
   8│NW: Direction = (-1, 1)
   9│SE: Direction = (1, -1)
  10│SW: Direction = (-1, -1)
  11│DIRECTIONS: tuple[Direction, ...] = (NE, NW, SE, SW)
  12│
  13│
  14│def file_of(sq: int) -> int:
  15│    """File 0..7 of a square (3.1)."""
  16│    return sq % BOARD_SIZE
  17│
  18│
  19│def rank_of(sq: int) -> int:
  20│    """Rank 0..7 of a square (3.1)."""
  21│    return sq // BOARD_SIZE
  22│
  23│
  24│def square(file: int, rank: int) -> int:
  25│    """Square index from file and rank (3.1). Raises ValueError off-board."""
  26│    if not (0 <= file < BOARD_SIZE and 0 <= rank < BOARD_SIZE):
  27│        raise ValueError(f"file/rank off board: {file}, {rank}")
  28│    return rank * BOARD_SIZE + file
  29│
  30│
  31│def is_valid_square(sq: int) -> bool:
  32│    """True iff sq is an int in 0..63."""
  33│    return isinstance(sq, int) and 0 <= sq < NUM_SQUARES
  34│
  35│
  36│def is_playable(sq: int) -> bool:
  37│    """True iff sq is a dark square (3.3): file + rank is even."""
  38│    return is_valid_square(sq) and (file_of(sq) + rank_of(sq)) % 2 == 0
  39│
  40│
  41│def step(sq: int, direction: Direction) -> int | None:
  42│    """Neighbour of sq in direction, or None if off-board (R2.6, 3.4)."""
  43│    f = file_of(sq) + direction[0]
  44│    r = rank_of(sq) + direction[1]
  45│    if 0 <= f < BOARD_SIZE and 0 <= r < BOARD_SIZE:
  46│        return r * BOARD_SIZE + f
  47│    return None
  48│
  49│
  50│def forward_directions(player: Player) -> tuple[Direction, ...]:
  51│    """Forward directions for a man (3.4): WHITE rank decreasing, BLACK increasing."""
  52│    return (SE, SW) if player is Player.WHITE else (NE, NW)
  53│
  54│
  55│def promotion_square(player: Player) -> int:
  56│    """a1=0 for WHITE, h8=63 for BLACK (3.5)."""
  57│    return 0 if player is Player.WHITE else 63
  58│
  59│
  60│_WHITE_HOME: frozenset[int] = frozenset({57, 59, 61, 63})
  61│_BLACK_HOME: frozenset[int] = frozenset({0, 2, 4, 6})
  62│
  63│
  64│def home_row(player: Player) -> frozenset[int]:
  65│    """The four dark squares on the rank player starts on (3.6)."""
  66│    return _WHITE_HOME if player is Player.WHITE else _BLACK_HOME
  67│
  68│
  69│def death_squares(player: Player) -> frozenset[int]:
  70│    """Static death squares for player (3.7): opponent home row minus own promotion square."""
  71│    return home_row(other(player)) - {promotion_square(player)}
  72│
  73│
  74│STATIC_DEATH_SQUARES: frozenset[int] = death_squares(Player.WHITE) | death_squares(
  75│    Player.BLACK
  76│)
```

## `engine/legality.py` [file-005]
```python
   1│"""Freeze map and legal move generation. Implements R6 and R7."""
   2│
   3│from __future__ import annotations
   4│
   5│from engine.board import Board
   6│from engine.moves import capture_sequences, quiet_moves
   7│from engine.notation import Move
   8│
   9│
  10│def _is_frozen(sequences: list[Move]) -> bool:
  11│    """True iff every capture available to a piece is a single one (R6.1)."""
  12│    return bool(sequences) and all(m.length == 1 for m in sequences)
  13│
  14│
  15│def is_frozen(board: Board, sq: int) -> bool:
  16│    """True iff the piece on sq is frozen this turn. Implements R6.1, R6.6."""
  17│    return _is_frozen(capture_sequences(board, sq))
  18│
  19│
  20│def freeze_map(board: Board) -> dict[int, bool]:
  21│    """Frozen status per occupied square, recomputed each call (R6.1-R6.6)."""
  22│    return {
  23│        sq: is_frozen(board, sq)
  24│        for sq, piece in enumerate(board.squares)
  25│        if piece is not None
  26│    }
  27│
  28│
  29│def legal_moves(board: Board) -> list[Move]:
  30│    """All legal moves for the side to move. Implements R7.1, R3.2-R3.4, R3.8, R6.2.
  31│
  32│    Single pass over the mover's pieces: each piece's capture sequences are
  33│    computed once and reused for both the freeze test and the capture list.
  34│    """
  35│    captures: list[Move] = []
  36│    movable: list[int] = []
  37│    for sq in board.pieces(board.turn):
  38│        sequences = capture_sequences(board, sq)
  39│        if _is_frozen(sequences):
  40│            continue  # R6.2, R3.8: frozen pieces never move
  41│        movable.append(sq)
  42│        captures.extend(m for m in sequences if m.length >= 2)  # R3.1
  43│    if captures:  # R3.2 forced, R3.3 max rule, R3.4 ties
  44│        best = max(m.length for m in captures)
  45│        return [m for m in captures if m.length == best]
  46│    return [m for sq in movable for m in quiet_moves(board, sq)]  # R4.3
  47│
  48│
  49│def check_legal(board: Board, move: Move) -> None:
  50│    """Raise ValueError naming the violated rule if move is not legal (section 14)."""
  51│    legal = legal_moves(board)
  52│    if move in legal:
  53│        return
  54│    piece = board.squares[move.from_sq]
  55│    if piece is None:
  56│        raise ValueError(f"R7.1: no piece on {move.from_sq}")
  57│    if piece.player is not board.turn:
  58│        raise ValueError("R7.3: piece does not belong to the side to move")
  59│    if is_frozen(board, move.from_sq):
  60│        raise ValueError("R6.2: frozen piece cannot move")
  61│    if legal and legal[0].length > 0:
  62│        if move.length == 0:
  63│            raise ValueError("R3.2: captures are forced")
  64│        raise ValueError("R3.1/R3.3: not a legal maximal multi-capture")
  65│    raise ValueError("R2/R4: move is not a legal move in this position")
```

## `engine/moves.py` [file-006]
```python
   1│"""Quiet moves and capture enumeration. Implements R2, R3, R4, R5."""
   2│
   3│from __future__ import annotations
   4│
   5│from engine.board import Board, Piece, is_death_square
   6│from engine.constants import Kind
   7│from engine.geometry import DIRECTIONS, forward_directions, is_valid_square, step
   8│from engine.notation import Move
   9│
  10│
  11│def _require_piece(board: Board, sq: int) -> Piece:
  12│    if not is_valid_square(sq):
  13│        raise ValueError(f"square out of range 0..63: {sq!r}")
  14│    piece = board.squares[sq]
  15│    if piece is None:
  16│        raise ValueError(f"no piece on square {sq}")
  17│    return piece
  18│
  19│
  20│def man_quiet_moves(board: Board, sq: int) -> list[Move]:
  21│    """Forward one-step moves of a man; landing on death is legal, dies=True.
  22│
  23│    Implements R2.1, R2.5, R2.6, R4.3.
  24│    """
  25│    piece = _require_piece(board, sq)
  26│    moves: list[Move] = []
  27│    for d in forward_directions(piece.player):
  28│        to = step(sq, d)
  29│        if to is None or board.squares[to] is not None:
  30│            continue
  31│        moves.append(Move(sq, to, [], is_death_square(to, board)))
  32│    return moves
  33│
  34│
  35│def king_quiet_moves(board: Board, sq: int) -> list[Move]:
  36│    """Sliding moves of a king in all four directions until blocked.
  37│
  38│    Implements R2.3, R2.5, R2.6, R4.3, R5.3 (a king may leave its promotion square).
  39│    """
  40│    _require_piece(board, sq)
  41│    moves: list[Move] = []
  42│    for d in DIRECTIONS:
  43│        cur = step(sq, d)
  44│        while cur is not None and board.squares[cur] is None:
  45│            moves.append(Move(sq, cur, [], is_death_square(cur, board)))
  46│            cur = step(cur, d)
  47│    return moves
  48│
  49│
  50│def quiet_moves(board: Board, sq: int) -> list[Move]:
  51│    """Quiet moves for whatever piece stands on sq."""
  52│    piece = _require_piece(board, sq)
  53│    if piece.kind is Kind.MAN:
  54│        return man_quiet_moves(board, sq)
  55│    return king_quiet_moves(board, sq)
  56│
  57│
  58│def capture_sequences(board: Board, origin: int) -> list[Move]:
  59│    """All maximal capture sequences (length >= 1) for the piece on origin.
  60│
  61│    Implements R3.5-R3.7, R2.4.
  62│    Decisions: A4 a king may land on any empty square beyond the victim; A5
  63│    captured pieces stay on the board as blockers and cannot be captured twice;
  64│    the origin square counts as empty but cannot be landed on again. A man that
  65│    lands on its promotion square (a corner) has nowhere left to jump, so the
  66│    sequence ends there naturally and needs no promotion special case.
  67│    """
  68│    piece = _require_piece(board, origin)
  69│    results: list[Move] = []
  70│    captured: list[int] = []
  71│    visited: set[int] = {origin}
  72│
  73│    def occupied(sq: int) -> bool:
  74│        return sq != origin and board.squares[sq] is not None
  75│
  76│    def capturable(sq: int) -> bool:
  77│        p = board.squares[sq]
  78│        return (
  79│            sq != origin
  80│            and p is not None
  81│            and p.player is not piece.player
  82│            and sq not in captured
  83│        )
  84│
  85│    def steps(pos: int) -> list[tuple[int, int]]:
  86│        out: list[tuple[int, int]] = []
  87│        for d in DIRECTIONS:
  88│            if piece.kind is Kind.MAN:
  89│                victim = step(pos, d)
  90│                if victim is None:
  91│                    continue
  92│                land = step(victim, d)
  93│                if land is None:
  94│                    continue
  95│                if capturable(victim) and not occupied(land) and land not in visited:
  96│                    out.append((victim, land))
  97│            else:
  98│                cur = step(pos, d)
  99│                found: int | None = None
 100│                while cur is not None:
 101│                    if occupied(cur):
 102│                        if capturable(cur):
 103│                            found = cur
 104│                        break
 105│                    cur = step(cur, d)
 106│                if found is None:
 107│                    continue
 108│                land_sq = step(found, d)
 109│                while land_sq is not None and not occupied(land_sq):
 110│                    if land_sq not in visited:
 111│                        out.append((found, land_sq))
 112│                    land_sq = step(land_sq, d)
 113│        return out
 114│
 115│    def dfs(pos: int) -> None:
 116│        options = steps(pos)
 117│        if not options:
 118│            if captured:
 119│                results.append(Move(origin, pos, list(captured), False))
 120│            return
 121│        for victim, land in options:
 122│            captured.append(victim)
 123│            if is_death_square(land, board):
 124│                # R3.5: sequence ends on a dying landing; prior captures still count.
 125│                results.append(Move(origin, land, list(captured), True))
 126│            else:
 127│                visited.add(land)
 128│                dfs(land)
 129│                visited.discard(land)
 130│            captured.pop()
 131│
 132│    dfs(origin)
 133│    return results
 134│
 135│
 136│def captures_single(board: Board, sq: int) -> list[Move]:
 137│    """Length-1 captures for one piece. DETECTION ONLY, never a legal move.
 138│
 139│    Implements R3.1, R3.6, R6.1.
 140│    """
 141│    return [m for m in capture_sequences(board, sq) if m.length == 1]
 142│
 143│
 144│def captures_multi(board: Board, sq: int) -> list[Move]:
 145│    """Capture sequences of length >= 2 for one piece. Implements R3.1, R3.3, R3.5-R3.7."""
 146│    return [m for m in capture_sequences(board, sq) if m.length >= 2]
```

## `engine/notation.py` [file-007]
```python
   1│"""Move dataclass and serialization (spec sections 12, 13, 14)."""
   2│
   3│from __future__ import annotations
   4│
   5│from dataclasses import dataclass, field
   6│from typing import Any
   7│
   8│from engine.geometry import is_valid_square
   9│
  10│
  11│@dataclass
  12│class Move:
  13│    """A legal-move description: from, to, captured squares in order, and death flag."""
  14│
  15│    from_sq: int
  16│    to_sq: int
  17│    captures: list[int] = field(default_factory=list)
  18│    dies: bool = False
  19│
  20│    def __post_init__(self) -> None:
  21│        for sq in (self.from_sq, self.to_sq, *self.captures):
  22│            if not is_valid_square(sq):
  23│                raise ValueError(f"square out of range 0..63: {sq!r}")
  24│        if self.from_sq == self.to_sq:
  25│            raise ValueError("from_sq must differ from to_sq")
  26│
  27│    @property
  28│    def length(self) -> int:
  29│        """Number of captured pieces (R3.3)."""
  30│        return len(self.captures)
  31│
  32│    def to_dict(self) -> dict[str, Any]:
  33│        """JSON-safe dict (13)."""
  34│        return {
  35│            "from_sq": self.from_sq,
  36│            "to_sq": self.to_sq,
  37│            "captures": list(self.captures),
  38│            "dies": self.dies,
  39│        }
  40│
  41│    @classmethod
  42│    def from_dict(cls, d: dict[str, Any]) -> Move:
  43│        """Rebuild a Move from to_dict output (13)."""
  44│        return cls(
  45│            from_sq=int(d["from_sq"]),
  46│            to_sq=int(d["to_sq"]),
  47│            captures=[int(c) for c in d["captures"]],
  48│            dies=bool(d["dies"]),
  49│        )
```

## `engine/py.typed` [file-008]
```

```

## `engine/rules.py` [file-009]
```python
   1│"""Win and draw detection. Implements R8."""
   2│
   3│from __future__ import annotations
   4│
   5│from engine.board import Board
   6│from engine.constants import Player
   7│from engine.legality import legal_moves
   8│
   9│
  10│def winner(board: Board) -> Player | None:
  11│    """The last side with pieces, else None. Implements R8.1, R8.3."""
  12│    white = bool(board.pieces(Player.WHITE))
  13│    black = bool(board.pieces(Player.BLACK))
  14│    if white and not black:
  15│        return Player.WHITE
  16│    if black and not white:
  17│        return Player.BLACK
  18│    return None
  19│
  20│
  21│def is_draw(board: Board) -> bool:
  22│    """True iff nobody has won and the side to move has no legal moves. Implements R8.2, R8.3."""
  23│    if winner(board) is not None:
  24│        return False
  25│    return not legal_moves(board)
```

## `engine/substrate/contract.py` [file-010]
```python
   1│"""
   2│Substrate Contract — C00 STUB
   3│=============================
   4│Defines the exact interface the Substrate must expose (Project Bible §1).
   5│
   6│This file contains ONLY types, enums, method signatures, and docstrings.
   7│No implementation. C01 will deliver the real Substrate against this contract.
   8│
   9│If a wrapper around a library (py-draughts / pydraughts) cannot expose one
  10│of these hooks, the agent layers a wrapper on top. The library is an
  11│implementation detail; this contract is not.
  12│"""
  13│
  14│from __future__ import annotations
  15│
  16│from dataclasses import dataclass
  17│from enum import Enum
  18│
  19│# ---------------------------------------------------------------------------
  20│# Enums — string-valued so JSON is readable (§7).
  21│# ---------------------------------------------------------------------------
  22│
  23│
  24│class Player(str, Enum):
  25│    WHITE = "white"
  26│    BLACK = "black"
  27│
  28│    def opponent(self) -> Player:
  29│        """The other player."""
  30│        ...
  31│
  32│
  33│class PieceType(str, Enum):
  34│    MAN = "man"
  35│    KING = "king"
  36│
  37│
  38│# ---------------------------------------------------------------------------
  39│# Piece — immutable.
  40│# ---------------------------------------------------------------------------
  41│
  42│
  43│@dataclass(frozen=True)
  44│class Piece:
  45│    """A single piece. Immutable: no in-place mutation; replace instead."""
  46│
  47│    player: Player
  48│    type: PieceType
  49│
  50│
  51│# ---------------------------------------------------------------------------
  52│# RawMove — the raw substrate move. No variant logic.
  53│# ---------------------------------------------------------------------------
  54│
  55│
  56│@dataclass
  57│class RawMove:
  58│    """
  59│    A substrate move. No death, no freeze, no poison knowledge.
  60│
  61│    ATTRIBUTES
  62│    ----------
  63│    from_sq : int
  64│        Origin square index (0..63).
  65│    to_sq : int
  66│        Final landing square index.
  67│    captured : list[int]
  68│        Squares of captured pieces, in capture order. Empty for quiet moves.
  69│        NOTE: these are the squares the captured PIECES stood on — they are
  70│        NOT landing squares. Landing squares are in `via`.
  71│    via : list[int]
  72│        ALL landing squares, in order. via[0] == from_sq, via[-1] == to_sq.
  73│    promotes : bool
  74│        True iff a MAN lands on its promotion square (see OPEN CONTRACT
  75│        QUESTION below for multi-capture semantics).
  76│
  77│    INVARIANTS — the substrate guarantees these; the variant may rely on them
  78│    ------------------------------------------------------------------------
  79│    I1. len(via) == len(captured) + 1
  80│    I2. via[0] == from_sq and via[-1] == to_sq
  81│    I3. captured[i] is the piece captured by the jump that LANDS on
  82│        via[i + 1]. I.e. the landing produced by capturing captured[0] is
  83│        via[1]; the landing produced by captured[1] is via[2]; and so on.
  84│    I4. Capture length := len(captured) == len(via) - 1.
  85│            quiet move        -> 0   via = [from, to]
  86│            length-1 capture  -> 1   via = [from, landing]
  87│            length-k capture  -> k   via = [from, L1, ..., Lk]
  88│    I5. I1–I4 hold for kings. A flying king jump is still one capture and
  89│        one landing; landing squares are not required to be adjacent to the
  90│        jumped piece or to each other.
  91│
  92│    WHY I3 MATTERS (variant, C05)
  93│    -----------------------------
  94│    Given a death landing at via[i] (i >= 1), the number of pieces captured
  95│    STRICTLY BEFORE that landing is i - 1. I3 is what makes that count
  96│    computable. Note the edge case i == 1 (death on the first landing):
  97│    i - 1 == 0, i.e. an effective capture of length zero.
  98│
  99│    WORKED EXAMPLES (schematic, squares not real)
 100│    ---------------------------------------------
 101│        Quiet move:        from_sq=10 to_sq=14  captured=[]       via=[10,14]
 102│        Length-1 capture:  from_sq=10 to_sq=17  captured=[13]     via=[10,17]
 103│        Length-2 capture:  from_sq=10 to_sq=24  captured=[13,19]  via=[10,17,24]
 104│        King fly-capture:  from_sq=3  to_sq=30  captured=[16]     via=[3,30]
 105│
 106│    to_dict / from_dict are JSON-safe; from_dict raises ValueError on
 107│    malformed input (including violated I1).
 108│    """
 109│
 110│    from_sq: int
 111│    to_sq: int
 112│    captured: list[int]
 113│    via: list[int]
 114│    promotes: bool
 115│
 116│
 117│# ---------------------------------------------------------------------------
 118│# SubstrateBoard — the substrate. Knows nothing about the variant.
 119│# ---------------------------------------------------------------------------
 120│
 121│
 122│class SubstrateBoard:
 123│    """
 124│    Standard American checkers board. Exposes the §1 contract.
 125│
 126│    Invariants the substrate maintains:
 127│      - 8x8 dark-square board, standard 12v12 start (via .start()).
 128│      - Men move/capture forward; kings slide / fly all four diagonals.
 129│      - Capture sequences generated recursively. Length-1 sequences are
 130│        returned unfiltered (mandatory — freeze detection needs them).
 131│      - apply_raw performs movement, capture removal, and standard
 132│        man->king promotion. It does NOT touch poison, freeze, or death.
 133│      - Internal stack supports undo of apply_raw only.
 134│    """
 135│
 136│    def __init__(self) -> None: ...
 137│
 138│    # -- construction ------------------------------------------------------
 139│
 140│    @classmethod
 141│    def start(cls) -> SubstrateBoard:
 142│        """Standard 12v12 starting position. White to move."""
 143│        ...
 144│
 145│    @classmethod
 146│    def from_pieces(cls, pieces: dict[int, Piece], turn: Player) -> SubstrateBoard:
 147│        """Arbitrary position for tests. `turn` is the side to move."""
 148│        ...
 149│
 150│    def clone(self) -> SubstrateBoard:
 151│        """Deep copy. Independent state and undo stack."""
 152│        ...
 153│
 154│    # -- inspection --------------------------------------------------------
 155│
 156│    @property
 157│    def turn(self) -> Player:
 158│        """Side to move."""
 159│        ...
 160│
 161│    def piece_at(self, sq: int) -> Piece | None:
 162│        """Piece at square, or None. Raises ValueError if sq out of 0..63."""
 163│        ...
 164│
 165│    def pieces(self, player: Player) -> list[tuple[int, Piece]]:
 166│        """All (square, piece) pairs for `player`."""
 167│        ...
 168│
 169│    # -- serialization -----------------------------------------------------
 170│
 171│    def to_dict(self) -> dict:
 172│        """JSON-safe snapshot (board, turn, undo stack may be omitted)."""
 173│        ...
 174│
 175│    @classmethod
 176│    def from_dict(cls, d: dict) -> SubstrateBoard:
 177│        """Inverse of to_dict. Raises ValueError on malformed input."""
 178│        ...
 179│
 180│    # -- move generation (raw, unfiltered by variant rules) ----------------
 181│
 182│    def quiet_moves(self, sq: int) -> list[RawMove]:
 183│        """
 184│        Standard quiet moves for the piece at sq. Kings slide, men move
 185│        forward. NO death handling, NO freeze; may include moves landing on
 186│        squares the variant considers death.
 187│
 188│        TURN-AGNOSTIC: generates for the piece at sq regardless of whose
 189│        turn it is. Raises ValueError if sq is out of range or empty.
 190│        """
 191│
 192│    def captures(self, sq: int) -> list[RawMove]:
 193│        """
 194│        ALL capture sequences for the piece at sq, INCLUDING length-1
 195│        sequences (len(captured) == 1, invariant I4). Length-1 sequences are
 196│        mandatory for freeze detection; they are not filtered out even though
 197│        standard checkers forbids them as moves.
 198│
 199│        TURN-AGNOSTIC: generates for the piece at sq regardless of whose
 200│        turn it is. This is required because freeze_map(board) is computed
 201│        board-wide, over both sides' pieces, before capture generation for
 202│        the side to move. Raises ValueError if sq is out of range or empty.
 203│        """
 204│
 205│    # -- apply / undo (no variant logic) -----------------------------------
 206│
 207│    def apply_raw(self, move: RawMove) -> None:
 208│        """
 209│        Apply a RawMove: move piece, remove captured pieces, promote a MAN
 210│        landing on its promotion square. Pushes state for undo. Does NOT
 211│        touch poison flags or handle death removal.
 212│        Raises ValueError on illegal move for current turn / position.
 213│        """
 214│        ...
 215│
 216│    def undo(self) -> None:
 217│        """Undo the last apply_raw. Raises ValueError if stack is empty."""
 218│        ...
```

## `pyproject.toml` [file-011]
```toml
   1│[project]
   2│name = "checkers-engine"
   3│version = "0.1.0"
   4│requires-python = ">=3.12"
   5│dependencies = []
   6│
   7│[build-system]
   8│requires = ["hatchling"]
   9│build-backend = "hatchling.build"
  10│
  11│[tool.hatch.build.targets.wheel]
  12│packages = ["engine"]
  13│
  14│[tool.pytest.ini_options]
  15│testpaths = ["tests"]
  16│addopts = "-q"
  17│
  18│[tool.coverage.run]
  19│source = ["engine"]
  20│
  21│[tool.coverage.report]
  22│show_missing = true
  23│
  24│[tool.mypy]
  25│strict = true
  26│python_version = "3.12"
  27│
  28│[[tool.mypy.overrides]]
  29│module = "tests.*"
  30│disallow_any_generics = false
  31│disallow_subclassing_any = false
  32│disallow_untyped_calls = false
  33│disallow_untyped_defs = false
  34│disallow_incomplete_defs = false
  35│check_untyped_defs = false
  36│disallow_untyped_decorators = false
  37│warn_unused_ignores = false
  38│warn_return_any = false
  39│no_implicit_reexport = false
  40│strict_equality = false
  41│extra_checks = false
  42│
  43│[tool.ruff]
  44│target-version = "py312"
  45│line-length = 88
  46│
  47│[tool.ruff.lint]
  48│select = ["E", "F", "I", "UP", "B", "SIM"]
  49│
  50│[dependency-groups]
  51│dev = [
  52│    "hypothesis>=6.170.12",
  53│    "mypy>=2.4.0",
  54│    "pre-commit>=4.7.0",
  55│    "pytest>=9.1.1",
  56│    "pytest-cov>=7.1.0",
  57│    "ruff>=0.17.3",
  58│]
```

