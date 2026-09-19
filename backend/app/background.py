"""Background loop: permission decay sweeper + risk cool-down. Owner: Person 1."""

import asyncio
import logging

from app.container import Container
from app.core.ids import utcnow
from app.services.behavior.cooldown import cool_down_agents
from app.services.grants.service import sweep

log = logging.getLogger("sentinel.background")

COOLDOWN_EVERY_N_TICKS = 5


async def sweeper_loop(c: Container) -> None:
    tick = 0
    while True:
        await asyncio.sleep(c.settings.sweep_interval_seconds)
        tick += 1
        try:
            async with c.state_lock:
                with c.session_factory() as db:
                    now = utcnow()
                    changes = sweep(db, now)
                    if tick % COOLDOWN_EVERY_N_TICKS == 0:
                        changes.merge(cool_down_agents(db, c.world.risk_policy, now))
                    db.commit()
            changes.publish(c.broadcaster)
        except Exception:
            log.exception("sweeper tick failed")
