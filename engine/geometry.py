"""Square indexing and diagonal geometry. Implements spec section 3."""

from engine.constants import BOARD_SIZE, NUM_SQUARES, Player, other

Direction = tuple[int, int]  # (d_file, d_rank)

NE: Direction = (1, 1)
NW: Direction = (-1, 1)
SE: Direction = (1, -1)
SW: Direction = (-1, -1)
DIRECTIONS: tuple[Direction, ...] = (NE, NW, SE, SW)


def file_of(sq: int) -> int:
    """File 0..7 of a square (3.1)."""
    return sq % BOARD_SIZE


def rank_of(sq: int) -> int:
    """Rank 0..7 of a square (3.1)."""
    return sq // BOARD_SIZE


def square(file: int, rank: int) -> int:
    """Square index from file and rank (3.1). Raises ValueError off-board."""
    if not (0 <= file < BOARD_SIZE and 0 <= rank < BOARD_SIZE):
        raise ValueError(f"file/rank off board: {file}, {rank}")
    return rank * BOARD_SIZE + file


def is_valid_square(sq: int) -> bool:
    """True iff sq is an int in 0..63."""
    return isinstance(sq, int) and 0 <= sq < NUM_SQUARES


def is_playable(sq: int) -> bool:
    """True iff sq is a dark square (3.3): file + rank is even."""
    return is_valid_square(sq) and (file_of(sq) + rank_of(sq)) % 2 == 0


def step(sq: int, direction: Direction) -> int | None:
    """Neighbour of sq in direction, or None if off-board (R2.6, 3.4)."""
    f = file_of(sq) + direction[0]
    r = rank_of(sq) + direction[1]
    if 0 <= f < BOARD_SIZE and 0 <= r < BOARD_SIZE:
        return r * BOARD_SIZE + f
    return None


def forward_directions(player: Player) -> tuple[Direction, ...]:
    """Forward directions for a man (3.4): WHITE rank decreasing, BLACK increasing."""
    return (SE, SW) if player is Player.WHITE else (NE, NW)


def promotion_square(player: Player) -> int:
    """a1=0 for WHITE, h8=63 for BLACK (3.5)."""
    return 0 if player is Player.WHITE else 63


_WHITE_HOME: frozenset[int] = frozenset({57, 59, 61, 63})
_BLACK_HOME: frozenset[int] = frozenset({0, 2, 4, 6})


def home_row(player: Player) -> frozenset[int]:
    """The four dark squares on the rank player starts on (3.6)."""
    return _WHITE_HOME if player is Player.WHITE else _BLACK_HOME


def death_squares(player: Player) -> frozenset[int]:
    """Static death squares for player (3.7): opponent home row minus own promotion square."""
    return home_row(other(player)) - {promotion_square(player)}


STATIC_DEATH_SQUARES: frozenset[int] = death_squares(Player.WHITE) | death_squares(
    Player.BLACK
)
