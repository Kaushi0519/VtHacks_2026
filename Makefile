# Sentinel Mesh dev commands. Needs: uv (brew install uv), node 20+.
.PHONY: setup backend sim frontend test smoke reset backfill

setup:            ## install everything
	cd backend && uv sync
	cd simulator && uv sync
	cd frontend && npm install
	@test -f .env || cp .env.example .env
	@test -f frontend/.env.local || cp frontend/.env.local.example frontend/.env.local

backend:          ## API + gateway on :8000 (single worker on purpose)
	cd backend && uv run uvicorn app.main:app --reload --port 8000

sim:              ## simulator control API on :8001 (dashboard demo buttons)
	cd simulator && uv run python -m sentinel_sim serve

frontend:         ## dashboard on :3000
	cd frontend && npm run dev

test:             ## backend unit + flow tests
	cd backend && uv run pytest -q

smoke:            ## the whole demo against a running backend, with pass/fail checks
	cd simulator && uv run python -m sentinel_sim smoke

reset:            ## wipe demo state back to the seeded world
	curl -s -X POST localhost:8000/api/admin/reset && echo

backfill:         ## reset + seed 7 days of history for the accountability view
	cd simulator && uv run python -m sentinel_sim run history_backfill --check
