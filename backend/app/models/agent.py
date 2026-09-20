"""Agents + behavioral state. CONTRACT FILE (see models/common.py)."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field

from app.models.common import ApiModel, RiskLevel
from app.models.identity import IdentityResult


class AgentStatus(StrEnum):
    ACTIVE = "active"
    QUARANTINED = "quarantined"


class QuarantineInfo(ApiModel):
    since: datetime
    reason: str
    triggered_by: Literal["auto", "operator"]
    incident_id: str | None = None
    event_id: str | None = None


class Agent(ApiModel):
    id: str  # Lattice-local id, e.g. "facilities-agent"
    display_name: str
    role: str
    description: str = ""
    current_task: str = ""  # what this agent is CURRENTLY supposed to be doing; Gemini judges consistency
    ans_name: str  # e.g. "ans://v1.0.0.facilities.demo-hospital.example"
    identity: IdentityResult | None = None  # last ANS check
    status: AgentStatus = AgentStatus.ACTIVE
    # Lattice's Behavioral Risk Score (0-100). NOT an ANS trust/integrity score.
    risk_score: int
    risk_level: RiskLevel
    baseline_risk: int  # cool-down floor
    risk_updated_at: datetime
    quarantine: QuarantineInfo | None = None
    peers: list[str] = Field(default_factory=list)  # agents it normally talks to
    expected_rpm: int = 6  # normal requests/minute, used by the rate-spike signal
    last_seen_at: datetime | None = None


class BehaviorProfile(ApiModel):
    """What this agent normally does. Learned ONLY from allowed requests (no baseline poisoning)."""

    agent_id: str
    scope_counts: dict[str, int] = Field(default_factory=dict)
    resource_counts: dict[str, int] = Field(default_factory=dict)
    peer_counts: dict[str, int] = Field(default_factory=dict)
    signal_last_fired: dict[str, datetime] = Field(default_factory=dict)
    updated_at: datetime | None = None
