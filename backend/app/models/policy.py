"""Tenant world: resources, role policies, risk policy, permission grants.
CONTRACT FILE (see models/common.py).

The world file (simulator/fixtures/world.yaml) is validated against `World` at startup.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.models.common import ApiModel, Sensitivity


class Resource(ApiModel):
    id: str  # e.g. "payroll-system"
    display_name: str
    scope_prefix: str  # first segment of scopes on this resource, e.g. "payroll"
    sensitivity: Sensitivity
    requires_human: list[str] = Field(default_factory=list)  # scope patterns needing approval
    honeypot: bool = False  # stretch: deception resource


class RolePolicy(ApiModel):
    """Scope patterns use fnmatch syntax: "building.*", "payroll.salary.*"."""

    description: str = ""
    baseline: list[str]  # standing grants every agent of this role gets
    grantable: list[str] = Field(default_factory=list)  # may get temporary (decaying) grants
    forbidden: list[str] = Field(default_factory=list)  # hard deny + risk signal


class RiskPolicy(ApiModel):
    """Transparent, hand-tuned heuristics. Not a calibrated model; never claim otherwise."""

    threshold_elevated: int = 30
    threshold_high: int = 60
    threshold_critical: int = 80  # >= this: auto-quarantine
    weight_forbidden_scope: int = 35
    weight_new_sensitive_resource: int = 20
    weight_rate_spike: int = 15
    weight_unexpected_peer: int = 15
    weight_repeated_denials: int = 10
    weight_expired_grant_use: int = 5
    weight_honeypot: int = 50
    rate_window_seconds: int = 60
    rate_spike_multiplier: float = 3.0
    rate_spike_min_requests: int = 8
    repeated_denials_threshold: int = 3
    repeated_denials_window_seconds: int = 300
    signal_cooldown_seconds: int = 60  # a signal fires at most once per window
    cooldown_per_minute: float = 1.0  # risk decays toward baseline while behaving
    risk_after_release: int = 40  # probation score after an operator releases quarantine
    # A single signal this heavy opens an incident (forbidden scope, honeypot). Weaker patterns
    # (e.g. a misconfigured agent) surface in the accountability view instead of paging anyone.
    incident_min_signal_weight: int = 30


class GrantKind(StrEnum):
    BASELINE = "baseline"  # standing, from role policy
    TEMPORARY = "temporary"  # just-in-time, decays


class GrantStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PermissionGrant(ApiModel):
    id: str
    agent_id: str
    scope: str  # exact scope or fnmatch pattern
    kind: GrantKind
    status: GrantStatus = GrantStatus.ACTIVE
    granted_at: datetime
    expires_at: datetime | None = None  # TTL decay
    idle_timeout_seconds: int | None = None  # use-it-or-lose-it decay
    last_used_at: datetime | None = None
    use_count: int = 0
    granted_by: str  # "policy:role:facilities" | "operator" | "scenario:<id>"
    reason: str | None = None
    ended_at: datetime | None = None
    end_reason: str | None = None  # ReasonCode value: TTL_ELAPSED | IDLE_TIMEOUT | OPERATOR_ACTION | ...


class AgentSpec(ApiModel):
    id: str
    display_name: str
    role: str
    ans_name: str
    description: str = ""
    peers: list[str] = Field(default_factory=list)
    expected_rpm: int = 6
    initial_risk: int = 8


class AnsRegistryEntry(ApiModel):
    """Used ONLY by the mock ANS adapter. Mirrors what is registered in real ANS."""

    ans_name: str
    ans_agent_id: str
    status: str = "ACTIVE"
    display_name: str | None = None


class TenantInfo(ApiModel):
    id: str
    name: str


class World(ApiModel):
    tenant: TenantInfo
    resources: list[Resource]
    roles: dict[str, RolePolicy]
    agents: list[AgentSpec]
    risk_policy: RiskPolicy = Field(default_factory=RiskPolicy)
    ans_mock_registry: list[AnsRegistryEntry] = Field(default_factory=list)

    def resource_for_scope(self, scope: str) -> Resource | None:
        prefix = scope.split(".", 1)[0]
        return next((r for r in self.resources if r.scope_prefix == prefix), None)

    def role(self, role: str) -> RolePolicy:
        return self.roles[role]
