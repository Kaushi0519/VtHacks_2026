# Simulator control API (:8001) — powers the dashboard demo bar. For Railway/Render/Fly.
# Build context = simulator/ (set Root Directory = simulator on the host). world.py loads
# fixtures/world.yaml relative to this dir, so copying the whole simulator/ is all it needs.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY . /app
RUN uv sync --no-dev

ENV PATH="/app/.venv/bin:$PATH"
# Talks to the backend over HTTP (set SENTINEL_URL to the deployed backend). $PORT from the host.
CMD ["sh", "-c", "uvicorn sentinel_sim.server:app --host 0.0.0.0 --port ${PORT:-8001}"]
