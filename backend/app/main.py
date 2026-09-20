"""Sentinel Mesh backend. Run: `uv run uvicorn app.main:app --reload --port 8000` (ONE worker)."""

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.background import sweeper_loop
from app.container import build_container
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.seed import seed_if_empty

log = logging.getLogger("sentinel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    c = build_container(get_settings())
    with c.session_factory() as db:
        if seed_if_empty(db, c.world):
            log.info("seeded database from %s", c.settings.world_file)
        db.commit()
    log.info("ANS mode=%s  analyzer=%s  backfill=%s", c.ans.mode, c.analyzer.mode, c.settings.allow_backfill)
    with contextlib.suppress(Exception):
        await c.ans.warm_up([a.ans_name for a in c.world.agents])
    app.state.container = c
    sweeper = asyncio.create_task(sweeper_loop(c))
    try:
        yield
    finally:
        sweeper.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sweeper


app = FastAPI(title="Lattice", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
