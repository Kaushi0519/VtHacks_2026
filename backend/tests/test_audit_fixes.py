"""Regression tests for the audit fixes (grant usage, audit completeness, operator auth, SSE)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models.system import StreamType
from app.realtime.broadcaster import Broadcaster


@pytest.fixture
def secured_client(tmp_path, monkeypatch):
    """Same app but with OPERATOR_TOKEN set, to exercise the operator-auth guard."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ANS_MODE", "mock")
    monkeypatch.setenv("GEMINI_MODE", "mock")
    monkeypatch.setenv("ALLOW_BACKFILL", "true")
    monkeypatch.setenv("OPERATOR_TOKEN", "s3cret")
    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def _agents(client) -> dict[str, dict]:
    return {a["id"]: a for a in client.get("/api/agents").json()}


def _use_count_sum(client, agent_id: str) -> int:
    return sum(g["useCount"] for g in client.get(f"/api/agents/{agent_id}/grants").json())


def test_allow_via_grant_records_grant_id_and_counts_use(client):
    """An allowed request authorized by a grant records the grantId and increments its use."""
    ans = _agents(client)["analytics-agent"]["ansName"]
    grant = client.post(
        "/api/agents/analytics-agent/grants", json={"scope": "patient.records.read", "ttlSeconds": 60}
    ).json()
    before = _use_count_sum(client, "analytics-agent")

    decision = client.post(
        "/api/gateway/evaluate", json={"actorAnsName": ans, "action": "patient.records.read"}
    ).json()
    assert decision["decision"] == "allow"

    # the request event carries the grant that authorized it (audit completeness)
    events = client.get("/api/events", params={"agentId": "analytics-agent", "decision": "allow"}).json()["items"]
    assert any(e.get("grantId") == grant["id"] for e in events)
    # and the grant's usage was counted exactly once
    assert _use_count_sum(client, "analytics-agent") == before + 1


def test_require_human_does_not_touch_grant(client):
    """A require_human decision executed nothing, so it must not refresh grant usage/idle timers."""
    ans = _agents(client)["payroll-agent"]["ansName"]
    before = _use_count_sum(client, "payroll-agent")

    decision = client.post(
        "/api/gateway/evaluate", json={"actorAnsName": ans, "action": "payroll.salary.write"}
    ).json()
    assert decision["decision"] == "require_human"

    assert _use_count_sum(client, "payroll-agent") == before  # unchanged


def test_report_for_unknown_id_is_404(client):
    """An id with no enrolled agent AND no activity is a 404, not a fake UNVERIFIED_IDENTITY finding."""
    assert client.get("/api/accountability/agents/does-not-exist").status_code == 404


def test_granted_by_is_set_server_side(client):
    """A client-supplied grantedBy is ignored; attribution comes from the server principal."""
    grant = client.post(
        "/api/agents/analytics-agent/grants",
        json={"scope": "patient.records.read", "ttlSeconds": 60, "grantedBy": "attacker"},
    ).json()
    assert grant["grantedBy"] == "operator"


def test_operator_routes_open_by_default(client):
    """With OPERATOR_TOKEN unset (local demo), operator/admin routes are open."""
    assert client.post("/api/admin/resync").status_code == 200


def test_operator_routes_require_token_when_set(secured_client):
    assert secured_client.post("/api/admin/reset").status_code == 401
    assert secured_client.post("/api/admin/reset", headers={"X-Operator-Token": "nope"}).status_code == 401
    assert secured_client.post("/api/admin/reset", headers={"X-Operator-Token": "s3cret"}).status_code == 200


def test_sse_overflow_forces_resync_not_silent_drop():
    """A slow subscriber gets a resync (recoverable) instead of being silently stranded."""
    b = Broadcaster(queue_size=1)
    q = b.subscribe()
    b.publish(StreamType.AGENT, {"x": 1})  # fills the queue
    b.publish(StreamType.AGENT, {"x": 2})  # overflow -> drain + resync

    last = None
    while not q.empty():
        last = json.loads(q.get_nowait())
    assert last is not None and last["type"] == StreamType.RESYNC.value
    assert q in b._subscribers  # still connected, just told to refetch
