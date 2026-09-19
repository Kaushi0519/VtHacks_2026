"""SentinelClient: the thin "SDK" an agent would embed. Every agent action goes through the gateway.

Only uses the public API documented in docs/API.md.
"""

import os
from datetime import datetime
from typing import Any

import httpx

from sentinel_sim.world import SimActor

DEFAULT_URL = os.environ.get("SENTINEL_URL", "http://localhost:8000")


class SentinelClient:
    def __init__(self, base_url: str = DEFAULT_URL, timeout: float = 15.0):
        self._http = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout)

    async def close(self) -> None:
        await self._http.aclose()

    async def request(
        self,
        actor: SimActor,
        action: str,
        *,
        target: str | None = None,
        trace_id: str | None = None,
        parent_event_id: str | None = None,
        delegation_chain: list[str] | None = None,
        observed_at: datetime | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "actorAnsName": actor.ans_name,
            "actorAgentId": actor.id,
            "action": action,
            "targetAgentId": target,
            "traceId": trace_id,
            "parentEventId": parent_event_id,
            "delegationChain": delegation_chain or [],
            "source": source,
        }
        if observed_at is not None:
            body["observedAt"] = observed_at.isoformat()
        res = await self._http.post("/api/gateway/evaluate", json=body)
        res.raise_for_status()
        return res.json()

    # --- operator actions (a human operator / automation acting through the control plane) ---

    async def grant(self, agent_id: str, scope: str, ttl_seconds: int, reason: str, granted_by: str) -> dict[str, Any]:
        res = await self._http.post(
            f"/api/agents/{agent_id}/grants",
            json={"scope": scope, "ttlSeconds": ttl_seconds, "reason": reason, "grantedBy": granted_by},
        )
        res.raise_for_status()
        return res.json()

    async def reset(self) -> None:
        (await self._http.post("/api/admin/reset")).raise_for_status()

    async def resync(self) -> None:
        (await self._http.post("/api/admin/resync")).raise_for_status()
