"""Deterministic authorization: may this agent use this scope right now? Owner: Person 3.

Pure function over role policy + the agent's own grants. Delegation never inherits
permissions: only the direct caller's grants are checked, whoever is upstream in the chain.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.models.event import ReasonCode
from app.models.policy import GrantStatus, PermissionGrant, Resource, RolePolicy
from app.services.grants.rules import is_live
from app.services.policy.scopes import any_match, scope_matches


@dataclass(frozen=True)
class PermissionResult:
    outcome: Literal["permitted", "denied", "require_human"]
    reason_code: ReasonCode
    reason: str
    grant: PermissionGrant | None = None  # the grant used (or the dead one that no longer applies)

    @property
    def permitted(self) -> bool:
        return self.outcome == "permitted"


def evaluate_permission(
    role_name: str,
    role: RolePolicy,
    grants: list[PermissionGrant],
    scope: str,
    resource: Resource | None,
    now: datetime,
) -> PermissionResult:
    if resource is None:
        return PermissionResult("denied", ReasonCode.UNKNOWN_RESOURCE, f"No resource serves scope {scope}")

    if any_match(role.forbidden, scope):
        return PermissionResult(
            "denied", ReasonCode.FORBIDDEN_FOR_ROLE, f"{scope} is forbidden for the {role_name} role"
        )

    matching = [g for g in grants if scope_matches(g.scope, scope)]
    live = [g for g in matching if is_live(g, now)]
    if not live:
        if not matching:
            return PermissionResult("denied", ReasonCode.NO_GRANT, f"No grant covers {scope}")
        latest = max(matching, key=lambda g: g.ended_at or g.expires_at or g.granted_at)
        if latest.status == GrantStatus.REVOKED:
            return PermissionResult("denied", ReasonCode.GRANT_REVOKED, f"Grant for {scope} was revoked", latest)
        return PermissionResult("denied", ReasonCode.GRANT_EXPIRED, f"Access to {scope} has decayed", latest)

    grant = min(live, key=_preference)

    if any_match(resource.requires_human, scope):
        return PermissionResult(
            "require_human", ReasonCode.REQUIRES_HUMAN, f"{scope} requires human approval", grant
        )
    return PermissionResult("permitted", ReasonCode.ALLOWED, f"Allowed by {grant.kind.value} grant {grant.scope}", grant)


def _preference(g: PermissionGrant) -> tuple[int, float]:
    """Standing grants first, then the temporary grant that lives longest."""
    return (0, 0.0) if g.expires_at is None else (1, -g.expires_at.timestamp())
