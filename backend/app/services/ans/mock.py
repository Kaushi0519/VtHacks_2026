"""MOCK ANS adapter. Clearly labeled: every result carries source="mock" and the UI shows
"ANS: MOCK". Never present this as a live GoDaddy ANS call.

Registry contents come from world.ansMockRegistry, which mirrors what we registered in real ANS
so both modes behave the same.
"""

from collections.abc import Callable
from typing import Literal

from app.core.ids import utcnow
from app.models.identity import IdentityResult
from app.models.policy import World
from app.services.ans.base import parse_ans_name


class MockANSService:
    mode: Literal["mock"] = "mock"
    base_url = None

    def __init__(self, get_world: Callable[[], World]):
        self._get_world = get_world

    async def verify_agent(self, ans_name: str) -> IdentityResult:
        now = utcnow()
        if parse_ans_name(ans_name) is None:
            return IdentityResult(
                ans_name=ans_name, verified=False, ans_status="INVALID_NAME", source="mock",
                checked_at=now, detail="Not a valid ans:// name",
            )
        entry = next((e for e in self._get_world().ans_mock_registry if e.ans_name == ans_name), None)
        if entry is None:
            return IdentityResult(
                ans_name=ans_name, verified=False, ans_status="NOT_FOUND", source="mock",
                checked_at=now, detail="Name does not resolve in the (mock) ANS registry",
            )
        return IdentityResult(
            ans_name=ans_name,
            verified=entry.status == "ACTIVE",
            ans_status=entry.status,
            source="mock",
            ans_agent_id=entry.ans_agent_id,
            checked_at=now,
            detail=None if entry.status == "ACTIVE" else f"ANS lifecycle status is {entry.status}",
        )

    async def warm_up(self, ans_names: list[str]) -> None:
        return None

    def invalidate(self, ans_name: str | None = None) -> None:
        return None
