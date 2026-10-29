"""Entry point for ``python -m engine.api``."""

from __future__ import annotations

import uvicorn

from engine.api import create_app

if __name__ == "__main__":  # pragma: no cover
    uvicorn.run(create_app())
