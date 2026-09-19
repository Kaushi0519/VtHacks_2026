"""Behavior profile updates. Owner: Person 3.

learn() is only called for ALLOWED requests so an attacker can't train the baseline by
repeating forbidden requests (baseline poisoning).
"""

from datetime import datetime

from app.models.agent import BehaviorProfile
from app.models.event import RiskSignal


def learn(
    profile: BehaviorProfile, action: str, resource_id: str | None, target_agent_id: str | None, now: datetime
) -> BehaviorProfile:
    scopes = dict(profile.scope_counts)
    scopes[action] = scopes.get(action, 0) + 1
    resources = dict(profile.resource_counts)
    if resource_id:
        resources[resource_id] = resources.get(resource_id, 0) + 1
    peers = dict(profile.peer_counts)
    if target_agent_id:
        peers[target_agent_id] = peers.get(target_agent_id, 0) + 1
    return profile.model_copy(
        update={"scope_counts": scopes, "resource_counts": resources, "peer_counts": peers, "updated_at": now}
    )


def mark_fired(profile: BehaviorProfile, signals: list[RiskSignal], now: datetime) -> BehaviorProfile:
    if not signals:
        return profile
    fired = dict(profile.signal_last_fired)
    for s in signals:
        fired[s.code.value] = now
    return profile.model_copy(update={"signal_last_fired": fired, "updated_at": now})
