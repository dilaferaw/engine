"""Move dataclass and serialization (spec sections 12, 13, 14)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.geometry import is_valid_square


@dataclass
class Move:
    """A legal-move description: from, to, captured squares in order, and death flag."""

    from_sq: int
    to_sq: int
    captures: list[int] = field(default_factory=list)
    dies: bool = False

    def __post_init__(self) -> None:
        for sq in (self.from_sq, self.to_sq, *self.captures):
            if not is_valid_square(sq):
                raise ValueError(f"square out of range 0..63: {sq!r}")
        if self.from_sq == self.to_sq:
            raise ValueError("from_sq must differ from to_sq")

    @property
    def length(self) -> int:
        """Number of captured pieces (R3.3)."""
        return len(self.captures)

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe dict (13)."""
        return {
            "from_sq": self.from_sq,
            "to_sq": self.to_sq,
            "captures": list(self.captures),
            "dies": self.dies,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Move:
        """Rebuild a Move from to_dict output (13)."""
        return cls(
            from_sq=int(d["from_sq"]),
            to_sq=int(d["to_sq"]),
            captures=[int(c) for c in d["captures"]],
            dies=bool(d["dies"]),
        )
