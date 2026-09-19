"""One place that builds non-request (lifecycle) events so they are all shaped the same."""

from datetime import datetime
from typing import Any

from app.core.ids import new_id
from app.models.event import EventKind, ReasonCode, SentinelEvent


def lifecycle_event(
    kind: EventKind,
    agent_id: str,
    now: datetime,
    *,
    reason_code: ReasonCode,
    reason: str,
    initiated_by: str,
    trace_id: str | None = None,
    parent_event_id: str | None = None,
    action: str | None = None,
    target_resource: str | None = None,
    grant_id: str | None = None,
    incident_id: str | None = None,
    risk_before: int | None = None,
    risk_after: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> SentinelEvent:
    return SentinelEvent(
        id=new_id("evt"),
        trace_id=trace_id or new_id("trc"),
        parent_event_id=parent_event_id,
        timestamp=now,
        kind=kind,
        actor_agent_id=agent_id,
        action=action,
        target_resource=target_resource,
        reason_code=reason_code,
        reason=reason,
        initiated_by=initiated_by,
        grant_id=grant_id,
        incident_id=incident_id,
        risk_before=risk_before,
        risk_after=risk_after,
        metadata=metadata or {},
    )
