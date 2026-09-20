"""Structured telemetry we hand to the analyzer. Owner: Person 3.

Gemini does SEMANTIC analysis: is this agent's behavior consistent with its role and its current task?
So the telemetry centers on identity (role, task), a recent action window (with resource sensitivity),
the deterministic anomaly signals, and who it has been delegating to. Only facts Lattice observed;
no raw payloads, no secrets.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.db import repo
from app.db.repo import EventFilter
from app.models.agent import Agent
from app.models.event import EventKind, SentinelEvent
from app.models.incident import Incident, IncidentStatus
from app.models.policy import World


def _identity(agent: Agent | None, agent_id: str) -> dict[str, Any]:
    if agent is None:
        return {"id": agent_id, "enrolled": False}
    return {
        "id": agent.id,
        "role": agent.role,
        "description": agent.description,
        "current_task": agent.current_task or "(no task assigned)",
        "status": agent.status.value,
    }


def _recent_actions(events: list[SentinelEvent], world: World) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for e in events:
        resource = world.resource_for_scope(e.action) if e.action else None
        rows.append({
            "at": e.timestamp.isoformat(),
            "action": e.action,
            "target": e.target_agent_id or e.target_resource,
            "resource_sensitivity": resource.sensitivity.value if resource else None,
            "decision": e.decision.value if e.decision else None,
            "reason_code": e.reason_code.value if e.reason_code else None,
        })
    return rows


def incident_telemetry(db: Session, world: World, incident: Incident) -> dict[str, Any]:
    agent = repo.get_agent(db, incident.agent_id)
    evidence = repo.get_events_by_ids(db, incident.event_ids)
    trigger = next((e for e in evidence if e.id == incident.trigger_event_id), evidence[0] if evidence else None)
    recent = list(reversed(repo.query_events(
        db, EventFilter(agent_id=incident.agent_id, kind=EventKind.REQUEST, limit=15)
    )))
    resource = world.resource_for_scope(trigger.action) if trigger and trigger.action else None

    data: dict[str, Any] = {
        "trigger": "incident",
        "incident_title": incident.title,
        "agent": _identity(agent, incident.agent_id),
        "identity": (
            {"ans_verified": trigger.identity.verified, "ans_status": trigger.identity.ans_status}
            if trigger and trigger.identity else None
        ),
        "requested_action": trigger.action if trigger else None,
        "requested_resource": (
            {"name": resource.display_name, "sensitivity": resource.sensitivity.value} if resource else None
        ),
        "signals": sorted({s.code.value + ": " + s.detail for e in evidence for s in e.signals}),
        "risk_before": evidence[0].risk_before if evidence else None,
        "risk_peak": incident.risk_peak,
        "quarantined": incident.quarantined,
        "recent_actions": _recent_actions(recent, world),
        "delegated_to": sorted({e.target_agent_id for e in recent if e.target_agent_id}),
    }
    if agent:
        role = world.role(agent.role)
        profile = repo.get_profile(db, agent.id)
        data["role_policy"] = {"baseline": role.baseline, "forbidden": role.forbidden}
        data["normal_actions"] = sorted(profile.scope_counts, key=profile.scope_counts.get, reverse=True)[:10]
        data["previous_incidents"] = len(
            [i for i in repo.list_incidents(db, agent_id=agent.id, status=IncidentStatus.RESOLVED)]
        )
    return data


def review_telemetry(db: Session, world: World, agent: Agent) -> dict[str, Any]:
    """Semantic review of an agent that touched sensitive data even though no hard rule fired.
    Built purely from the recent action window so Gemini can judge the SEQUENCE, not one request."""
    recent = list(reversed(repo.query_events(
        db, EventFilter(agent_id=agent.id, kind=EventKind.REQUEST, limit=15)
    )))
    role = world.role(agent.role)
    profile = repo.get_profile(db, agent.id)
    window = recent[-10:]
    sensitive_hits = [
        r for r in _recent_actions(window, world)
        if r["resource_sensitivity"] in ("high", "critical") and r["decision"] == "allow"
    ]
    return {
        "trigger": "semantic_review",
        "agent": _identity(agent, agent.id),
        "risk_before": agent.risk_score,
        "role_policy": {"baseline": role.baseline, "forbidden": role.forbidden},
        "normal_actions": sorted(profile.scope_counts, key=profile.scope_counts.get, reverse=True)[:10],
        "known_peers": agent.peers,
        "recent_actions": _recent_actions(window, world),
        "sensitive_data_touched": sensitive_hits,
        "delegated_to": sorted({e.target_agent_id for e in window if e.target_agent_id}),
    }
