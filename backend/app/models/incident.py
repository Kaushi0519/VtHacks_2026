"""Incidents + AI behavioral analysis. CONTRACT FILE (see models/common.py)."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.models.common import ApiModel, Severity
from app.models.event import SentinelEvent


class IncidentStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


class AnomalyType(StrEnum):
    ROLE_RESOURCE_MISMATCH = "role_resource_mismatch"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    RATE_ANOMALY = "rate_anomaly"
    UNUSUAL_PEER = "unusual_peer"
    EXPIRED_ACCESS_REUSE = "expired_access_reuse"
    IDENTITY_FAILURE = "identity_failure"
    BENIGN = "benign"
    OTHER = "other"


class RecommendedAction(StrEnum):
    NONE = "none"
    MONITOR = "monitor"
    REQUIRE_HUMAN = "require_human"
    QUARANTINE = "quarantine"


class GeminiAnalysisOutput(BaseModel):
    """Exact structured-output schema we ask Gemini for. Kept constraint-free for the SDK;
    Lattice validates and clamps before use. Gemini supplies SEMANTIC findings; Lattice owns the score."""

    anomaly_type: AnomalyType
    severity: Severity
    confidence: float
    violations: list[str]  # short semantic violation tags, e.g. "task deviation", "possible exfiltration"
    reason: str
    recommended_action: RecommendedAction


class BehaviorAnalysis(ApiModel):
    anomaly_type: AnomalyType
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    violations: list[str] = Field(default_factory=list)  # semantic violations Gemini named
    reason: str
    recommended_action: RecommendedAction
    source: Literal["gemini", "fallback"]  # UI must label fallback as rule-based
    model: str | None = None
    analyzed_at: datetime
    error: str | None = None  # why Gemini was not used, if it wasn't


class Incident(ApiModel):
    id: str  # inc_...
    agent_id: str
    agent_known: bool  # False for unverified / unenrolled actors
    title: str
    severity: Severity
    status: IncidentStatus = IncidentStatus.OPEN
    opened_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    trigger_event_id: str
    event_ids: list[str] = Field(default_factory=list)
    trace_ids: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    signal_codes: list[str] = Field(default_factory=list)
    risk_peak: int | None = None
    quarantined: bool = False
    analysis: BehaviorAnalysis | None = None
    analysis_status: Literal["pending", "done", "skipped"] = "pending"
    resolution_note: str | None = None


class IncidentDetail(ApiModel):
    incident: Incident
    events: list[SentinelEvent]  # evidence, oldest first
