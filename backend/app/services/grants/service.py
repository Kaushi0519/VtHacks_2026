"""Permission decay: just-in-time grants that expire on their own. Owner: Person 1.

Semantics (what's allowed) live in services/policy + grants/rules.py; this module handles the
lifecycle: issue, touch on use, revoke, and the sweeper that makes expiry visible.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.changes import Changes
from app.core.ids import new_id
from app.db import repo
from app.models.agent import Agent, AgentStatus
from app.models.event import EventKind, ReasonCode
from app.models.gateway import GrantCommand
from app.models.policy import GrantKind, GrantStatus, PermissionGrant, World
from app.services.event_factory import lifecycle_event
from app.services.grants.rules import decay_reason
from app.services.policy.scopes import any_match


class GrantPolicyError(ValueError):
    """Raised when an operator asks for a grant the role policy doesn't allow."""


def issue_temporary(db: Session, world: World, agent: Agent, cmd: GrantCommand, now: datetime) -> Changes:
    role = world.role(agent.role)
    if agent.status == AgentStatus.QUARANTINED:
        raise GrantPolicyError(f"{agent.display_name} is quarantined")
    if any_match(role.forbidden, cmd.scope):
        raise GrantPolicyError(f"{cmd.scope} is forbidden for the {agent.role} role")
    if not any_match(role.grantable, cmd.scope):
        raise GrantPolicyError(f"{cmd.scope} is not grantable to the {agent.role} role")

    grant = PermissionGrant(
        id=new_id("grt"),
        agent_id=agent.id,
        scope=cmd.scope,
        kind=GrantKind.TEMPORARY,
        granted_at=now,
        expires_at=now + timedelta(seconds=cmd.ttl_seconds),
        idle_timeout_seconds=cmd.idle_timeout_seconds,
        granted_by=cmd.granted_by,
        reason=cmd.reason,
    )
    repo.save_grant(db, grant)
    resource = world.resource_for_scope(cmd.scope)
    event = repo.append_event(db, lifecycle_event(
        EventKind.GRANT_ISSUED, agent.id, now,
        reason_code=ReasonCode.OPERATOR_ACTION,
        reason=f"{cmd.scope} granted for {cmd.ttl_seconds}s: {cmd.reason}",
        initiated_by="operator", action=cmd.scope,
        target_resource=resource.id if resource else None, grant_id=grant.id,
        metadata={"expiresAt": grant.expires_at.isoformat() if grant.expires_at else None, "grantedBy": cmd.granted_by},
    ))
    return Changes(events=[event], grants={grant.id: grant})


def touch(grant: PermissionGrant, now: datetime) -> PermissionGrant:
    return grant.model_copy(update={"use_count": grant.use_count + 1, "last_used_at": now})


def revoke(
    db: Session,
    grant: PermissionGrant,
    now: datetime,
    *,
    reason: str,
    reason_code: ReasonCode = ReasonCode.OPERATOR_ACTION,
    initiated_by: str = "operator",
    trace_id: str | None = None,
    parent_event_id: str | None = None,
) -> Changes:
    if grant.status != GrantStatus.ACTIVE:
        return Changes()
    ended = grant.model_copy(update={
        "status": GrantStatus.REVOKED, "ended_at": now, "end_reason": reason_code.value,
    })
    repo.save_grant(db, ended)
    event = repo.append_event(db, lifecycle_event(
        EventKind.GRANT_REVOKED, grant.agent_id, now,
        reason_code=reason_code, reason=f"{grant.scope} revoked: {reason}",
        initiated_by=initiated_by, action=grant.scope, grant_id=grant.id,
        trace_id=trace_id, parent_event_id=parent_event_id,
    ))
    return Changes(events=[event], grants={ended.id: ended})


def sweep(db: Session, now: datetime) -> Changes:
    """Mark decayed grants EXPIRED and emit GRANT_EXPIRED events. Called every second."""
    changes = Changes()
    for grant in repo.list_grants(db, status=GrantStatus.ACTIVE):
        code = decay_reason(grant, now)
        if code is None:
            continue
        ended_at = grant.expires_at if code == ReasonCode.TTL_ELAPSED and grant.expires_at else now
        expired = grant.model_copy(update={"status": GrantStatus.EXPIRED, "ended_at": ended_at, "end_reason": code.value})
        repo.save_grant(db, expired)
        why = "time-to-live elapsed" if code == ReasonCode.TTL_ELAPSED else "unused past its idle timeout"
        changes.events.append(repo.append_event(db, lifecycle_event(
            EventKind.GRANT_EXPIRED, grant.agent_id, now,
            reason_code=code, reason=f"Access to {grant.scope} decayed ({why})",
            initiated_by="sentinel", action=grant.scope, grant_id=grant.id,
        )))
        changes.grant(expired)
    return changes
