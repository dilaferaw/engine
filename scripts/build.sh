#!/usr/bin/env bash
# Render build step: install Python deps, build the SPA, leave web/dist in place.
set -euo pipefail

cd "$(dirname "$0")/.."

# Python deps (uv.lock is committed, so this is reproducible).
if command -v uv >/dev/null 2>&1; then
  uv sync --frozen --no-dev
else
  python -m pip install --upgrade pip
  python -m pip install .
fi

# Frontend: the backend serves web/dist at /, so it must exist before start.
if [ -d web ]; then
  cd web
  if [ -f package-lock.json ]; then
    npm ci
  else
    npm install
  fi
  npm run build
  cd ..
fi
