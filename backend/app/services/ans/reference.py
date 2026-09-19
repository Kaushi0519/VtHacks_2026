"""REAL ANS adapter — talks to the ANS reference implementation. Owner: Person 3.

The earlier "api.godaddy.com" REST path was a wrong assumption. Real ANS is the open reference
implementation (github.com/agentnameservice/ans), which we run locally (see docs/ANS.md):

    ans-ra  :18080   Registration Authority — registration, identity certs, lifecycle
    ans-tl  :18081   Transparency Log       — agent badge + SCITT COSE_Sign1 receipts (public read)
    ans-verify (CLI)                        — offline cryptographic verification of a receipt

What verify_agent actually does for a claimed ans:// name:
  1. resolve name -> agentId          (registry mapping seeded at registration, from world.yaml)
  2. GET {tl}/v1/agents/{agentId}     -> badge; read lifecycle `status`   (public read, no auth)
  3. ans-verify -url {tl} -agent {id} -> Merkle-inclusion + ES256 receipt check (the real ANS proof)
  verified == (status == ACTIVE) AND (name matches) AND (receipt cryptographically VERIFIED)

Registration is a SETUP step done with the reference impl's own tooling (docs/ANS.md), not at
runtime. Once agents are registered, put each real agentId in world.yaml's ansMockRegistry entry.

Key facts from the authoritative ANS v2 OpenAPI spec:
  - REST name resolution was REMOVED in v2 (`POST /v1/agents/resolution` is gone). Resolution is now
    via the agent's `_ans` DNS TXT record. Our world-registry map is the MVP stand-in; the reference
    impl ships `ans-dns` for local `_ans` lookups if we want true DNS resolution later.
  - The RA management API (`GET /ans/agents/{id}`, base `.../v2`, Bearer) is OWNER-SCOPED — it 404s for
    agents you don't own, so it CANNOT verify impostors/external agents. We deliberately read the
    public Transparency Log instead (`GET {tl}/v1/agents/{id}` + `GET /v1/agents/events`, no auth).

TODO(P3, P0) — confirm against the running stack's Swagger (`/docs`) before the demo:
  - the TL badge shape and the JSON key that holds lifecycle status (assumed `status`)
  - the exact `ans-verify` success string (assumed a line containing "VERIFIED")
  - optionally resolve via the `_ans` DNS TXT record instead of the seeded map (see `ans-dns`)
Do not invent endpoints that aren't in the ANS docs.
"""

import asyncio
import logging
import re
import time
from collections.abc import Callable
from typing import Literal

import httpx

from app.core.config import Settings
from app.core.ids import utcnow
from app.models.identity import IdentityResult
from app.models.policy import World
from app.services.ans.base import parse_ans_name

log = logging.getLogger("sentinel.ans")


class ReferenceANSService:
    mode: Literal["real"] = "real"

    def __init__(self, settings: Settings, get_world: Callable[[], World]):
        self._get_world = get_world
        self.base_url = settings.ans_tl_url.rstrip("/")  # shown in SystemStatus.ans_base_url
        self._tl_url = settings.ans_tl_url.rstrip("/")
        self._verify_bin = settings.ans_verify_bin
        self._timeout = settings.ans_timeout_seconds
        self._ttl = settings.ans_cache_ttl_seconds
        self._stale_ok = settings.ans_stale_ok_seconds
        # ans_name -> (monotonic time stored, result)
        self._cache: dict[str, tuple[float, IdentityResult]] = {}

    async def verify_agent(self, ans_name: str) -> IdentityResult:
        cached = self._cache.get(ans_name)
        age = time.monotonic() - cached[0] if cached else None
        if cached and age is not None and age < self._ttl:
            return cached[1].model_copy(update={"cached": True})

        try:
            result = await self._verify_live(ans_name)
        except (httpx.HTTPError, ValueError, OSError) as exc:
            log.warning("ANS TL unreachable for %s: %s", ans_name, exc)
            if cached and age is not None and age < self._stale_ok:
                # Still a real ANS answer, just not fresh. Flagged so the UI can say so.
                return cached[1].model_copy(update={
                    "cached": True, "stale": True, "verified": False, "ans_status": "UNREACHABLE",
                    "detail": "Cached identity is stale; current lifecycle could not be verified",
                })
            return IdentityResult(
                ans_name=ans_name, verified=False, ans_status="UNREACHABLE", source="ans",
                checked_at=utcnow(), detail=f"ANS Transparency Log unreachable: {type(exc).__name__}",
            )

        self._cache[ans_name] = (time.monotonic(), result)
        return result

    async def _verify_live(self, ans_name: str) -> IdentityResult:
        now = utcnow()
        if parse_ans_name(ans_name) is None:
            return IdentityResult(
                ans_name=ans_name, verified=False, ans_status="INVALID_NAME", source="ans",
                checked_at=now, detail="Not a valid ans:// name",
            )

        agent_id = self._resolve_agent_id(ans_name)
        if agent_id is None:
            return IdentityResult(
                ans_name=ans_name, verified=False, ans_status="NOT_FOUND", source="ans",
                checked_at=now, detail="Name does not resolve to a registered ANS agent",
            )

        # 2. Transparency Log badge -> lifecycle status (public read, no auth).
        async with httpx.AsyncClient(base_url=self._tl_url, timeout=self._timeout) as http:
            res = await http.get(f"/v1/agents/{agent_id}", headers={"Accept": "application/json"})
            if res.status_code == 404:
                return IdentityResult(
                    ans_name=ans_name, verified=False, ans_status="NOT_FOUND", source="ans",
                    ans_agent_id=agent_id, checked_at=now,
                    detail="Agent id not present in the Transparency Log",
                )
            res.raise_for_status()
            badge = res.json()
            if not isinstance(badge, dict):
                raise ValueError("ANS badge must be a JSON object")

        status = str(badge.get("status", "UNKNOWN"))
        badge_name = badge.get("ansName") or badge.get("ans_name")
        name_matches = isinstance(badge_name, str) and badge_name == ans_name

        # 3. Cryptographic receipt verification via the official offline verifier.
        tl_verified, verify_detail = await self._crypto_verify(agent_id)

        verified = status == "ACTIVE" and name_matches and tl_verified
        detail = None
        if not name_matches:
            detail = f"ANS badge is for {badge_name!r}, not the claimed name"
        elif status != "ACTIVE":
            detail = f"ANS lifecycle status is {status}"
        elif not tl_verified:
            detail = f"Transparency-log receipt did not verify: {verify_detail}"

        return IdentityResult(
            ans_name=ans_name, verified=verified, ans_status=status, source="ans",
            ans_agent_id=agent_id, tl_verified=tl_verified, checked_at=now, detail=detail,
        )

    def _resolve_agent_id(self, ans_name: str) -> str | None:
        """Map an ans:// name to its ANS agentId. Seeded from world.yaml's registry (filled with the
        real agentIds after registration). ANS v2 removed REST resolution; the production-correct path
        is the agent's `_ans` DNS TXT record (reference impl: `ans-dns`). Map is the MVP stand-in."""
        entry = next((e for e in self._get_world().ans_mock_registry if e.ans_name == ans_name), None)
        return entry.ans_agent_id if entry else None

    async def _crypto_verify(self, agent_id: str) -> tuple[bool, str]:
        """Run `ans-verify -url {tl} -agent {id}`; success is exit 0 with a VERIFIED line."""
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                self._verify_bin, "-url", self._tl_url, "-agent", agent_id,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            )
            raw, _ = await asyncio.wait_for(proc.communicate(), timeout=self._timeout)
            text = raw.decode(errors="replace")
            if proc.returncode == 0 and verifier_succeeded(text):
                return True, "ok"
            last = text.strip().splitlines()[-1] if text.strip() else f"exit {proc.returncode}"
            return False, last[:200]
        except FileNotFoundError:
            log.warning("ans-verify binary %r not found; cannot do crypto verification", self._verify_bin)
            return False, f"ans-verify binary not found ({self._verify_bin})"
        except asyncio.TimeoutError:
            return False, "ans-verify timed out"
        finally:
            # Timeout/cancellation must not leave a verifier running in the background.
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                await proc.communicate()

    async def warm_up(self, ans_names: list[str]) -> None:
        for name in ans_names:
            result = await self.verify_agent(name)
            log.info("ANS warm-up %s -> %s (verified=%s)", name, result.ans_status, result.verified)

    def invalidate(self, ans_name: str | None = None) -> None:
        if ans_name is None:
            self._cache.clear()
        else:
            self._cache.pop(ans_name, None)


def verifier_succeeded(output: str) -> bool:
    """Accept the exact success line documented in agentnameservice/ans README.

    Unknown output formats fail closed and must be validated before adding support.
    https://github.com/agentnameservice/ans/blob/main/README.md
    """
    return any(re.fullmatch(
        r"\u2713 VERIFIED \(kid [0-9a-fA-F]{8} matched key directly\)", line.strip()
    ) for line in output.splitlines())
