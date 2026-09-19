"""Runs behavioral analysis in the background and attaches it to the incident. Owner: Person 3."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from app.core.ids import utcnow
from app.db import repo
from app.models.event import EventKind, ReasonCode
from app.services.event_factory import lifecycle_event
from app.services.gemini.telemetry import incident_telemetry

if TYPE_CHECKING:
    from app.container import Container

log = logging.getLogger("sentinel.analysis")


class AnalysisRunner:
    def __init__(self, c: Container):
        self.c = c
        self._tasks: set[asyncio.Task] = set()
        self._inflight: set[str] = set()

    def schedule(self, incident_id: str) -> None:
        # Dedup: rapid escalation (incident opens, then escalates to quarantine) can ask to analyze
        # the same incident twice. One in-flight analysis per incident avoids duplicate Gemini calls
        # and duplicate ANALYSIS events/telemetry.
        if incident_id in self._inflight:
            return
        self._inflight.add(incident_id)
        task = asyncio.create_task(self._run(incident_id))
        self._tasks.add(task)

        def _done(t: asyncio.Task) -> None:
            self._tasks.discard(t)
            self._inflight.discard(incident_id)

        task.add_done_callback(_done)

    async def _run(self, incident_id: str) -> None:
        c = self.c
        try:
            with c.session_factory() as db:
                incident = repo.get_incident(db, incident_id)
                if incident is None or incident.analysis_status == "done":
                    return  # incident gone (demo reset) or already analyzed by an earlier run
                telemetry = incident_telemetry(db, c.world, incident)

            analysis = await c.analyzer.analyze_incident(telemetry)

            async with c.state_lock:
                with c.session_factory() as db:
                    incident = repo.get_incident(db, incident_id)
                    if incident is None:  # demo was reset meanwhile
                        return
                    now = utcnow()
                    event = repo.append_event(db, lifecycle_event(
                        EventKind.ANALYSIS, incident.agent_id, now,
                        reason_code=ReasonCode.ANALYSIS_COMPLETE, reason=analysis.reason,
                        initiated_by="analyzer",
                        trace_id=incident.trace_ids[-1] if incident.trace_ids else None,
                        parent_event_id=incident.trigger_event_id, incident_id=incident.id,
                        metadata={"analysis": analysis.to_json()},
                    ))
                    incident = incident.model_copy(update={
                        "analysis": analysis, "analysis_status": "done", "updated_at": now,
                        "event_ids": [*incident.event_ids, event.id],
                    })
                    repo.save_incident(db, incident)
                    db.commit()
            c.broadcaster.event(event)
            c.broadcaster.incident(incident)
        except Exception:
            log.exception("analysis failed for %s", incident_id)
