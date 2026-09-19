"""Runs behavioral analysis off the request path and applies its effects. Owner: Person 3.

Two triggers feed the same analyzer:
  - schedule(incident_id): a hard rule already opened an incident; explain + possibly escalate.
  - schedule_review(agent_id): the agent touched sensitive data but NO rule fired; run a semantic
    review so Gemini can catch a malicious *sequence* of individually-permitted actions.

Applying the result (Sentinel owns the decision, Gemini supplies the semantic evidence):
  - a bounded score contribution from the severity (semantic_points), and
  - a Gemini-TRIGGERED quarantine when the finding is CRITICAL at high confidence and real
    (source=="gemini"). The rule-based fallback never quarantines and never moves the score.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from app.core.changes import Changes
from app.core.ids import utcnow
from app.db import repo
from app.models.agent import AgentStatus
from app.models.common import Severity
from app.models.event import EventKind, ReasonCode
from app.models.incident import BehaviorAnalysis, RecommendedAction, IncidentStatus
from app.services.behavior.risk import cooled_score, level_for, semantic_points
from app.services.event_factory import lifecycle_event
from app.services.gemini.telemetry import incident_telemetry, review_telemetry
from app.services.quarantine import service as quarantine

if TYPE_CHECKING:
    from app.container import Container

log = logging.getLogger("sentinel.analysis")

REVIEW_COOLDOWN_SECONDS = 3.5  # re-review as the pattern develops; still bounded so we don't spam Gemini


class AnalysisRunner:
    def __init__(self, c: Container):
        self.c = c
        self._tasks: set[asyncio.Task] = set()
        self._inflight: set[str] = set()          # incident ids currently being analyzed
        self._reviewing: set[str] = set()          # agent ids currently under semantic review
        self._review_last: dict[str, float] = {}   # agent id -> monotonic time of last review
        self._epoch = 0
        self._revisions: dict[str, int] = {}

    def invalidate(self, agent_id: str | None = None) -> None:
        """Called under state_lock after reset/release; old results cannot change new state."""
        if agent_id is None:
            self._epoch += 1
            self._revisions.clear()
            self._review_last.clear()
        else:
            self._revisions[agent_id] = self._revisions.get(agent_id, 0) + 1
            self._review_last.pop(agent_id, None)

    def _token(self, agent_id: str) -> tuple[int, int]:
        return self._epoch, self._revisions.get(agent_id, 0)

    # --- incident-triggered analysis (a hard rule already fired) ---
    def schedule(self, incident_id: str) -> None:
        if incident_id in self._inflight:
            return  # dedup: rapid escalation can ask twice; one analysis per incident
        self._inflight.add(incident_id)
        self._spawn(self._run(incident_id), lambda: self._inflight.discard(incident_id))

    # --- semantic review (sensitive activity, no rule fired) ---
    def schedule_review(self, agent_id: str) -> None:
        now = time.monotonic()
        if agent_id in self._reviewing or (now - self._review_last.get(agent_id, 0.0)) < REVIEW_COOLDOWN_SECONDS:
            return
        self._review_last[agent_id] = now
        self._reviewing.add(agent_id)
        self._spawn(self._run_review(agent_id), lambda: self._reviewing.discard(agent_id))

    def _spawn(self, coro, cleanup) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)

        def _done(t: asyncio.Task) -> None:
            self._tasks.discard(t)
            cleanup()

        task.add_done_callback(_done)

    async def _run(self, incident_id: str) -> None:
        try:
            with self.c.session_factory() as db:
                incident = repo.get_incident(db, incident_id)
                if incident is None or incident.analysis_status == "done":
                    return  # gone (reset) or already analyzed
                telemetry = incident_telemetry(db, self.c.world, incident)
                agent_id = incident.agent_id
                token = self._token(agent_id)
            analysis = await self.c.analyzer.analyze_incident(telemetry)
            await self._apply(agent_id, analysis, incident_id=incident_id, token=token)
        except Exception:
            log.exception("analysis failed for %s", incident_id)

    async def _run_review(self, agent_id: str) -> None:
        try:
            with self.c.session_factory() as db:
                agent = repo.get_agent(db, agent_id)
                if agent is None or agent.status == AgentStatus.QUARANTINED:
                    return
                telemetry = review_telemetry(db, self.c.world, agent)
                token = self._token(agent_id)
            analysis = await self.c.analyzer.analyze_incident(telemetry)
            await self._apply(agent_id, analysis, incident_id=None, token=token)
        except Exception:
            log.exception("semantic review failed for %s", agent_id)

    async def _apply(self, agent_id: str, analysis: BehaviorAnalysis, *, incident_id: str | None,
                     token: tuple[int, int]) -> None:
        c = self.c
        rp = c.world.risk_policy
        changes = Changes()
        async with c.state_lock:
            if token != self._token(agent_id):
                return
            with c.session_factory() as db:
                incident = repo.get_incident(db, incident_id) if incident_id else None
                if incident_id and (incident is None or incident.status != IncidentStatus.OPEN):
                    return
                agent = repo.get_agent(db, agent_id)
                if agent is None and incident is None:
                    return
                now = utcnow()
                points = semantic_points(analysis.source, analysis.severity, rp)
                triggers_quarantine = (
                    agent is not None
                    and analysis.source == "gemini"
                    and analysis.severity == Severity.CRITICAL
                    and analysis.confidence >= rp.ai_quarantine_min_confidence
                    and analysis.recommended_action == RecommendedAction.QUARANTINE
                    and agent.status != AgentStatus.QUARANTINED
                )
                log.info(
                    "gemini analysis agent=%s source=%s severity=%s confidence=%.2f action=%s violations=%s -> %s",
                    agent_id, analysis.source, analysis.severity.value, analysis.confidence,
                    analysis.recommended_action.value, analysis.violations,
                    "QUARANTINE" if triggers_quarantine else f"+{points}pts",
                )

                if triggers_quarantine:
                    # Gemini decided. Reflect its finding in the score, then isolate the agent.
                    risk_before = cooled_score(agent, now, rp)
                    bumped = max(0, min(100, risk_before + points))
                    agent = agent.model_copy(update={
                        "risk_score": bumped, "risk_level": level_for(bumped, rp), "risk_updated_at": now,
                    })
                    reason = (
                        f"Gemini semantic analysis flagged {analysis.severity.value} risk "
                        f"({analysis.confidence:.0%}): {analysis.reason}"
                    )
                    qchanges = quarantine.quarantine(
                        db, agent, now, rp, reason=reason, triggered_by="auto",
                        reason_code=ReasonCode.AI_SEMANTIC_QUARANTINE, risk_before=risk_before,
                    )
                    qchanges.analyze_incident_ids.clear()  # this incident already carries its analysis
                    for inc in list(qchanges.incidents.values()):
                        ev = repo.append_event(db, self._analysis_event(
                            agent_id, analysis, now, inc.id, inc.trigger_event_id,
                            risk_before=risk_before, risk_after=bumped,
                        ))
                        qchanges.events.append(ev)
                        qchanges.incident(inc.model_copy(update={
                            "analysis": analysis, "analysis_status": "done",
                            "event_ids": [*inc.event_ids, ev.id], "updated_at": now,
                        }))
                        repo.save_incident(db, qchanges.incidents[inc.id])
                    changes.merge(qchanges)
                else:
                    incident = repo.get_incident(db, incident_id) if incident_id else None
                    risk_before = risk_after = agent.risk_score if agent else None
                    if agent is not None and points and agent.status != AgentStatus.QUARANTINED:
                        risk_before = cooled_score(agent, now, rp)
                        risk_after = max(0, min(100, risk_before + points))
                        agent = agent.model_copy(update={
                            "risk_score": risk_after, "risk_level": level_for(risk_after, rp), "risk_updated_at": now,
                        })
                        repo.save_agent(db, agent)
                        changes.agent(agent)
                    trace_id = incident.trace_ids[-1] if incident and incident.trace_ids else None
                    parent = incident.trigger_event_id if incident else None
                    ev = repo.append_event(db, self._analysis_event(
                        agent_id, analysis, now, incident.id if incident else None, parent,
                        trace_id=trace_id, risk_before=risk_before, risk_after=risk_after,
                    ))
                    changes.events.append(ev)
                    if incident is not None:
                        changes.incident(incident.model_copy(update={
                            "analysis": analysis, "analysis_status": "done",
                            "event_ids": [*incident.event_ids, ev.id], "updated_at": now,
                        }))
                        repo.save_incident(db, changes.incidents[incident.id])
                db.commit()
        changes.publish(c.broadcaster)

    @staticmethod
    def _analysis_event(agent_id, analysis, now, incident_id, parent_event_id, *, trace_id=None,
                        risk_before=None, risk_after=None):
        return lifecycle_event(
            EventKind.ANALYSIS, agent_id, now,
            reason_code=ReasonCode.ANALYSIS_COMPLETE, reason=analysis.reason,
            initiated_by="analyzer", incident_id=incident_id, parent_event_id=parent_event_id,
            trace_id=trace_id, risk_before=risk_before, risk_after=risk_after,
            metadata={"analysis": analysis.to_json()},
        )
