"""SentinelEvent: the most important contract in the project. CONTRACT FILE (see models/common.py).

Every meaningful decision appends exactly one immutable event. The live feed, graph animation,
incident evidence, and the accountability view are all built from these records. If something
can't be reconstructed from events, the design is incomplete.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from app.models.common import ApiModel, Decision
from app.models.identity import IdentityResult


class EventKind(StrEnum):
    REQUEST = "request"  # gateway decision on an agent request
    QUARANTINE = "quarantine"  # agent isolated (auto or operator)
    RELEASE = "release"  # agent released from quarantine
    GRANT_ISSUED = "grant_issued"
    GRANT_EXPIRED = "grant_expired"  # permission decay (TTL or idle)
    GRANT_REVOKED = "grant_revoked"
    ANALYSIS = "analysis"  # AI (or fallback) behavioral analysis attached to an incident


class ReasonCode(StrEnum):
    AI_SEMANTIC_QUARANTINE = "AI_SEMANTIC_QUARANTINE"
    # request decisions
    ALLOWED = "ALLOWED"
    IDENTITY_UNVERIFIED = "IDENTITY_UNVERIFIED"  # ANS: not found / revoked / expired / mismatch
    IDENTITY_UNAVAILABLE = "IDENTITY_UNAVAILABLE"  # ANS unreachable and no usable cache: fail closed
    AGENT_NOT_ENROLLED = "AGENT_NOT_ENROLLED"  # real ANS agent, but not part of this company's mesh
    AGENT_QUARANTINED = "AGENT_QUARANTINED"
    UNKNOWN_RESOURCE = "UNKNOWN_RESOURCE"
    FORBIDDEN_FOR_ROLE = "FORBIDDEN_FOR_ROLE"
    NO_GRANT = "NO_GRANT"
    GRANT_EXPIRED = "GRANT_EXPIRED"
    GRANT_REVOKED = "GRANT_REVOKED"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"
    RISK_THRESHOLD = "RISK_THRESHOLD"  # behavioral risk crossed the quarantine threshold
    # lifecycle events
    OPERATOR_ACTION = "OPERATOR_ACTION"
    TTL_ELAPSED = "TTL_ELAPSED"
    IDLE_TIMEOUT = "IDLE_TIMEOUT"
    QUARANTINE_CLEANUP = "QUARANTINE_CLEANUP"
    ANALYSIS_COMPLETE = "ANALYSIS_COMPLETE"


class SignalCode(StrEnum):
    FORBIDDEN_SCOPE = "FORBIDDEN_SCOPE"
    NEW_SENSITIVE_RESOURCE = "NEW_SENSITIVE_RESOURCE"
    RATE_SPIKE = "RATE_SPIKE"
    UNEXPECTED_PEER = "UNEXPECTED_PEER"
    REPEATED_DENIALS = "REPEATED_DENIALS"
    EXPIRED_GRANT_USE = "EXPIRED_GRANT_USE"
    HONEYPOT_ACCESS = "HONEYPOT_ACCESS"
    AI_ASSESSMENT = "AI_ASSESSMENT"  # P1: bounded adjustment from validated Gemini output


class RiskSignal(ApiModel):
    code: SignalCode
    weight: int  # points added to the Behavioral Risk Score
    detail: str


class SentinelEvent(ApiModel):
    id: str  # evt_...
    seq: int = 0  # global monotonic order, assigned on append
    trace_id: str  # trc_... shared by every event in one causal chain
    parent_event_id: str | None = None
    timestamp: datetime
    kind: EventKind

    actor_agent_id: str  # the agent this event is about (claimed id for unknown agents)
    actor_ans_name: str | None = None
    target_agent_id: str | None = None  # agent-to-agent communication
    target_resource: str | None = None  # Resource.id
    action: str | None = None  # scope, e.g. "payroll.salary.read"
    delegation_chain: list[str] = Field(default_factory=list)  # [originator, ..., direct caller]

    identity: IdentityResult | None = None  # request events only
    decision: Decision | None = None  # request events only
    reason_code: ReasonCode | None = None
    reason: str | None = None  # human-readable "why"

    risk_before: int | None = None
    risk_after: int | None = None
    signals: list[RiskSignal] = Field(default_factory=list)

    incident_id: str | None = None
    grant_id: str | None = None
    initiated_by: str = "gateway"  # gateway | sentinel | operator | analyzer
    # Free-form. Known keys: source ("scenario:<id>"), backfill (bool), analysis, result.
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventPage(ApiModel):
    items: list[SentinelEvent]
    next_before_seq: int | None = None  # pass as ?beforeSeq= for the next (older) page
