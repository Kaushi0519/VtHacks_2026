"""Unit tests for the deterministic finding rules (services/accountability/findings.py)."""

from datetime import datetime, timedelta, timezone

from app.models.accountability import ActivityTotals, Hypothesis
from app.models.policy import GrantKind, PermissionGrant
from app.services.accountability.findings import evaluate, FindingInput

NOW = datetime(2026, 9, 19, tzinfo=timezone.utc)
WINDOW_START = NOW - timedelta(days=7)


def _baseline_grant(scope: str) -> PermissionGrant:
    return PermissionGrant(
        id=f"g-{scope}", agent_id="payroll-agent", scope=scope, kind=GrantKind.BASELINE,
        granted_at=NOW - timedelta(days=30), granted_by="policy:role:payroll", last_used_at=None,
    )


def _inp(**kw) -> FindingInput:
    base = dict(known=True, window_days=7.0, window_start=WINDOW_START, totals=ActivityTotals(requests=5))
    base.update(kw)
    return FindingInput(**base)


def _codes(inp: FindingInput) -> set[str]:
    return {f.code for f in evaluate(inp)}


def test_unused_standing_grant_flagged_when_never_touched():
    """A baseline grant the agent never used and never attempted is genuinely surplus."""
    inp = _inp(grants=[_baseline_grant("payroll.salary.write")], attempted_scopes=set())
    assert "UNUSED_STANDING_GRANT" in _codes(inp)


def test_attempted_but_blocked_grant_is_not_unused():
    """G3: a grant the agent tried to use but was blocked on (require_human never sets last_used_at)
    is needed, not over-privileged, and must not be flagged."""
    inp = _inp(
        grants=[_baseline_grant("payroll.salary.write")],
        attempted_scopes={"payroll.salary.write"},
    )
    assert "UNUSED_STANDING_GRANT" not in _codes(inp)


def test_attempt_matches_grant_pattern():
    """A wildcard baseline grant is 'needed' if any attempted scope matches its pattern."""
    inp = _inp(
        grants=[_baseline_grant("payroll.salary.*")],
        attempted_scopes={"payroll.salary.write"},
    )
    assert "UNUSED_STANDING_GRANT" not in _codes(inp)
