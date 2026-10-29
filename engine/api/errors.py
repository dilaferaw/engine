"""Translate storage and engine exceptions into HTTP errors."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException, status

from engine.storage import GameFull, GameNotFound, NotASeat, NotYourTurn

STATUS_FOR: dict[type[Exception], int] = {
    GameNotFound: status.HTTP_404_NOT_FOUND,
    GameFull: status.HTTP_409_CONFLICT,
    NotASeat: status.HTTP_403_FORBIDDEN,
    NotYourTurn: status.HTTP_403_FORBIDDEN,
    IndexError: status.HTTP_409_CONFLICT,
    KeyError: status.HTTP_400_BAD_REQUEST,
    TypeError: status.HTTP_400_BAD_REQUEST,
    ValueError: status.HTTP_400_BAD_REQUEST,
}


def _detail(exc: Exception) -> str:
    if isinstance(exc, GameNotFound):
        return "unknown game"
    return str(exc) or exc.__class__.__name__


@contextmanager
def translate() -> Iterator[None]:
    """Map storage and engine exceptions onto ``HTTPException``."""
    try:
        yield
    except HTTPException:
        raise
    except Exception as exc:
        code = next(
            (s for kind, s in STATUS_FOR.items() if isinstance(exc, kind)), None
        )
        if code is None:
            raise
        raise HTTPException(status_code=code, detail=_detail(exc)) from exc
