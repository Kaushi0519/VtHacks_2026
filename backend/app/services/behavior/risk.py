"""Behavioral Risk Score arithmetic. Owner: Person 3.

Transparent heuristic, not a trained model: score = previous (cooled) score + signal weights,
clamped to 0..100. It decays back toward the agent's baseline while it behaves (except when
quarantined, where it freezes until an operator releases the agent).
"""

from datetime import datetime

from app.models.agent import Agent, AgentStatus
from app.models.common import RiskLevel
from app.models.event import RiskSignal
from app.models.policy import RiskPolicy


def level_for(score: int, rp: RiskPolicy) -> RiskLevel:
    if score >= rp.threshold_critical:
        return RiskLevel.CRITICAL
    if score >= rp.threshold_high:
        return RiskLevel.HIGH
    if score >= rp.threshold_elevated:
        return RiskLevel.ELEVATED
    return RiskLevel.LOW


def cooled_score(agent: Agent, now: datetime, rp: RiskPolicy) -> int:
    if agent.status == AgentStatus.QUARANTINED or agent.risk_score <= agent.baseline_risk:
        return agent.risk_score
    minutes = max(0.0, (now - agent.risk_updated_at).total_seconds() / 60)
    return max(agent.baseline_risk, round(agent.risk_score - minutes * rp.cooldown_per_minute))


def apply_signals(before: int, signals: list[RiskSignal]) -> int:
    return max(0, min(100, before + sum(s.weight for s in signals)))
