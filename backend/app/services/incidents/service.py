"""Incidents group the evidence that explains why Sentinel acted. Owner: Person 1.

One OPEN incident per agent at a time: incident-worthy events open it, later non-allowed
events for the same agent append to it, and releasing the agent resolves it.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db import repo
from app.models.agent import Agent
from app.models.common import Decision, Severity
from app.models.event import EventKind, ReasonCode, SentinelEvent
from app.models.incident import Incident, IncidentStatus
from app.models.policy import RiskPolicy

IDENTITY_FAILURES = {ReasonCode.IDENTITY_UNVERIFIED, ReasonCode.IDENTITY_UNAVAILABLE, ReasonCode.AGENT_NOT_ENROLLED}
_SEVERITY_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]


def is_incident_worthy(event: SentinelEvent, rp: RiskPolicy) -> bool:
    if event.kind == EventKind.QUARANTINE or event.decision == Decision.QUARANTINE:
        return True
    if event.reason_code in IDENTITY_FAILURES or event.reason_code == ReasonCode.FORBIDDEN_FOR_ROLE:
        return True
    return any(s.weight >= rp.incident_min_signal_weight for s in event.signals)


def record(
    db: Session, event: SentinelEvent, agent: Agent | None, rp: RiskPolicy, now: datetime
) -> tuple[Incident | None, bool]:
    """Attach `event` to the agent's open incident (opening one if warranted).
    Mutates event.incident_id; call BEFORE appending the event. Returns (incident, should_analyze)."""
    existing = repo.find_open_incident(db, event.actor_agent_id)
    worthy = is_incident_worthy(event, rp)
    quarantining = event.kind == EventKind.QUARANTINE or event.decision == Decision.QUARANTINE
    severity = _severity(event, rp)

    if existing is None:
        if not worthy:
            return None, False
        incident = Incident(
            id=new_id("inc"),
            agent_id=event.actor_agent_id,
            agent_known=agent is not None,
            title=_title(event, agent),
            severity=severity,
            opened_at=now,
            updated_at=now,
            trigger_event_id=event.id,
            event_ids=[event.id],
            trace_ids=[event.trace_id],
            reason_codes=[event.reason_code.value] if event.reason_code else [],
            signal_codes=[s.code.value for s in event.signals],
            risk_peak=event.risk_after,
            quarantined=quarantining,
        )
        event.incident_id = incident.id
        repo.save_incident(db, incident)
        return incident, True

    if not worthy and event.decision == Decision.ALLOW:
        return existing, False

    newly_quarantined = quarantining and not existing.quarantined
    # Incidents opened during history backfill were never analyzed; analyze on the first live event.
    analyze = newly_quarantined or existing.analysis_status == "skipped"
    incident = existing.model_copy(update={
        "updated_at": now,
        "title": _title(event, agent) if newly_quarantined else existing.title,
        "severity": max(existing.severity, severity, key=_SEVERITY_ORDER.index),
        "event_ids": [*existing.event_ids, event.id],
        "trace_ids": _union(existing.trace_ids, [event.trace_id]),
        "reason_codes": _union(existing.reason_codes, [event.reason_code.value] if event.reason_code else []),
        "signal_codes": _union(existing.signal_codes, [s.code.value for s in event.signals]),
        "risk_peak": max(x for x in (existing.risk_peak, event.risk_after, 0) if x is not None),
        "quarantined": existing.quarantined or quarantining,
        "analysis_status": "pending" if analyze else existing.analysis_status,
    })
    event.incident_id = incident.id
    repo.save_incident(db, incident)
    return incident, analyze


def resolve(db: Session, agent_id: str, now: datetime, note: str) -> Incident | None:
    incident = repo.find_open_incident(db, agent_id)
    if incident is None:
        return None
    resolved = incident.model_copy(update={
        "status": IncidentStatus.RESOLVED, "resolved_at": now, "updated_at": now, "resolution_note": note,
    })
    repo.save_incident(db, resolved)
    return resolved


def _severity(event: SentinelEvent, rp: RiskPolicy) -> Severity:
    if event.kind == EventKind.QUARANTINE or event.decision == Decision.QUARANTINE:
        return Severity.CRITICAL
    if event.reason_code in IDENTITY_FAILURES or event.reason_code == ReasonCode.FORBIDDEN_FOR_ROLE:
        return Severity.HIGH
    risk = event.risk_after or 0
    if risk >= rp.threshold_high:
        return Severity.HIGH
    if risk >= rp.threshold_elevated:
        return Severity.MEDIUM
    return Severity.LOW


def _title(event: SentinelEvent, agent: Agent | None) -> str:
    name = agent.display_name if agent else event.actor_agent_id
    if event.kind == EventKind.QUARANTINE or event.decision == Decision.QUARANTINE:
        return f"{name} quarantined: behavioral risk {event.risk_after}"
    if event.reason_code == ReasonCode.AGENT_NOT_ENROLLED:
        return f"Agent not enrolled in this mesh ({event.actor_ans_name}) attempted {event.action}"
    if event.reason_code in IDENTITY_FAILURES:
        return f"Unverified agent {name} attempted {event.action}"
    if event.reason_code == ReasonCode.FORBIDDEN_FOR_ROLE:
        return f"{name} requested {event.action} outside its role"
    codes = ", ".join(s.code.value for s in event.signals) or "abnormal behavior"
    return f"{name}: {codes}"


def _union(a: list[str], b: list[str]) -> list[str]:
    return [*a, *(x for x in b if x not in a)]
