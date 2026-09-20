"""The Lattice request lifecycle. Owner: Person 1 (orchestration only).

    1. identity    ANS resolves + verifies the claimed name        -> DENY if unverified
    2. quarantine  isolated agents get nothing                     -> DENY
    3. permission  role policy + the agent's OWN live grants       -> permitted / denied / human
    4. behavior    deterministic signals raise the Behavioral Risk Score
    5. enforce     risk >= critical -> QUARANTINE, else the permission outcome
    6. record      append ONE immutable request event (+ incident, quarantine, grant usage)
    7. publish     broadcast after commit; schedule async AI analysis (never blocks the decision)

Security semantics live in services/policy, services/behavior, services/quarantine (Person 3).
Keep this file a thin sequencer so both owners can work without colliding.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.core.changes import Changes
from app.core.ids import new_id, utcnow
from app.core.logging import log_event
from app.db import repo
from app.db.repo import EventFilter
from app.models.agent import Agent, AgentStatus
from app.models.common import Decision, Sensitivity
from app.models.event import EventKind, ReasonCode, SentinelEvent
from app.models.gateway import AgentRequest, GatewayDecision
from app.models.identity import IdentityResult
from app.services.behavior.profile import learn, mark_fired
from app.services.behavior.risk import apply_signals, cooled_score, level_for
from app.services.behavior.signals import SignalContext, compute_signals
from app.services.grants.service import touch
from app.services.incidents import service as incidents
from app.services.policy.enforcement import decide
from app.services.policy.engine import evaluate_permission
from app.services.quarantine import service as quarantine

if TYPE_CHECKING:
    from app.container import Container


class Gateway:
    def __init__(self, c: Container):
        self.c = c

    async def evaluate(self, req: AgentRequest) -> GatewayDecision:
        c = self.c
        backfill = req.observed_at is not None
        now = req.observed_at if req.observed_at else utcnow()
        trace_id = req.trace_id or new_id("trc")

        # Step 1 needs the network, so it runs before taking the state lock.
        identity = await c.ans.verify_agent(req.actor_ans_name)

        async with c.state_lock:
            with c.session_factory() as db:
                response, changes = self._decide(db, req, identity, now, trace_id, backfill)
                db.commit()

        # Log only after the commit succeeds, so we never log a decision the DB rejected.
        if changes.decision_event is not None:
            log_event(changes.decision_event)
        if backfill:
            return response  # history seeding: no live broadcast, no AI calls (see /api/admin/resync)
        changes.publish(c.broadcaster)
        for incident_id in changes.analyze_incident_ids:
            c.analysis.schedule(incident_id)
        self._maybe_semantic_review(changes.decision_event)
        return response

    def _maybe_semantic_review(self, event: SentinelEvent | None) -> None:
        """Second detector: once an agent has AGGREGATED sensitive data (several allowed high/critical
        accesses), run a Gemini semantic review so a malicious *sequence* of individually-permitted
        actions is caught even when no hard rule fired. Throttled per agent in the AnalysisRunner."""
        if event is None or event.decision != Decision.ALLOW or not event.action:
            return
        resource = self.c.world.resource_for_scope(event.action)
        if resource is None or resource.sensitivity not in (Sensitivity.HIGH, Sensitivity.CRITICAL):
            return
        with self.c.session_factory() as db:
            recent = repo.query_events(
                db, EventFilter(agent_id=event.actor_agent_id, kind=EventKind.REQUEST, limit=15)
            )
        sensitive = sum(
            1 for e in recent
            if e.decision == Decision.ALLOW and e.action
            and (r := self.c.world.resource_for_scope(e.action)) is not None
            and r.sensitivity in (Sensitivity.HIGH, Sensitivity.CRITICAL)
        )
        if sensitive >= 3:
            self.c.analysis.schedule_review(event.actor_agent_id)

    def _decide(
        self, db: Session, req: AgentRequest, identity: IdentityResult, now, trace_id: str, backfill: bool
    ) -> tuple[GatewayDecision, Changes]:
        world, rp = self.c.world, self.c.world.risk_policy
        changes = Changes()
        agent = repo.get_agent_by_ans(db, req.actor_ans_name)
        resource = world.resource_for_scope(req.action)

        event = SentinelEvent(
            id=new_id("evt"),
            trace_id=trace_id,
            parent_event_id=req.parent_event_id,
            timestamp=now,
            kind=EventKind.REQUEST,
            actor_agent_id=agent.id if agent else (req.actor_agent_id or req.actor_ans_name),
            actor_ans_name=req.actor_ans_name,
            target_agent_id=req.target_agent_id,
            target_resource=resource.id if resource else None,
            action=req.action,
            delegation_chain=req.delegation_chain,
            identity=identity,
            metadata={k: v for k, v in {"source": req.source, "backfill": backfill}.items() if v},
        )

        # 1. identity
        denial = _identity_denial(req, identity, agent)
        if denial is not None:
            return self._deny_early(db, event, agent, identity, *denial, now, backfill, changes)

        assert agent is not None
        agent = agent.model_copy(update={"identity": identity, "last_seen_at": now})

        # 2. quarantine
        if agent.status == AgentStatus.QUARANTINED:
            return self._deny_early(
                db, event, agent, identity, ReasonCode.AGENT_QUARANTINED,
                f"{agent.display_name} is quarantined; all communication denied until reviewed",
                now, backfill, changes,
            )

        # 3. permission
        perm = evaluate_permission(
            agent.role, world.role(agent.role), repo.list_grants(db, agent_id=agent.id), req.action, resource, now
        )

        # 4. behavior
        profile = repo.get_profile(db, agent.id)
        ctx = SignalContext(
            agent=agent,
            profile=profile,
            action=req.action,
            resource=resource,
            target_agent_id=req.target_agent_id,
            permission=perm,
            requests_in_window=repo.count_requests(db, agent.id, now - timedelta(seconds=rp.rate_window_seconds), now) + 1,
            denials_in_window=repo.count_denials(db, agent.id, now - timedelta(seconds=rp.repeated_denials_window_seconds), now),
            now=now,
        )
        signals = compute_signals(ctx, rp)
        risk_before = cooled_score(agent, now, rp)
        risk_after = apply_signals(risk_before, signals)

        # 5. enforce
        decision, reason_code, reason = decide(perm, risk_after, rp)

        # 6. record
        event.decision, event.reason_code, event.reason = decision, reason_code, reason
        event.risk_before, event.risk_after, event.signals = risk_before, risk_after, signals

        profile = mark_fired(profile, signals, now)
        result = None
        if decision == Decision.ALLOW:
            # Agents' real work is simulated; Lattice only decides and records.
            profile = learn(profile, req.action, resource.id if resource else None, req.target_agent_id, now)
            result = {"status": "executed", "simulated": True}
            event.metadata["result"] = "executed (simulated)"
            if perm.grant is not None:
                # Record which grant authorized this request (audit completeness) and count the use.
                # Only a real execution touches the grant: a require_human decision executed nothing,
                # so it must NOT refresh the idle timer and keep decaying access alive.
                event.grant_id = perm.grant.id
                used = touch(perm.grant, now)  # feeds idle-decay and "unused permission" findings
                repo.save_grant(db, used)
                changes.grant(used)
        repo.save_profile(db, profile)

        agent = agent.model_copy(update={
            "risk_score": risk_after, "risk_level": level_for(risk_after, rp), "risk_updated_at": now,
        })
        incident, analyze = incidents.record(db, event, agent, rp, now)
        changes.events.append(repo.append_event(db, event))
        repo.save_agent(db, agent)
        changes.agent(agent)
        if incident:
            changes.incident(incident)
            if analyze:
                changes.analyze_incident_ids.append(incident.id)

        if decision == Decision.QUARANTINE:
            changes.merge(quarantine.quarantine(
                db, agent, now, rp,
                reason=f"Behavioral risk {risk_after} reached {rp.threshold_critical} (critical)",
                triggered_by="auto", trace_id=trace_id, parent_event_id=event.id,
            ))
            agent = changes.agents.get(agent.id, agent)

        self._finalize(db, changes, backfill)
        changes.decision_event = event
        return _response(event, agent, result), changes

    def _deny_early(
        self, db: Session, event: SentinelEvent, agent: Agent | None, identity: IdentityResult,
        code: ReasonCode, reason: str, now, backfill: bool, changes: Changes,
    ) -> tuple[GatewayDecision, Changes]:
        rp = self.c.world.risk_policy
        event.decision, event.reason_code, event.reason = Decision.DENY, code, reason
        if agent is not None:
            agent = agent.model_copy(update={"identity": identity, "last_seen_at": now})
            event.risk_before = event.risk_after = agent.risk_score
            repo.save_agent(db, agent)
            changes.agent(agent)
        incident, analyze = incidents.record(db, event, agent, rp, now)
        changes.events.append(repo.append_event(db, event))
        if incident:
            changes.incident(incident)
            if analyze:
                changes.analyze_incident_ids.append(incident.id)
        self._finalize(db, changes, backfill)
        changes.decision_event = event
        return _response(event, agent, None), changes

    def _finalize(self, db: Session, changes: Changes, backfill: bool) -> None:
        if not backfill:
            return
        for incident_id in changes.analyze_incident_ids:
            incident = repo.get_incident(db, incident_id)
            if incident:
                repo.save_incident(db, incident.model_copy(update={"analysis_status": "skipped"}))
        changes.analyze_incident_ids.clear()


def _identity_denial(
    req: AgentRequest, identity: IdentityResult, agent: Agent | None
) -> tuple[ReasonCode, str] | None:
    if not identity.verified:
        if identity.ans_status == "UNREACHABLE":
            return ReasonCode.IDENTITY_UNAVAILABLE, "ANS is unreachable and no cached identity is available; failing closed"
        return ReasonCode.IDENTITY_UNVERIFIED, f"ANS could not verify {req.actor_ans_name} (status {identity.ans_status})"
    if agent is None:
        return ReasonCode.AGENT_NOT_ENROLLED, f"{req.actor_ans_name} is a valid ANS identity but is not enrolled in this mesh"
    if req.actor_agent_id and req.actor_agent_id != agent.id:
        return ReasonCode.IDENTITY_UNVERIFIED, f"Claimed id {req.actor_agent_id} does not match the ANS identity of {agent.id}"
    return None


def _response(event: SentinelEvent, agent: Agent | None, result: dict | None) -> GatewayDecision:
    assert event.decision and event.reason_code and event.identity
    return GatewayDecision(
        event_id=event.id,
        trace_id=event.trace_id,
        decision=event.decision,
        reason_code=event.reason_code,
        reason=event.reason or "",
        identity=event.identity,
        risk_before=event.risk_before,
        risk_after=event.risk_after,
        risk_level=agent.risk_level if agent else None,
        signals=event.signals,
        incident_id=event.incident_id,
        agent_status=agent.status if agent else None,
        result=result,
    )
