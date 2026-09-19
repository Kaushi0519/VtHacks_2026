"""REAL GoDaddy ANS adapter. Owner: Person 3.

Endpoints come from GoDaddy's published ANS OpenAPI spec (developer.godaddy.com ->
REST API reference -> ANS; base https://api.godaddy.com), researched 2026-09-19:

    POST /v1/agents/resolution   body {agentHost, version}
         200 -> {ansName, links: [{rel: "agent-details", href: ".../v1/agents/{agentId}"}, ...]}
         404 -> agent not found
    GET  /v1/agents/{agentId}    200 -> AgentDetails {agentId, ansName, agentStatus, ...}
         agentStatus in PENDING_VALIDATION | PENDING_DNS | ACTIVE | FAILED | EXPIRED | REVOKED

TODO(P3, P0): verify against the live API with our key before trusting this in the demo:
  - auth header format for the ANS PAT (Bearer assumed; ANS_AUTH_SCHEME=sso-key also supported)
  - whether GET /v1/agents/{id} is ownership-scoped (404 for agents we don't own). If so, fall
    back to GET /v1/ans/registered-agents/{agentId} (registered-agents search service).
Do not add endpoints here that aren't in GoDaddy's docs.
"""

import logging
import time
from typing import Literal

import httpx

from app.core.config import Settings
from app.core.ids import utcnow
from app.models.identity import IdentityResult
from app.services.ans.base import parse_ans_name

log = logging.getLogger("sentinel.ans")


class GoDaddyANSService:
    mode: Literal["real"] = "real"

    def __init__(self, settings: Settings):
        self.base_url = settings.ans_base_url.rstrip("/")
        self._timeout = settings.ans_timeout_seconds
        self._ttl = settings.ans_cache_ttl_seconds
        self._stale_ok = settings.ans_stale_ok_seconds
        self._headers = {"Accept": "application/json"}
        if settings.ans_api_key:
            scheme = "sso-key" if settings.ans_auth_scheme == "sso-key" else "Bearer"
            self._headers["Authorization"] = f"{scheme} {settings.ans_api_key}"
        else:
            log.warning("ANS_MODE=real but ANS_API_KEY is empty; calls will likely fail")
        # ans_name -> (monotonic time stored, result)
        self._cache: dict[str, tuple[float, IdentityResult]] = {}

    async def verify_agent(self, ans_name: str) -> IdentityResult:
        cached = self._cache.get(ans_name)
        age = time.monotonic() - cached[0] if cached else None
        if cached and age is not None and age < self._ttl:
            return cached[1].model_copy(update={"cached": True})

        try:
            result = await self._verify_live(ans_name)
        except (httpx.HTTPError, ValueError) as exc:
            log.warning("ANS unreachable for %s: %s", ans_name, exc)
            if cached and age is not None and age < self._stale_ok:
                # Still a real ANS answer, just not fresh. Flagged so the UI can say so.
                return cached[1].model_copy(update={"cached": True, "stale": True})
            return IdentityResult(
                ans_name=ans_name, verified=False, ans_status="UNREACHABLE", source="ans",
                checked_at=utcnow(), detail=f"ANS unreachable: {type(exc).__name__}",
            )

        self._cache[ans_name] = (time.monotonic(), result)
        return result

    async def _verify_live(self, ans_name: str) -> IdentityResult:
        now = utcnow()
        parsed = parse_ans_name(ans_name)
        if parsed is None:
            return IdentityResult(
                ans_name=ans_name, verified=False, ans_status="INVALID_NAME", source="ans",
                checked_at=now, detail="Not a valid ans:// name",
            )
        version, host = parsed
        async with httpx.AsyncClient(base_url=self.base_url, headers=self._headers, timeout=self._timeout) as http:
            res = await http.post("/v1/agents/resolution", json={"agentHost": host, "version": version})
            if res.status_code == 404:
                return IdentityResult(
                    ans_name=ans_name, verified=False, ans_status="NOT_FOUND", source="ans",
                    checked_at=now, detail="Name does not resolve in ANS",
                )
            res.raise_for_status()
            resolved = res.json()
            agent_id = _agent_id_from_links(resolved.get("links", []))
            if agent_id is None:
                raise ValueError("resolution response had no agent-details link")

            details = await http.get(f"/v1/agents/{agent_id}")
            details.raise_for_status()
            body = details.json()

        status = str(body.get("agentStatus", "UNKNOWN"))
        name_matches = body.get("ansName", resolved.get("ansName")) == ans_name
        verified = status == "ACTIVE" and name_matches
        detail = None
        if not name_matches:
            detail = f"ANS resolved to {body.get('ansName')!r}, not the claimed name"
        elif status != "ACTIVE":
            detail = f"ANS lifecycle status is {status}"
        return IdentityResult(
            ans_name=ans_name, verified=verified, ans_status=status, source="ans",
            ans_agent_id=agent_id, checked_at=now, detail=detail,
        )

    async def warm_up(self, ans_names: list[str]) -> None:
        for name in ans_names:
            result = await self.verify_agent(name)
            log.info("ANS warm-up %s -> %s (verified=%s)", name, result.ans_status, result.verified)

    def invalidate(self, ans_name: str | None = None) -> None:
        if ans_name is None:
            self._cache.clear()
        else:
            self._cache.pop(ans_name, None)


def _agent_id_from_links(links: list[dict]) -> str | None:
    for link in links:
        if link.get("rel") == "agent-details" and link.get("href"):
            return link["href"].rstrip("/").rsplit("/", 1)[-1]
    return None
