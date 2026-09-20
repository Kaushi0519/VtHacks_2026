"""Gateway request/response + operator commands. CONTRACT FILE (see models/common.py)."""

from datetime import datetime
from typing import Any

from pydantic import Field

from app.models.agent import Agent, AgentStatus, BehaviorProfile
from app.models.common import ApiModel, Decision, RiskLevel
from app.models.event import ReasonCode, RiskSignal, SentinelEvent
from app.models.identity import IdentityResult
from app.models.incident import Incident
from app.models.policy import PermissionGrant


class AgentRequest(ApiModel):
    """What an agent (via SDK / sidecar / proxy) submits to the Lattice gateway."""

    actor_ans_name: str  # claimed identity, verified against ANS
    actor_agent_id: str | None = None  # optional hint; must match the enrolled agent if given
    action: str = Field(pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+){1,3}$")  # e.g. payroll.salary.read
    target_agent_id: str | None = None
    trace_id: str | None = None  # propagate to link delegated calls
    parent_event_id: str | None = None
    delegation_chain: list[str] = Field(default_factory=list)  # upstream agents, originator first
    payload: dict[str, Any] = Field(default_factory=dict)  # simulated body; not inspected in MVP
    observed_at: datetime | None = None  # history backfill only; requires ALLOW_BACKFILL=true
    source: str | None = None  # label such as "scenario:compromised_agent"; never used for policy


class GatewayDecision(ApiModel):
    event_id: str
    trace_id: str
    decision: Decision
    reason_code: ReasonCode
    reason: str
    identity: IdentityResult
    risk_before: int | None = None
    risk_after: int | None = None
    risk_level: RiskLevel | None = None
    signals: list[RiskSignal] = Field(default_factory=list)
    incident_id: str | None = None
    agent_status: AgentStatus | None = None
    result: dict[str, Any] | None = None  # simulated execution result when allowed


class QuarantineCommand(ApiModel):
    reason: str = "Isolated by operator"


class ReleaseCommand(ApiModel):
    note: str = "Reviewed and released by operator"


class GrantCommand(ApiModel):
    scope: str
    ttl_seconds: int = Field(gt=0, le=7 * 24 * 3600)
    idle_timeout_seconds: int | None = Field(default=None, gt=0)
    reason: str = "Just-in-time access"
    granted_by: str = "operator"


class RevokeCommand(ApiModel):
    reason: str = "Revoked by operator"


class AgentDetail(ApiModel):
    agent: Agent
    profile: BehaviorProfile
    grants: list[PermissionGrant]
    recent_events: list[SentinelEvent]
    open_incident: Incident | None = None
