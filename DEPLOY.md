# Deploying to Render (free tier)

One web service runs the FastAPI app **and** serves the built SPA from
`web/dist`. No Redis, no separate worker, no client changes.

## Files involved

| File | Role |
| --- | --- |
| `render.yaml` | Blueprint: build/start commands, free plan, one instance |
| `scripts/build.sh` | Render build step: `uv sync --frozen --no-dev` then `npm ci && npm run build` in `web/` |
| `.env.example` | Documents env vars; copy to `.env` for local dev only |
| `engine/api/application.py` | CORS origins now read `ALLOWED_ORIGINS` + `RENDER_EXTERNAL_URL` |

## Deploy steps

1. Push the repo to GitHub (branch `master`).
2. Render Dashboard → **New** → **Blueprint** → select the repo. Render reads
   `render.yaml` automatically.
3. Apply. First build takes a few minutes (Python deps + `npm ci` + vite).
4. Open the service URL. The SPA loads at `/`, the API is same-origin.

## Env vars

Set in the Render dashboard (Render does **not** read `.env`):

| Key | Required | Notes |
| --- | --- | --- |
| `PYTHON_VERSION` | yes | `3.12.8` (set in `render.yaml`) |
| `REDIS_URL` | no | Only if you scale past one instance |
| `ALLOWED_ORIGINS` | no | Extra CORS origins, comma-separated |

`RENDER_EXTERNAL_URL` is injected by Render automatically and is added to the
CORS allow-list.

## Free-tier behaviour to expect

- **Sleep after 15 min idle**, ~1 min cold start. An open game tab sends an SSE
  keepalive every 15 s, so an active game keeps the service awake; an idle
  lobby does not.
- **One instance only.** Games live in `InMemoryGameStore` and the lobby in
  `MemoryLobbyStore`; both are per-process. Do not raise the instance count
  without setting `REDIS_URL` (lobby only — games still need a shared store).
- **Restart loses all games.** Inherent to in-memory storage.

## Local check before deploying

```sh
uv run pytest tests -q                 # backend
cd web && npm run build && cd ..       # produces web/dist for the SPA route
uv run uvicorn engine.api:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/` — the SPA is served by the same process.
