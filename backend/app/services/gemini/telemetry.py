"""Structured telemetry we hand to the analyzer. Owner: Person 3.

Keep it compact and factual. Only facts Sentinel observed; no raw payloads, no secrets.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.db import repo
from app.db.repo import EventFilter
from app.models.event import EventKind
from app.models.incident import Incident, IncidentStatus
from app.models.policy import World


def incident_telemetry(db: Session, world: World, incident: Incident) -> dict[str, Any]:
    agent = repo.get_agent(db, incident.agent_id)
    evidence = repo.get_events_by_ids(db, incident.event_ids)
    trigger = next((e for e in evidence if e.id == incident.trigger_event_id), evidence[0] if evidence else None)
    recent = list(reversed(repo.query_events(
        db, EventFilter(agent_id=incident.agent_id, kind=EventKind.REQUEST, limit=15)
    )))
    resource = world.resource_for_scope(trigger.action) if trigger and trigger.action else None

    data: dict[str, Any] = {
        "incident_title": incident.title,
        "agent": (
            {"id": agent.id, "role": agent.role, "description": agent.description, "status": agent.status.value}
            if agent else {"id": incident.agent_id, "enrolled": False}
        ),
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
        "recent_actions": [
            {"at": e.timestamp.isoformat(), "action": e.action, "decision": e.decision.value if e.decision else None,
             "reason_code": e.reason_code.value if e.reason_code else None}
            for e in recent
        ],
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
