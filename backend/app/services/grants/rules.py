"""Pure permission-decay rules shared by the policy engine and the sweeper. Owner: Person 1.

A grant is live only if it is ACTIVE, its TTL hasn't elapsed, and (if it has an idle timeout)
it was used recently enough. The policy engine checks this at request time, so enforcement never
depends on the sweeper's timing. The sweeper only makes expiry *visible* (event + UI update).
"""

from datetime import datetime

from app.models.event import ReasonCode
from app.models.policy import GrantStatus, PermissionGrant


def decay_reason(grant: PermissionGrant, now: datetime) -> ReasonCode | None:
    """Why an ACTIVE grant should now be considered expired, or None if it is still live."""
    if grant.status != GrantStatus.ACTIVE:
        return None
    if grant.expires_at is not None and grant.expires_at <= now:
        return ReasonCode.TTL_ELAPSED
    if grant.idle_timeout_seconds is not None:
        last = grant.last_used_at or grant.granted_at
        if (now - last).total_seconds() > grant.idle_timeout_seconds:
            return ReasonCode.IDLE_TIMEOUT
    return None


def is_live(grant: PermissionGrant, now: datetime) -> bool:
    return grant.status == GrantStatus.ACTIVE and decay_reason(grant, now) is None
