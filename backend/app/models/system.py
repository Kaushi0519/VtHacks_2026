"""Dashboard bootstrap + realtime envelope. CONTRACT FILE (see models/common.py)."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from app.models.agent import Agent
from app.models.common import ApiModel
from app.models.event import SentinelEvent
from app.models.incident import Incident
from app.models.policy import PermissionGrant, Resource, RiskPolicy


class SystemInfo(ApiModel):
    tenant_name: str
    ans_mode: Literal["real", "mock"]
    ans_base_url: str | None  # None in mock mode
    analyzer_mode: Literal["gemini", "fallback"]
    gemini_model: str | None
    risk_policy: RiskPolicy
    backfill_enabled: bool
    server_time: datetime


class GraphNode(ApiModel):
    id: str
    kind: Literal["agent", "resource"]
    label: str
    group: str  # role for agents, sensitivity for resources


class GraphEdge(ApiModel):
    id: str
    source: str
    target: str
    kind: Literal["peer", "access"]  # agent<->agent communication, agent->resource access


class Graph(ApiModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class Snapshot(ApiModel):
    """One call hydrates the dashboard; the SSE stream then sends deltas."""

    system: SystemInfo
    agents: list[Agent]
    resources: list[Resource]
    graph: Graph
    grants: list[PermissionGrant]  # active + ended in the last 10 minutes
    incidents: list[Incident]  # open + most recent
    events: list[SentinelEvent]  # newest first
    last_seq: int


class StreamType(StrEnum):
    EVENT = "event"  # data: SentinelEvent
    AGENT = "agent"  # data: Agent (full replacement)
    INCIDENT = "incident"  # data: Incident (full replacement)
    GRANT = "grant"  # data: PermissionGrant (full replacement)
    RESYNC = "resync"  # data: {}; bulk change (reset / history backfill): refetch /api/snapshot


class StreamMessage(ApiModel):
    type: StreamType
    data: dict[str, Any]
