"""In-process fan-out of game changes to open event streams.

Sync route handlers run in Starlette's threadpool, so waiters are plain
:class:`threading.Condition` objects. This is the single-worker implementation;
a multi-worker deployment needs the same contract over Redis pub/sub.
"""

from __future__ import annotations

import threading


class Broadcaster:
    """Wake every stream watching a game when that game changes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._waiters: dict[str, list[threading.Condition]] = {}
        self._versions: dict[str, int] = {}

    def versions(self, game_id: str) -> int:
        """Last version published for ``game_id`` (0 when unknown)."""
        with self._lock:
            return self._versions.get(game_id, 0)

    def publish(self, game_id: str, version: int) -> None:
        """Record ``version`` and wake the streams watching ``game_id``."""
        with self._lock:
            self._versions[game_id] = version
            waiters = list(self._waiters.get(game_id, ()))
        for cond in waiters:
            with cond:
                cond.notify_all()

    def subscribe(self, game_id: str) -> threading.Condition:
        """Register a waiter; pair with :meth:`unsubscribe` in a ``finally``."""
        cond = threading.Condition()
        with self._lock:
            self._waiters.setdefault(game_id, []).append(cond)
        return cond

    def unsubscribe(self, game_id: str, cond: threading.Condition) -> None:
        with self._lock:
            waiters = self._waiters.get(game_id)
            if waiters is None:
                return
            if cond in waiters:
                waiters.remove(cond)
            if not waiters:
                del self._waiters[game_id]
                self._versions.pop(game_id, None)

    def wait(
        self, game_id: str, cond: threading.Condition, seen: int, timeout: float
    ) -> None:
        """Block until ``game_id`` moves past ``seen`` or ``timeout`` elapses.

        Checking the last published version under the condition's lock closes
        the gap between reading the state and starting to wait.
        """
        with cond:
            if self._versions.get(game_id, 0) > seen:
                return
            cond.wait(timeout)
