"""Storage-layer exceptions. HTTP status mapping lives in the API layer."""


class StorageError(Exception):
    """Base class for recoverable storage failures."""


class GameNotFound(StorageError, KeyError):
    """No game exists under the requested id."""


class GameFull(StorageError):
    """Both seats are taken."""


class NotASeat(StorageError):
    """The caller does not hold a seat in this game."""


class NotYourTurn(StorageError):
    """The caller tried to move for the other side."""
