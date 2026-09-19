"""Aggregates the event history into fleet- and agent-level accountability views. Owner: Person 1.
Finding rules live in findings.py (Person 3)."""

from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.db import repo
from app.db.repo import EventFilter
from app.models.accountability import (
    ActivityTotals,
    AgentActivityRow,
    AgentReport,
    FleetOverview,
    GrantHygiene,
    RiskPoint,
    ScopeUsage,
)
from app.models.agent import Agent
from app.models.common import Decision
from app.models.event import EventKind
from app.models.policy import GrantKind, GrantStatus, World
from app.services.accountability.findings import PRECEDENCE, FindingInput, evaluate, primary_hypothesis
from app.services.incidents.service import IDENTITY_FAILURES
from app.services.policy.scopes import any_match

_IDENTITY_CODES = {c.value for c in IDENTITY_FAILURES}


class _Acc:
    def __init__(self) -> None:
        self.totals = ActivityTotals()
        self.denied_by_scope: dict[str, Counter] = defaultdict(Counter)
        self.denial_reasons: Counter = Counter()
        self.scopes: dict[str, ScopeUsage] = {}
        self.last_seen: datetime | None = None

    def add(self, action: str | None, decision: str | None, reason: str | None, n: int, last: datetime) -> None:
        t = self.totals
        t.requests += n
        if decision == Decision.ALLOW.value:
            t.allowed += n
        elif decision == Decision.DENY.value:
            t.denied += n
        elif decision == Decision.REQUIRE_HUMAN.value:
            t.require_human += n
        elif decision == Decision.QUARANTINE.value:
            t.quarantine_decisions += n
        if reason in _IDENTITY_CODES:
            t.identity_failures += n
        if reason == "GRANT_EXPIRED":
            t.expired_grant_attempts += n
        denied = decision in (Decision.DENY.value, Decision.QUARANTINE.value)
        if denied and reason:
            self.denial_reasons[reason] += n
            if action:
                self.denied_by_scope[action][reason] += n
        if action:
            s = self.scopes.setdefault(action, ScopeUsage(scope=action, total=0, allowed=0, denied=0, in_role=False))
            s.total += n
            s.allowed += n if decision == Decision.ALLOW.value else 0
            s.denied += n if denied else 0
            s.last_at = max(filter(None, [s.last_at, last]))
        self.last_seen = max(filter(None, [self.last_seen, last]))


def _accumulate(db: Session, start: datetime, end: datetime) -> dict[str, _Acc]:
    accs: dict[str, _Acc] = defaultdict(_Acc)
    for actor, action, decision, reason, n, last in repo.request_event_stats(db, start, end):
        accs[actor].add(action, decision, reason, n, last)
    incident_counts = Counter(i.agent_id for i in repo.list_incidents(db, since=start, limit=10_000))
    quarantines = repo.kind_counts(db, EventKind.QUARANTINE, start, end)
    for actor in set(incident_counts) | set(quarantines):
        accs[actor].totals.incidents = incident_counts.get(actor, 0)
        accs[actor].totals.quarantines = quarantines.get(actor, 0)
    return accs


def _row(
    agent_id: str, acc: _Acc, agent: Agent | None, db: Session, world: World, start: datetime, end: datetime
) -> AgentActivityRow:
    findings = evaluate(FindingInput(
        known=agent is not None,
        window_days=round((end - start).total_seconds() / 86400, 1),
        window_start=start,
        totals=acc.totals,
        denied_by_scope={s: dict(c) for s, c in acc.denied_by_scope.items()},
        grants=repo.list_grants(db, agent_id=agent_id) if agent else [],
        forbidden=world.role(agent.role).forbidden if agent else [],
    ))
    return AgentActivityRow(
        agent_id=agent_id,
        display_name=agent.display_name if agent else agent_id,
        role=agent.role if agent else None,
        known=agent is not None,
        status=agent.status if agent else None,
        risk_score=agent.risk_score if agent else None,
        totals=acc.totals,
        top_reason=acc.denial_reasons.most_common(1)[0][0] if acc.denial_reasons else None,
        hypothesis=primary_hypothesis(findings),
        findings=findings,
        last_seen_at=acc.last_seen,
    )


def fleet_overview(db: Session, world: World, start: datetime, end: datetime) -> FleetOverview:
    accs = _accumulate(db, start, end)
    agents = {a.id: a for a in repo.list_agents(db)}
    known_rows = [_row(a.id, accs.get(a.id) or _Acc(), a, db, world, start, end) for a in agents.values()]
    unknown_rows = [_row(aid, acc, None, db, world, start, end) for aid, acc in accs.items() if aid not in agents]

    def rank(r: AgentActivityRow):
        return (PRECEDENCE.index(r.hypothesis), -r.totals.denied - r.totals.quarantine_decisions)

    totals = ActivityTotals()
    for acc in accs.values():
        for field in ActivityTotals.model_fields:
            setattr(totals, field, getattr(totals, field) + getattr(acc.totals, field))
    return FleetOverview(
        window_start=start, window_end=end, totals=totals,
        agents=sorted(known_rows, key=rank), unknown_actors=sorted(unknown_rows, key=rank),
    )


def agent_report(db: Session, world: World, agent_id: str, start: datetime, end: datetime) -> AgentReport:
    agent = repo.get_agent(db, agent_id)
    acc = _accumulate(db, start, end).get(agent_id) or _Acc()
    row = _row(agent_id, acc, agent, db, world, start, end)

    scopes = list(acc.scopes.values())
    if agent:
        role = world.role(agent.role)
        for s in scopes:
            s.in_role = any_match(role.baseline + role.grantable, s.scope)

    events = repo.query_events(db, EventFilter(agent_id=agent_id, since=start, until=end, limit=1000))
    risk_history = [
        RiskPoint(timestamp=e.timestamp, risk=e.risk_after)
        for e in sorted(events, key=lambda e: e.timestamp)
        if e.risk_after is not None
    ]

    grants = None
    if agent:
        all_grants = repo.list_grants(db, agent_id=agent_id)
        grants = GrantHygiene(
            active=sum(g.status == GrantStatus.ACTIVE for g in all_grants),
            expired=sum(g.status == GrantStatus.EXPIRED for g in all_grants),
            revoked=sum(g.status == GrantStatus.REVOKED for g in all_grants),
            unused_standing=sorted(
                g.scope for g in all_grants
                if g.kind == GrantKind.BASELINE and (g.last_used_at is None or g.last_used_at < start)
            ),
        )

    return AgentReport(
        agent_id=agent_id,
        display_name=row.display_name,
        known=row.known,
        window_start=start,
        window_end=end,
        totals=acc.totals,
        denials_by_reason=dict(acc.denial_reasons),
        scopes=sorted(scopes, key=lambda s: (-s.denied, -s.total)),
        risk_history=risk_history,
        incidents=repo.list_incidents(db, agent_id=agent_id, since=start),
        grants=grants,
        findings=row.findings,
        hypothesis=row.hypothesis,
        summary=None,  # TODO(P3, P1): Gemini narrative over this report (cache per agent+window)
    )
