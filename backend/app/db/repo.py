"""All persistence goes through here. Services never touch SQLAlchemy rows directly.

Owner: Person 1. Add query helpers here rather than writing SQL inside services.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.tables import AgentRow, EventRow, GrantRow, IncidentRow
from app.models.agent import Agent, BehaviorProfile
from app.models.common import Decision
from app.models.event import EventKind, SentinelEvent
from app.models.incident import Incident, IncidentStatus
from app.models.policy import GrantStatus, PermissionGrant

# --- agents -------------------------------------------------------------------------------


def get_agent(db: Session, agent_id: str) -> Agent | None:
    row = db.get(AgentRow, agent_id)
    return Agent.model_validate(row.body) if row else None


def get_agent_by_ans(db: Session, ans_name: str) -> Agent | None:
    row = db.scalar(select(AgentRow).where(AgentRow.ans_name == ans_name))
    return Agent.model_validate(row.body) if row else None


def list_agents(db: Session) -> list[Agent]:
    return [Agent.model_validate(r.body) for r in db.scalars(select(AgentRow).order_by(AgentRow.id))]


def save_agent(db: Session, agent: Agent) -> None:
    row = db.get(AgentRow, agent.id)
    if row is None:
        row = AgentRow(id=agent.id, profile=BehaviorProfile(agent_id=agent.id).to_json())
        db.add(row)
    row.ans_name = agent.ans_name
    row.status = agent.status.value
    row.body = agent.to_json()


def get_profile(db: Session, agent_id: str) -> BehaviorProfile:
    row = db.get(AgentRow, agent_id)
    if row is None or not row.profile:
        return BehaviorProfile(agent_id=agent_id)
    return BehaviorProfile.model_validate(row.profile)


def save_profile(db: Session, profile: BehaviorProfile) -> None:
    row = db.get(AgentRow, profile.agent_id)
    if row is not None:
        row.profile = profile.to_json()


# --- grants -------------------------------------------------------------------------------


def get_grant(db: Session, grant_id: str) -> PermissionGrant | None:
    row = db.get(GrantRow, grant_id)
    return PermissionGrant.model_validate(row.body) if row else None


def list_grants(
    db: Session, agent_id: str | None = None, status: GrantStatus | None = None
) -> list[PermissionGrant]:
    q = select(GrantRow)
    if agent_id:
        q = q.where(GrantRow.agent_id == agent_id)
    if status:
        q = q.where(GrantRow.status == status.value)
    return [PermissionGrant.model_validate(r.body) for r in db.scalars(q)]


def save_grant(db: Session, grant: PermissionGrant) -> None:
    row = db.get(GrantRow, grant.id)
    if row is None:
        row = GrantRow(id=grant.id)
        db.add(row)
    row.agent_id = grant.agent_id
    row.status = grant.status.value
    row.expires_at = grant.expires_at
    row.body = grant.to_json()


# --- events (append-only) -----------------------------------------------------------------


def append_event(db: Session, event: SentinelEvent) -> SentinelEvent:
    row = EventRow(
        id=event.id,
        trace_id=event.trace_id,
        timestamp=event.timestamp,
        kind=event.kind.value,
        actor_agent_id=event.actor_agent_id,
        action=event.action,
        decision=event.decision.value if event.decision else None,
        reason_code=event.reason_code.value if event.reason_code else None,
        incident_id=event.incident_id,
        body={},
    )
    db.add(row)
    db.flush()  # assigns seq
    event.seq = row.seq
    row.body = event.to_json()
    return event


@dataclass
class EventFilter:
    agent_id: str | None = None
    kind: EventKind | None = None
    decision: Decision | None = None
    reason_code: str | None = None
    trace_id: str | None = None
    incident_id: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    before_seq: int | None = None
    limit: int = 100


def query_events(db: Session, f: EventFilter) -> list[SentinelEvent]:
    """Newest first (by seq)."""
    q = select(EventRow)
    if f.agent_id:
        q = q.where(EventRow.actor_agent_id == f.agent_id)
    if f.kind:
        q = q.where(EventRow.kind == f.kind.value)
    if f.decision:
        q = q.where(EventRow.decision == f.decision.value)
    if f.reason_code:
        q = q.where(EventRow.reason_code == f.reason_code)
    if f.trace_id:
        q = q.where(EventRow.trace_id == f.trace_id)
    if f.incident_id:
        q = q.where(EventRow.incident_id == f.incident_id)
    if f.since:
        q = q.where(EventRow.timestamp >= f.since)
    if f.until:
        q = q.where(EventRow.timestamp <= f.until)
    if f.before_seq:
        q = q.where(EventRow.seq < f.before_seq)
    q = q.order_by(EventRow.seq.desc()).limit(f.limit)
    return [SentinelEvent.model_validate(r.body) for r in db.scalars(q)]


def get_events_by_ids(db: Session, ids: list[str]) -> list[SentinelEvent]:
    """Oldest first."""
    if not ids:
        return []
    rows = db.scalars(select(EventRow).where(EventRow.id.in_(ids)).order_by(EventRow.seq))
    return [SentinelEvent.model_validate(r.body) for r in rows]


def count_requests(db: Session, agent_id: str, since: datetime, until: datetime) -> int:
    return db.scalar(
        select(func.count())
        .select_from(EventRow)
        .where(
            EventRow.actor_agent_id == agent_id,
            EventRow.kind == EventKind.REQUEST.value,
            EventRow.timestamp >= since,
            EventRow.timestamp <= until,
        )
    ) or 0


def count_denials(db: Session, agent_id: str, since: datetime, until: datetime) -> int:
    return db.scalar(
        select(func.count())
        .select_from(EventRow)
        .where(
            EventRow.actor_agent_id == agent_id,
            EventRow.kind == EventKind.REQUEST.value,
            EventRow.decision.in_([Decision.DENY.value, Decision.QUARANTINE.value]),
            EventRow.timestamp >= since,
            EventRow.timestamp <= until,
        )
    ) or 0


def last_seq(db: Session) -> int:
    return db.scalar(select(func.max(EventRow.seq))) or 0


def request_event_stats(db: Session, since: datetime, until: datetime) -> list[tuple]:
    """(actor_agent_id, action, decision, reason_code, count, last_timestamp) for request events."""
    q = (
        select(
            EventRow.actor_agent_id,
            EventRow.action,
            EventRow.decision,
            EventRow.reason_code,
            func.count(),
            func.max(EventRow.timestamp),
        )
        .where(
            EventRow.kind == EventKind.REQUEST.value,
            EventRow.timestamp >= since,
            EventRow.timestamp <= until,
        )
        .group_by(EventRow.actor_agent_id, EventRow.action, EventRow.decision, EventRow.reason_code)
    )
    return list(db.execute(q).all())


def peak_risk_by_actor(
    db: Session, since: datetime, until: datetime, agent_id: str | None = None
) -> dict[str, int]:
    """Highest Behavioral Risk Score each actor reached (max risk_after) over the window.

    Retrospective "worst it got" for the accountability view — distinct from the live, cooled
    `agent.risk_score`, which decays back to baseline between requests. risk_after lives only in the
    event body JSON, so we scan the window's request events and reduce in Python (portable across
    SQLite/Postgres; the window is small enough for the demo)."""
    q = select(EventRow.actor_agent_id, EventRow.body).where(
        EventRow.kind == EventKind.REQUEST.value,
        EventRow.timestamp >= since,
        EventRow.timestamp <= until,
    )
    if agent_id:
        q = q.where(EventRow.actor_agent_id == agent_id)
    peaks: dict[str, int] = {}
    for actor, body in db.execute(q):
        risk = body.get("riskAfter")
        if risk is not None and risk > peaks.get(actor, -1):
            peaks[actor] = risk
    return peaks


def kind_counts(db: Session, kind: EventKind, since: datetime, until: datetime) -> dict[str, int]:
    q = (
        select(EventRow.actor_agent_id, func.count())
        .where(EventRow.kind == kind.value, EventRow.timestamp >= since, EventRow.timestamp <= until)
        .group_by(EventRow.actor_agent_id)
    )
    return {agent_id: n for agent_id, n in db.execute(q).all()}


# --- incidents ----------------------------------------------------------------------------


def get_incident(db: Session, incident_id: str) -> Incident | None:
    row = db.get(IncidentRow, incident_id)
    return Incident.model_validate(row.body) if row else None


def find_open_incident(db: Session, agent_id: str) -> Incident | None:
    row = db.scalar(
        select(IncidentRow)
        .where(IncidentRow.agent_id == agent_id, IncidentRow.status == IncidentStatus.OPEN.value)
        .order_by(IncidentRow.opened_at.desc())
    )
    return Incident.model_validate(row.body) if row else None


def list_incidents(
    db: Session,
    status: IncidentStatus | None = None,
    agent_id: str | None = None,
    since: datetime | None = None,
    limit: int = 100,
) -> list[Incident]:
    q = select(IncidentRow)
    if status:
        q = q.where(IncidentRow.status == status.value)
    if agent_id:
        q = q.where(IncidentRow.agent_id == agent_id)
    if since:
        q = q.where(IncidentRow.opened_at >= since)
    q = q.order_by(IncidentRow.opened_at.desc()).limit(limit)
    return [Incident.model_validate(r.body) for r in db.scalars(q)]


def save_incident(db: Session, incident: Incident) -> None:
    row = db.get(IncidentRow, incident.id)
    if row is None:
        row = IncidentRow(id=incident.id)
        db.add(row)
    row.agent_id = incident.agent_id
    row.status = incident.status.value
    row.opened_at = incident.opened_at
    row.body = incident.to_json()
