# Backend (FastAPI gateway) image — for Railway / Render / Fly.
# IMPORTANT: build context is the REPO ROOT, not backend/, because the backend loads
# simulator/fixtures/world.yaml at REPO_ROOT (see backend/app/core/config.py). This Dockerfile
# copies both, so the platform doesn't have to guess.
FROM python:3.12-slim

# uv: fast, reproducible Python installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
# backend code + the world file it reads at /app/simulator/fixtures/world.yaml
COPY backend /app/backend
COPY simulator/fixtures /app/simulator/fixtures

RUN cd /app/backend && uv sync --no-dev

ENV PATH="/app/backend/.venv/bin:$PATH"
WORKDIR /app/backend
# ONE worker on purpose: in-memory state + the SSE stream live in a single process.
# $PORT is provided by the host (Railway/Render/Fly); defaults to 8000 locally.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
