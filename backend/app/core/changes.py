"""Collects everything a state change produced so it can be broadcast AFTER the DB commit."""

from dataclasses import dataclass, field

from app.models.agent import Agent
from app.models.event import SentinelEvent
from app.models.incident import Incident
from app.models.policy import PermissionGrant
from app.realtime.broadcaster import Broadcaster


@dataclass
class Changes:
    events: list[SentinelEvent] = field(default_factory=list)
    agents: dict[str, Agent] = field(default_factory=dict)
    grants: dict[str, PermissionGrant] = field(default_factory=dict)
    incidents: dict[str, Incident] = field(default_factory=dict)
    analyze_incident_ids: list[str] = field(default_factory=list)

    def agent(self, a: Agent) -> None:
        self.agents[a.id] = a

    def grant(self, g: PermissionGrant) -> None:
        self.grants[g.id] = g

    def incident(self, i: Incident) -> None:
        self.incidents[i.id] = i

    def merge(self, other: "Changes") -> None:
        self.events.extend(other.events)
        self.agents.update(other.agents)
        self.grants.update(other.grants)
        self.incidents.update(other.incidents)
        self.analyze_incident_ids.extend(other.analyze_incident_ids)

    def publish(self, b: Broadcaster) -> None:
        for e in self.events:
            b.event(e)
        for a in self.agents.values():
            b.agent(a)
        for g in self.grants.values():
            b.grant(g)
        for i in self.incidents.values():
            b.incident(i)
