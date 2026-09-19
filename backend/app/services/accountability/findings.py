"""Deterministic findings: turn raw history into "Agent X has these specific problems". Owner: Person 3.

Every finding must be backed by counts from stored events so an operator (or a judge) can ask
"why do you say that?" and get evidence, not vibes.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.models.accountability import ActivityTotals, Finding, Hypothesis
from app.models.common import Severity
from app.models.policy import GrantKind, PermissionGrant
from app.services.policy.scopes import any_match

PRECEDENCE = [
    Hypothesis.UNVERIFIED_IDENTITY,
    Hypothesis.POSSIBLY_COMPROMISED,
    Hypothesis.LIKELY_MISCONFIGURED,
    Hypothesis.OVER_PRIVILEGED,
    Hypothesis.INACTIVE,
    Hypothesis.HEALTHY,
]

REPEATED_NO_GRANT_MIN = 3
OUT_OF_ROLE_MIN = 2
EXPIRED_REUSE_MIN = 2


@dataclass
class FindingInput:
    known: bool
    window_days: float
    window_start: datetime
    totals: ActivityTotals
    # scope -> {reason_code -> count} for non-allowed requests
    denied_by_scope: dict[str, dict[str, int]] = field(default_factory=dict)
    grants: list[PermissionGrant] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)  # role's forbidden scope patterns
    attempted_scopes: set[str] = field(default_factory=set)  # every scope the agent tried, any decision


def _n(count: float, noun: str) -> str:
    return f"{count:g} {noun}{'' if count == 1 else 's'}"


def evaluate(inp: FindingInput) -> list[Finding]:
    t = inp.totals
    days = _n(inp.window_days, "day")
    findings: list[Finding] = []

    if not inp.known:
        scopes = ", ".join(sorted(inp.denied_by_scope)) or "resources"
        return [Finding(
            code="UNVERIFIED_IDENTITY", severity=Severity.HIGH, hypothesis=Hypothesis.UNVERIFIED_IDENTITY,
            title="Not a verified company agent",
            detail=f"{_n(t.requests, 'attempt')} in {days} targeting {scopes}. ANS could not verify it, or it is not enrolled in this mesh.",
        )]

    # Match on the role's forbidden patterns, not reason codes: a forbidden request that tipped the
    # agent into quarantine is recorded with reason RISK_THRESHOLD.
    out_of_role = {s: sum(r.values()) for s, r in inp.denied_by_scope.items() if any_match(inp.forbidden, s)}
    if t.quarantines or sum(out_of_role.values()) >= OUT_OF_ROLE_MIN:
        findings.append(Finding(
            code="REPEATED_OUT_OF_ROLE",
            severity=Severity.CRITICAL if t.quarantines else Severity.HIGH,
            hypothesis=Hypothesis.POSSIBLY_COMPROMISED,
            title="Requests far outside its role",
            detail=(
                f"{_n(sum(out_of_role.values()), 'out-of-role request')} ({', '.join(sorted(out_of_role)) or 'n/a'})"
                f"; quarantined {t.quarantines}x in {days}."
            ),
        ))

    for scope, reasons in sorted(inp.denied_by_scope.items()):
        n = reasons.get("NO_GRANT", 0)
        if n >= REPEATED_NO_GRANT_MIN:
            findings.append(Finding(
                code="REPEATED_NO_GRANT", severity=Severity.MEDIUM, hypothesis=Hypothesis.LIKELY_MISCONFIGURED,
                title=f"Keeps requesting {scope} without a grant",
                detail=f"{_n(n, 'denied attempt')} in {days}. Looks like a workflow that expects access it was never given.",
            ))

    if t.expired_grant_attempts >= EXPIRED_REUSE_MIN:
        findings.append(Finding(
            code="EXPIRED_ACCESS_REUSE", severity=Severity.LOW, hypothesis=Hypothesis.LIKELY_MISCONFIGURED,
            title="Keeps using access after it decays",
            detail=f"{_n(t.expired_grant_attempts, 'attempt')} on expired grants in {days}.",
        ))

    # "Unused" means never exercised AND never even attempted. A grant the agent tried to use but was
    # blocked on (require_human, or a deny that never refreshed last_used_at) is needed, not surplus —
    # flagging it as over-privileged is wrong (rehearsal finding G3).
    unused = [
        g.scope for g in inp.grants
        if g.kind == GrantKind.BASELINE
        and (g.last_used_at is None or g.last_used_at < inp.window_start)
        and not any(any_match([g.scope], attempted) for attempted in inp.attempted_scopes)
    ]
    if unused and t.requests:
        findings.append(Finding(
            code="UNUSED_STANDING_GRANT", severity=Severity.LOW, hypothesis=Hypothesis.OVER_PRIVILEGED,
            title=f"{_n(len(unused), 'standing permission')} never used",
            detail=f"Unused in {days}: {', '.join(sorted(unused))}. Candidates for decay or removal.",
        ))

    if t.requests == 0:
        findings.append(Finding(
            code="INACTIVE", severity=Severity.LOW, hypothesis=Hypothesis.INACTIVE,
            title="No activity", detail=f"No requests in {days}. Possibly obsolete.",
        ))
    return findings


def primary_hypothesis(findings: list[Finding]) -> Hypothesis:
    present = {f.hypothesis for f in findings}
    return next((h for h in PRECEDENCE if h in present), Hypothesis.HEALTHY)
