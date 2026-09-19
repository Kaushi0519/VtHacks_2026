"""Visibility & accountability: what did each agent actually do over time?
CONTRACT FILE (see models/common.py)."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field

from app.models.agent import AgentStatus
from app.models.common import ApiModel, Severity
from app.models.incident import Incident


class Hypothesis(StrEnum):
    """Deterministic best guess at *why* an agent behaves the way it does."""

    HEALTHY = "healthy"
    LIKELY_MISCONFIGURED = "likely_misconfigured"
    POSSIBLY_COMPROMISED = "possibly_compromised"
    UNVERIFIED_IDENTITY = "unverified_identity"
    OVER_PRIVILEGED = "over_privileged"
    INACTIVE = "inactive"


class Finding(ApiModel):
    code: str  # e.g. REPEATED_OUT_OF_ROLE, REPEATED_NO_GRANT, UNUSED_STANDING_GRANT
    severity: Severity
    hypothesis: Hypothesis
    title: str
    detail: str
    evidence_event_ids: list[str] = Field(default_factory=list)


class ActivityTotals(ApiModel):
    requests: int = 0
    allowed: int = 0
    denied: int = 0
    require_human: int = 0
    quarantine_decisions: int = 0
    identity_failures: int = 0
    expired_grant_attempts: int = 0
    incidents: int = 0
    quarantines: int = 0


class AgentActivityRow(ApiModel):
    agent_id: str
    display_name: str
    role: str | None = None  # None for unknown actors
    known: bool
    status: AgentStatus | None = None
    risk_score: int | None = None  # live, cooled score (drifts back to baseline between requests)
    peak_risk: int | None = None  # worst score reached in the window; None if no requests in window
    totals: ActivityTotals
    top_reason: str | None = None  # most frequent denial ReasonCode
    hypothesis: Hypothesis
    findings: list[Finding] = Field(default_factory=list)
    last_seen_at: datetime | None = None


class FleetOverview(ApiModel):
    window_start: datetime
    window_end: datetime
    totals: ActivityTotals
    agents: list[AgentActivityRow]  # enrolled agents, most problematic first
    unknown_actors: list[AgentActivityRow]  # unverified / unenrolled callers


class ScopeUsage(ApiModel):
    scope: str
    total: int
    allowed: int
    denied: int
    in_role: bool  # covered by the agent's baseline/grantable policy
    last_at: datetime | None = None


class RiskPoint(ApiModel):
    timestamp: datetime
    risk: int


class GrantHygiene(ApiModel):
    active: int
    expired: int
    revoked: int
    unused_standing: list[str]  # baseline scopes never used in the window: decay candidates


class AccountabilitySummary(ApiModel):
    text: str
    source: Literal["gemini", "fallback"]
    model: str | None = None
    generated_at: datetime


class AgentReport(ApiModel):
    agent_id: str
    display_name: str
    known: bool
    window_start: datetime
    window_end: datetime
    totals: ActivityTotals
    peak_risk: int | None = None  # worst Behavioral Risk Score reached in the window (see risk_history)
    denials_by_reason: dict[str, int]
    scopes: list[ScopeUsage]
    risk_history: list[RiskPoint]
    incidents: list[Incident]
    grants: GrantHygiene | None = None
    findings: list[Finding]
    hypothesis: Hypothesis
    summary: AccountabilitySummary | None = None  # P1: Gemini narrative
