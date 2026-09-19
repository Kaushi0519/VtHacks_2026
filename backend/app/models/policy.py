"""Tenant world: resources, role policies, risk policy, permission grants.
CONTRACT FILE (see models/common.py).

The world file (simulator/fixtures/world.yaml) is validated against `World` at startup.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import Field, ConfigDict, field_validator, model_validator
from fnmatch import fnmatchcase

from app.models.common import ApiModel, Sensitivity


class WorldConfigModel(ApiModel):
    model_config = ConfigDict(extra="forbid")


class Resource(WorldConfigModel):
    id: str  # e.g. "payroll-system"
    display_name: str
    scope_prefix: str  # first segment of scopes on this resource, e.g. "payroll"
    sensitivity: Sensitivity
    requires_human: list[str] = Field(default_factory=list)  # scope patterns needing approval
    honeypot: bool = False  # stretch: deception resource


class RolePolicy(WorldConfigModel):
    """Scope patterns use fnmatch syntax: "building.*", "payroll.salary.*"."""

    description: str = ""
    baseline: list[str]  # standing grants every agent of this role gets
    grantable: list[str] = Field(default_factory=list)  # may get temporary (decaying) grants
    forbidden: list[str] = Field(default_factory=list)  # hard deny + risk signal


class RiskPolicy(WorldConfigModel):
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
    # Gemini SEMANTIC findings map to bounded score contributions (Sentinel owns the number, not the LLM).
    # Only real (source=="gemini") analysis contributes; the rule-based fallback never does.
    weight_ai_semantic_medium: int = 10
    weight_ai_semantic_high: int = 25
    weight_ai_semantic_critical: int = 40
    # Gemini may itself quarantine on a CRITICAL semantic finding at/above this confidence, even when
    # deterministic signals stayed calm. Obvious violations never wait for this (they quarantine on rules).
    ai_quarantine_min_confidence: float = 0.85
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


    @field_validator("*")
    @classmethod
    def valid_numbers(cls, value, info):
        name = info.field_name
        if name == "ai_quarantine_min_confidence":
            if not 0 <= value <= 1:
                raise ValueError("confidence threshold must be between 0 and 1")
        elif name.startswith(("threshold_", "weight_")) or name in ("risk_after_release", "incident_min_signal_weight"):
            if not 0 <= value <= 100:
                raise ValueError("risk values must be between 0 and 100")
        elif name in ("signal_cooldown_seconds", "cooldown_per_minute"):
            if not value >= 0:
                raise ValueError("cooldown must be nonnegative")
        elif not value > 0:
            raise ValueError("window and rate parameters must be positive")
        return value

    @model_validator(mode="after")
    def ordered_thresholds(self):
        if not 0 < self.threshold_elevated < self.threshold_high < self.threshold_critical <= 100:
            raise ValueError("risk thresholds must increase within 1..100")
        return self


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


class AgentSpec(WorldConfigModel):
    id: str
    display_name: str
    role: str
    ans_name: str
    description: str = ""
    current_task: str = ""  # active assignment; Gemini judges whether behavior is consistent with it
    peers: list[str] = Field(default_factory=list)
    expected_rpm: int = Field(default=6, gt=0)
    initial_risk: int = Field(default=8, ge=0, le=100)


class AnsRegistryEntry(WorldConfigModel):
    """Used ONLY by the mock ANS adapter. Mirrors what is registered in real ANS."""

    ans_name: str
    ans_agent_id: str
    status: str = "ACTIVE"
    display_name: str | None = None


class TenantInfo(WorldConfigModel):
    id: str
    name: str


class World(WorldConfigModel):
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


    @model_validator(mode="after")
    def consistent_world(self):
        def unique(values, label):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label}")
        unique([a.id for a in self.agents], "agent IDs")
        unique([a.ans_name for a in self.agents], "agent ANS names")
        unique([r.id for r in self.resources], "resource IDs")
        unique([r.scope_prefix for r in self.resources], "resource prefixes")
        unique([r.ans_name for r in self.ans_mock_registry], "registry ANS names")
        unique([r.ans_agent_id for r in self.ans_mock_registry], "registry IDs")
        agent_ids = {a.id for a in self.agents}
        if agent_ids & {r.id for r in self.resources}:
            raise ValueError("agent and resource IDs must be distinct")
        for agent in self.agents:
            if agent.role not in self.roles:
                raise ValueError(f"unknown role for {agent.id}")
            if not set(agent.peers) <= agent_ids:
                raise ValueError(f"unknown peer for {agent.id}")
        for name, role in self.roles.items():
            for scope in role.baseline:
                if any(fnmatchcase(scope, denied) or fnmatchcase(denied, scope) for denied in role.forbidden):
                    raise ValueError(f"baseline conflicts with forbidden scope in {name}")
        return self
