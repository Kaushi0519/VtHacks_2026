import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.core.ids import utcnow
from app.models.identity import IdentityResult
from app.services.ans.reference import ReferenceANSService, verifier_succeeded

NAME = "ans://v1.0.0.facilities.example.com"


def service():
    settings = Settings(ans_cache_ttl_seconds=0, ans_stale_ok_seconds=3600, ans_timeout_seconds=.01)
    world = SimpleNamespace(ans_mock_registry=[SimpleNamespace(ans_name=NAME, ans_agent_id="test-agent")])
    return ReferenceANSService(settings, lambda: world)


@pytest.mark.parametrize("badge,expected", [
    ({"status":"ACTIVE", "ansName":NAME}, True),
    ({"status":"ACTIVE"}, False),
    ({"status":"ACTIVE", "ansName":"wrong"}, False),
    ({"status":"REVOKED", "ansName":NAME}, False),
    ([], False),
    ({"status":"ACTIVE", "payload":{"producer":{"event":{"ansName":NAME}}}}, True),
    ({"status":"ACTIVE", "payload":{"producer":{"event":{"ansName":"wrong"}}}}, False),
    ({"status":"ACTIVE", "payload":{"producer":{"event":{}}}}, False),
    ({"status":"ACTIVE", "payload":[]}, False),
    ({"status":"ACTIVE", "ansName":NAME, "payload":{"producer":{"event":{"ansName":"wrong"}}}}, False),
])
def test_badge_identity_must_be_explicit(badge, expected):
    s = service()
    response = httpx.Response(200, json=badge, request=httpx.Request("GET","http://test/badge"))
    http = AsyncMock()
    http.get.return_value = response
    with patch("app.services.ans.reference.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = http
        s._crypto_verify = AsyncMock(return_value=(True,"ok"))
        result = asyncio.run(s.verify_agent(NAME))
    assert result.verified is expected


def test_stale_active_identity_cannot_authorize():
    s = service()
    s._cache[NAME] = (time.monotonic()-120, IdentityResult(ans_name=NAME, verified=True,
        ans_status="ACTIVE", source="ans", checked_at=utcnow()))
    s._verify_live = AsyncMock(side_effect=httpx.ConnectError("offline"))
    result = asyncio.run(s.verify_agent(NAME))
    assert result.stale and result.cached
    assert not result.verified
    assert result.ans_status == "UNREACHABLE"


@pytest.mark.parametrize("output,expected", [
    ("  \u2713 VERIFIED (kid ab12cd34 matched key directly)\n", True),
    ("NOT VERIFIED", False), ("UNVERIFIED", False), ("VERIFIED", False),
    ("prefix \u2713 VERIFIED (kid ab12cd34 matched key directly)", False),
])
def test_verifier_output_is_not_a_substring_match(output, expected):
    assert verifier_succeeded(output) is expected


def test_verifier_timeout_kills_and_reaps_process():
    proc = SimpleNamespace(returncode=None, communicate=AsyncMock(side_effect=[asyncio.TimeoutError(), (b"",None)]))
    from unittest.mock import Mock
    proc.kill = Mock()
    with patch("app.services.ans.reference.asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        ok, detail = asyncio.run(service()._crypto_verify("test-agent"))
    assert not ok and "timed out" in detail
    proc.kill.assert_called_once()
    assert proc.communicate.await_count == 2
