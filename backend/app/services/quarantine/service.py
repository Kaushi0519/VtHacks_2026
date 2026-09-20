"""Quarantine: isolate an agent from the whole mesh, not just one request. Owner: Person 3.

While quarantined every request is denied (AGENT_QUARANTINED) regardless of grants, and its
temporary grants are revoked (least privilege on compromise).

Kill switch note: this is Lattice-level isolation. Revoking the agent's identity itself is an
ANS lifecycle operation (POST /v1/agents/{agentId}/revoke). That is a P2 stretch and must stay
an explicit operator action: ANS revocation is permanent.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.changes import Changes
from app.db import repo
from app.models.agent import Agent, AgentStatus, QuarantineInfo
from app.models.event import EventKind, ReasonCode
from app.models.policy import GrantKind, GrantStatus, RiskPolicy
from app.services.behavior.risk import level_for
from app.services.event_factory import lifecycle_event
from app.services.grants import service as grants
from app.services.incidents import service as incidents


def quarantine(
    db: Session,
    agent: Agent,
    now: datetime,
    rp: RiskPolicy,
    *,
    reason: str,
    triggered_by: str,  # "auto" | "operator"
    trace_id: str | None = None,
    parent_event_id: str | None = None,
    reason_code: ReasonCode | None = None,
    risk_before: int | None = None,
) -> Changes:
    changes = Changes()
    if agent.status == AgentStatus.QUARANTINED:
        return changes

    event = lifecycle_event(
        EventKind.QUARANTINE, agent.id, now,
        reason_code=reason_code or (ReasonCode.RISK_THRESHOLD if triggered_by == "auto" else ReasonCode.OPERATOR_ACTION),
        reason=reason,
        initiated_by="sentinel" if triggered_by == "auto" else "operator",
        trace_id=trace_id, parent_event_id=parent_event_id,
        risk_before=agent.risk_score if risk_before is None else risk_before, risk_after=agent.risk_score,
    )
    event.actor_ans_name = agent.ans_name
    incident, analyze = incidents.record(db, event, agent, rp, now)
    changes.events.append(repo.append_event(db, event))
    if incident:
        changes.incident(incident)
        if analyze:
            changes.analyze_incident_ids.append(incident.id)

    quarantined = agent.model_copy(update={
        "status": AgentStatus.QUARANTINED,
        "quarantine": QuarantineInfo(
            since=now, reason=reason, triggered_by=triggered_by,
            incident_id=incident.id if incident else None, event_id=event.id,
        ),
    })
    repo.save_agent(db, quarantined)
    changes.agent(quarantined)

    for grant in repo.list_grants(db, agent_id=agent.id, status=GrantStatus.ACTIVE):
        if grant.kind == GrantKind.TEMPORARY:
            changes.merge(grants.revoke(
                db, grant, now, reason="agent quarantined", reason_code=ReasonCode.QUARANTINE_CLEANUP,
                initiated_by="sentinel", trace_id=event.trace_id, parent_event_id=event.id,
            ))
    return changes


def release(db: Session, agent: Agent, now: datetime, rp: RiskPolicy, *, note: str) -> Changes:
    changes = Changes()
    if agent.status != AgentStatus.QUARANTINED:
        return changes
    probation = max(agent.baseline_risk, min(agent.risk_score, rp.risk_after_release))
    released = agent.model_copy(update={
        "status": AgentStatus.ACTIVE,
        "quarantine": None,
        "risk_score": probation,
        "risk_level": level_for(probation, rp),
        "risk_updated_at": now,
    })
    repo.save_agent(db, released)
    changes.agent(released)
    resolved = incidents.resolve(db, agent.id, now, note)
    event = repo.append_event(db, lifecycle_event(
        EventKind.RELEASE, agent.id, now,
        reason_code=ReasonCode.OPERATOR_ACTION, reason=note, initiated_by="operator",
        risk_before=agent.risk_score, risk_after=probation,
        incident_id=resolved.id if resolved else None,
    ))
    changes.events.append(event)
    if resolved:
        resolved = resolved.model_copy(update={"event_ids": [*resolved.event_ids, event.id]})
        repo.save_incident(db, resolved)
        changes.incident(resolved)
    return changes
