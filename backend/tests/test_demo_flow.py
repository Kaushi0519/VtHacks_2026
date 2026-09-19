"""The demo story, end to end through the real HTTP API (mock ANS, rule-based analyzer)."""

import time
from datetime import datetime, timedelta, timezone

import pytest

ANS = "ans://v1.0.0.{}.demo-hospital.example"


def ask(client, agent, action, **extra):
    body = {"actorAnsName": ANS.format(agent), "action": action, **extra}
    res = client.post("/api/gateway/evaluate", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def wait_for(fn, timeout=4.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(0.1)
    raise AssertionError("condition not met in time")


def test_normal_request_allowed(client):
    d = ask(client, "facilities", "building.energy.read")
    assert d["decision"] == "allow"
    assert d["identity"]["verified"] is True and d["identity"]["source"] == "mock"
    assert d["riskAfter"] == d["riskBefore"]


def test_fake_agent_denied_on_identity(client):
    res = client.post("/api/gateway/evaluate", json={
        "actorAnsName": "ans://v1.0.0.payroll-sync.unknown-vendor.example",
        "actorAgentId": "payroll-sync-bot",
        "action": "payroll.salary.read",
    }).json()
    assert res["decision"] == "deny" and res["reasonCode"] == "IDENTITY_UNVERIFIED"
    assert res["identity"]["ansStatus"] == "NOT_FOUND"
    assert res["incidentId"]


def test_real_ans_agent_not_enrolled(client):
    res = client.post("/api/gateway/evaluate", json={
        "actorAnsName": "ans://v1.0.0.courier.partner-clinic.example", "action": "patient.records.read",
    }).json()
    assert res["reasonCode"] == "AGENT_NOT_ENROLLED" and res["identity"]["verified"] is True


def test_compromised_agent_is_quarantined(client):
    assert ask(client, "facilities", "building.energy.read")["decision"] == "allow"
    # expectedRpm 6 x multiplier 3 = 18/min before RATE_SPIKE fires
    burst = [ask(client, "facilities", "building.lights.read") for _ in range(20)]
    assert all(d["decision"] == "allow" for d in burst)
    assert burst[-1]["riskAfter"] > burst[0]["riskBefore"]

    salary = ask(client, "facilities", "payroll.salary.read")
    assert salary["decision"] == "deny" and salary["reasonCode"] == "FORBIDDEN_FOR_ROLE"
    assert salary["identity"]["verified"] is True  # identity fine, behavior not
    assert salary["riskLevel"] in ("high", "elevated")

    records = ask(client, "facilities", "patient.records.read")
    assert records["decision"] == "quarantine" and records["agentStatus"] == "quarantined"

    after = ask(client, "facilities", "building.lights.write")  # even its normal job
    assert after["decision"] == "deny" and after["reasonCode"] == "AGENT_QUARANTINED"

    incident_id = records["incidentId"]
    incident = wait_for(lambda: (i := client.get(f"/api/incidents/{incident_id}").json())["incident"]["analysis"] and i)
    assert incident["incident"]["quarantined"] is True
    assert incident["incident"]["analysis"]["source"] == "fallback"
    kinds = [e["kind"] for e in incident["events"]]
    assert "quarantine" in kinds and "analysis" in kinds

    released = client.post("/api/agents/facilities-agent/release", json={"note": "test"}).json()
    assert released["status"] == "active"
    assert ask(client, "facilities", "building.lights.write")["decision"] == "allow"


def test_permission_decay(client):
    denied = ask(client, "analytics", "patient.records.read")
    assert denied["reasonCode"] == "NO_GRANT"

    forbidden = client.post("/api/agents/analytics-agent/grants", json={"scope": "payroll.salary.read", "ttlSeconds": 60})
    assert forbidden.status_code == 403

    g = client.post("/api/agents/analytics-agent/grants", json={
        "scope": "patient.records.read", "ttlSeconds": 1, "reason": "monthly report",
    })
    assert g.status_code == 201
    grant = g.json()
    assert grant["kind"] == "temporary" and grant["expiresAt"]

    ok = ask(client, "analytics", "patient.records.read")
    assert ok["decision"] == "allow" and ok["riskAfter"] == ok["riskBefore"]

    time.sleep(1.2)
    expired = ask(client, "analytics", "patient.records.read")
    assert expired["decision"] == "deny" and expired["reasonCode"] == "GRANT_EXPIRED"

    wait_for(lambda: any(
        x["id"] == grant["id"] and x["status"] == "expired" for x in client.get("/api/grants").json()
    ))
    kinds = [e["kind"] for e in client.get("/api/events", params={"agentId": "analytics-agent"}).json()["items"]]
    assert "grant_issued" in kinds and "grant_expired" in kinds


def test_accountability_overview(client):
    for _ in range(3):
        ask(client, "scheduling", "payroll.hours.write")  # grantable but never granted
    ask(client, "facilities", "payroll.salary.read")
    ask(client, "facilities", "patient.records.read")
    client.post("/api/gateway/evaluate", json={
        "actorAnsName": "ans://v1.0.0.payroll-sync.unknown-vendor.example", "actorAgentId": "payroll-sync-bot",
        "action": "payroll.salary.read",
    })

    ov = client.get("/api/accountability/overview", params={"days": 7}).json()
    by_id = {r["agentId"]: r for r in ov["agents"]}
    assert by_id["facilities-agent"]["hypothesis"] == "possibly_compromised"
    assert by_id["scheduling-agent"]["hypothesis"] == "likely_misconfigured"
    assert [u["agentId"] for u in ov["unknownActors"]] == ["payroll-sync-bot"]
    assert ov["unknownActors"][0]["hypothesis"] == "unverified_identity"

    report = client.get("/api/accountability/agents/scheduling-agent").json()
    assert report["denialsByReason"]["NO_GRANT"] == 3
    assert any(f["code"] == "REPEATED_NO_GRANT" for f in report["findings"])


def test_backfill_uses_observed_time(client):
    past = datetime.now(timezone.utc) - timedelta(days=3)
    d = ask(client, "payroll", "payroll.salary.read", observedAt=past.isoformat())
    assert d["decision"] == "allow"
    events = client.get("/api/events", params={"agentId": "payroll-agent"}).json()["items"]
    assert events[0]["metadata"]["backfill"] is True
    assert events[0]["timestamp"].startswith(past.date().isoformat())


@pytest.mark.parametrize("forbidden_requests", [0, 1, 2])
def test_manual_quarantine_does_not_invent_repeated_out_of_role_requests(client, forbidden_requests):
    assert ask(client, "facilities", "building.energy.read")["decision"] == "allow"
    for _ in range(forbidden_requests):
        ask(client, "facilities", "payroll.salary.read")
    response = client.post("/api/agents/facilities-agent/quarantine", json={"reason": "Operator maintenance check"})
    assert response.status_code == 200
    assert response.json()["status"] == "quarantined"

    def check_report():
        report = client.get("/api/accountability/agents/facilities-agent").json()
        overview = client.get("/api/accountability/overview").json()
        row = next(a for a in overview["agents"] if a["agentId"] == "facilities-agent")
        for item in (report, row):
            assert item["totals"]["quarantines"] >= 1
            findings = [f for f in item["findings"] if f["code"] == "REPEATED_OUT_OF_ROLE"]
            assert bool(findings) == (forbidden_requests >= 2)
            if forbidden_requests < 2:
                assert item["hypothesis"] != "possibly_compromised"
            else:
                assert item["hypothesis"] == "possibly_compromised"

    check_report()
    released = client.post("/api/agents/facilities-agent/release", json={"note": "Maintenance complete"})
    assert released.status_code == 200
    assert released.json()["status"] == "active"
    check_report()


def test_snapshot_shape(client):
    snap = client.get("/api/snapshot").json()
    assert {"system", "agents", "resources", "graph", "grants", "incidents", "events", "lastSeq"} <= snap.keys()
    assert snap["system"]["ansMode"] == "mock"
    assert len(snap["agents"]) == 5
    assert any(e["kind"] == "access" for e in snap["graph"]["edges"])
