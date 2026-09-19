from datetime import datetime, timedelta, timezone

from app.models.agent import Agent, BehaviorProfile
from app.models.common import RiskLevel, Sensitivity
from app.models.event import ReasonCode, SignalCode
from app.models.policy import GrantKind, GrantStatus, PermissionGrant, Resource, RiskPolicy, RolePolicy
from app.services.behavior.signals import SignalContext, compute_signals
from app.services.grants.rules import decay_reason
from app.services.policy.engine import evaluate_permission

NOW = datetime(2026, 9, 19, 14, 0, tzinfo=timezone.utc)
RP = RiskPolicy()
FACILITIES = RolePolicy(baseline=["building.*"], grantable=["building.*"], forbidden=["payroll.*", "patient.*"])
ANALYTICS = RolePolicy(baseline=["analytics.*"], grantable=["patient.records.read"], forbidden=["payroll.salary.*"])
PAYROLL = Resource(id="payroll-system", display_name="Payroll", scope_prefix="payroll", sensitivity=Sensitivity.CRITICAL)
EHR = Resource(id="ehr", display_name="EHR", scope_prefix="patient", sensitivity=Sensitivity.CRITICAL)
BUILDING = Resource(id="building-mgmt", display_name="BMS", scope_prefix="building", sensitivity=Sensitivity.LOW)


def grant(scope, *, kind=GrantKind.BASELINE, expires_in=None, status=GrantStatus.ACTIVE, agent="a"):
    return PermissionGrant(
        id=f"grt_{scope}", agent_id=agent, scope=scope, kind=kind, status=status,
        granted_at=NOW - timedelta(hours=1),
        expires_at=NOW + timedelta(seconds=expires_in) if expires_in is not None else None,
        granted_by="test",
    )


def agent(role="facilities", risk=8):
    return Agent(
        id="facilities-agent", display_name="FacilitiesAgent", role=role, ans_name="ans://v1.0.0.x.example",
        risk_score=risk, risk_level=RiskLevel.LOW, baseline_risk=8, risk_updated_at=NOW, peers=["scheduling-agent"],
    )


def test_baseline_grant_allows():
    r = evaluate_permission("facilities", FACILITIES, [grant("building.*")], "building.energy.read", BUILDING, NOW)
    assert r.permitted and r.reason_code == ReasonCode.ALLOWED


def test_forbidden_scope_denied_even_with_grant():
    r = evaluate_permission("facilities", FACILITIES, [grant("payroll.*")], "payroll.salary.read", PAYROLL, NOW)
    assert r.outcome == "denied" and r.reason_code == ReasonCode.FORBIDDEN_FOR_ROLE


def test_no_grant():
    r = evaluate_permission("analytics", ANALYTICS, [grant("analytics.*")], "patient.records.read", EHR, NOW)
    assert r.reason_code == ReasonCode.NO_GRANT


def test_temporary_grant_decays():
    g = grant("patient.records.read", kind=GrantKind.TEMPORARY, expires_in=30)
    assert evaluate_permission("analytics", ANALYTICS, [g], "patient.records.read", EHR, NOW).permitted
    later = NOW + timedelta(seconds=31)
    r = evaluate_permission("analytics", ANALYTICS, [g], "patient.records.read", EHR, later)
    assert r.reason_code == ReasonCode.GRANT_EXPIRED
    assert decay_reason(g, later) == ReasonCode.TTL_ELAPSED


def test_idle_timeout_decays():
    g = grant("patient.records.read", kind=GrantKind.TEMPORARY, expires_in=3600).model_copy(
        update={"idle_timeout_seconds": 60, "last_used_at": NOW - timedelta(seconds=30)}
    )
    assert decay_reason(g, NOW) is None
    assert decay_reason(g, NOW + timedelta(minutes=2)) == ReasonCode.IDLE_TIMEOUT


def test_delegation_does_not_inherit_permissions():
    """Agent B is checked against B's grants only, whoever delegated to it."""
    b_grants = [grant("analytics.*", agent="b")]
    r = evaluate_permission("analytics", ANALYTICS, b_grants, "payroll.hours.read", PAYROLL, NOW)
    assert r.outcome == "denied"


def _ctx(action, resource, perm, *, requests=1, denials=0, target=None, profile=None):
    return SignalContext(
        agent=agent(), profile=profile or BehaviorProfile(agent_id="facilities-agent"), action=action,
        resource=resource, target_agent_id=target, permission=perm,
        requests_in_window=requests, denials_in_window=denials, now=NOW,
    )


def test_compromised_request_signals():
    perm = evaluate_permission("facilities", FACILITIES, [], "payroll.salary.read", PAYROLL, NOW)
    codes = {s.code for s in compute_signals(_ctx("payroll.salary.read", PAYROLL, perm), RP)}
    assert codes == {SignalCode.FORBIDDEN_SCOPE, SignalCode.NEW_SENSITIVE_RESOURCE}


def test_granted_first_use_is_not_suspicious():
    g = grant("patient.records.read", kind=GrantKind.TEMPORARY, expires_in=30)
    perm = evaluate_permission("analytics", ANALYTICS, [g], "patient.records.read", EHR, NOW)
    assert compute_signals(_ctx("patient.records.read", EHR, perm), RP) == []


def test_rate_spike_and_cooldown():
    perm = evaluate_permission("facilities", FACILITIES, [grant("building.*")], "building.lights.read", BUILDING, NOW)
    fired = compute_signals(_ctx("building.lights.read", BUILDING, perm, requests=30), RP)
    assert [s.code for s in fired] == [SignalCode.RATE_SPIKE]
    cooling = BehaviorProfile(agent_id="facilities-agent", signal_last_fired={"RATE_SPIKE": NOW - timedelta(seconds=5)})
    assert compute_signals(_ctx("building.lights.read", BUILDING, perm, requests=31, profile=cooling), RP) == []


def test_unexpected_peer():
    perm = evaluate_permission("facilities", FACILITIES, [grant("building.*")], "building.lights.read", BUILDING, NOW)
    fired = compute_signals(_ctx("building.lights.read", BUILDING, perm, target="payroll-agent"), RP)
    assert [s.code for s in fired] == [SignalCode.UNEXPECTED_PEER]
