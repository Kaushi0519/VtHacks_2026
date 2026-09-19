"""Behavioral signals: what about this request is abnormal for THIS agent? Owner: Person 3.

Pure function. The gateway gathers context (profile, window counts) and passes it in.
Every signal must carry a human-readable detail: we always need to answer "why?".
"""

from dataclasses import dataclass
from datetime import datetime

from app.models.agent import Agent, BehaviorProfile
from app.models.common import Sensitivity
from app.models.event import ReasonCode, RiskSignal, SignalCode
from app.models.policy import Resource, RiskPolicy
from app.services.policy.engine import PermissionResult

SENSITIVE = {Sensitivity.HIGH, Sensitivity.CRITICAL}


@dataclass(frozen=True)
class SignalContext:
    agent: Agent
    profile: BehaviorProfile
    action: str
    resource: Resource | None
    target_agent_id: str | None
    permission: PermissionResult
    requests_in_window: int  # including this request
    denials_in_window: int  # excluding this request
    now: datetime


def _on_cooldown(ctx: SignalContext, code: SignalCode, rp: RiskPolicy) -> bool:
    last = ctx.profile.signal_last_fired.get(code.value)
    return last is not None and (ctx.now - last).total_seconds() < rp.signal_cooldown_seconds


def compute_signals(ctx: SignalContext, rp: RiskPolicy) -> list[RiskSignal]:
    signals: list[RiskSignal] = []
    res = ctx.resource
    perm = ctx.permission

    if perm.reason_code == ReasonCode.FORBIDDEN_FOR_ROLE:
        signals.append(RiskSignal(
            code=SignalCode.FORBIDDEN_SCOPE, weight=rp.weight_forbidden_scope,
            detail=f"{ctx.action} is outside the {ctx.agent.role} role",
        ))

    # Reaching for a sensitive resource it has never used AND holds no grant for.
    # (A legitimately granted first use of a JIT grant is expected, not suspicious.)
    if (
        res is not None
        and res.sensitivity in SENSITIVE
        and ctx.profile.resource_counts.get(res.id, 0) == 0
        and perm.grant is None
        and not _on_cooldown(ctx, SignalCode.NEW_SENSITIVE_RESOURCE, rp)
    ):
        signals.append(RiskSignal(
            code=SignalCode.NEW_SENSITIVE_RESOURCE, weight=rp.weight_new_sensitive_resource,
            detail=f"Reached for {res.sensitivity.value}-sensitivity {res.display_name}, never used before and not granted",
        ))

    if res is not None and res.honeypot:
        signals.append(RiskSignal(
            code=SignalCode.HONEYPOT_ACCESS, weight=rp.weight_honeypot,
            detail=f"Touched deception resource {res.display_name}",
        ))

    spike_limit = max(
        rp.rate_spike_min_requests,
        round(ctx.agent.expected_rpm * rp.rate_spike_multiplier * rp.rate_window_seconds / 60),
    )
    if ctx.requests_in_window > spike_limit and not _on_cooldown(ctx, SignalCode.RATE_SPIKE, rp):
        signals.append(RiskSignal(
            code=SignalCode.RATE_SPIKE, weight=rp.weight_rate_spike,
            detail=f"{ctx.requests_in_window} requests in {rp.rate_window_seconds}s (normal ~{ctx.agent.expected_rpm}/min)",
        ))

    if (
        ctx.target_agent_id
        and ctx.target_agent_id not in ctx.agent.peers
        and ctx.profile.peer_counts.get(ctx.target_agent_id, 0) == 0
        and not _on_cooldown(ctx, SignalCode.UNEXPECTED_PEER, rp)
    ):
        signals.append(RiskSignal(
            code=SignalCode.UNEXPECTED_PEER, weight=rp.weight_unexpected_peer,
            detail=f"Never communicated with {ctx.target_agent_id} before",
        ))

    if (
        perm.outcome == "denied"
        and ctx.denials_in_window + 1 >= rp.repeated_denials_threshold
        and not _on_cooldown(ctx, SignalCode.REPEATED_DENIALS, rp)
    ):
        signals.append(RiskSignal(
            code=SignalCode.REPEATED_DENIALS, weight=rp.weight_repeated_denials,
            detail=f"{ctx.denials_in_window + 1} denied requests in {rp.repeated_denials_window_seconds // 60} min",
        ))

    if perm.reason_code == ReasonCode.GRANT_EXPIRED:
        signals.append(RiskSignal(
            code=SignalCode.EXPIRED_GRANT_USE, weight=rp.weight_expired_grant_use,
            detail=f"Tried to use decayed access to {ctx.action}",
        ))

    return signals
