"""Final enforcement decision. Owner: Person 3.

Deterministic and explainable. Gemini output never reaches this function directly; at most it
contributes a bounded, validated AI_ASSESSMENT signal (P1) to the risk score.
"""

from app.models.common import Decision
from app.models.event import ReasonCode
from app.models.policy import RiskPolicy
from app.services.policy.engine import PermissionResult


def decide(perm: PermissionResult, risk_after: int, rp: RiskPolicy) -> tuple[Decision, ReasonCode, str]:
    if risk_after >= rp.threshold_critical:
        return (
            Decision.QUARANTINE,
            ReasonCode.RISK_THRESHOLD,
            f"Behavioral risk {risk_after} reached the quarantine threshold ({rp.threshold_critical}). "
            f"Permission check: {perm.reason}",
        )
    if perm.outcome == "denied":
        return Decision.DENY, perm.reason_code, perm.reason
    if perm.outcome == "require_human":
        return Decision.REQUIRE_HUMAN, perm.reason_code, perm.reason
    # TODO(P3, P1): HIGH risk + high/critical-sensitivity resource -> REQUIRE_HUMAN ("restrict").
    return Decision.ALLOW, perm.reason_code, perm.reason
