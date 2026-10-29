"""HTTP interface over the checkers engine.

Run with ``uvicorn engine.api:app``. The app is assembled in ``app.py``;
routes live in ``routes.py``, wire models in ``schemas.py``, request
headers in ``deps.py`` and error translation in ``errors.py``.
"""

from engine.api.application import create_app

app = create_app()

__all__ = ["app", "create_app"]
