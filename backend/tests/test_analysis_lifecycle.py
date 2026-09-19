"""Regression coverage uses fake Gemini responses, never live API calls."""
import asyncio
import pytest
from app.core.ids import utcnow
from app.models.incident import BehaviorAnalysis


def critical():
    return BehaviorAnalysis(anomaly_type="other", severity="critical", confidence=.99,
        reason="Suspicious task deviation", recommended_action="quarantine", source="gemini", analyzed_at=utcnow())


def drain(client):
    async def wait():
        await asyncio.gather(*list(client.app.state.container.analysis._tasks))
    client.portal.call(wait)


def test_unknown_caller_gets_analysis(client):
    result = client.post("/api/gateway/evaluate", json={"actorAnsName":"ans://v1.0.0.fake.unknown.example",
        "actorAgentId":"fake-agent", "action":"payroll.salary.read"}).json()
    drain(client)
    incident = client.get("/api/incidents/" + result["incidentId"]).json()["incident"]
    assert incident["analysisStatus"] == "done"
    assert incident["analysis"]["source"] == "fallback"


@pytest.mark.parametrize("operation", ["reset", "release"])
def test_old_semantic_result_cannot_quarantine_after_operator_change(client, operation):
    c = client.app.state.container
    async def launch():
        entered, finish = asyncio.Event(), asyncio.Event()
        async def delayed(telemetry):
            entered.set()
            await finish.wait()
            return critical()
        c.analyzer.analyze_incident = delayed
        c.analysis.schedule_review("analytics-agent")
        await entered.wait()
        return finish
    finish = client.portal.call(launch)
    if operation == "reset":
        assert client.post("/api/admin/reset").status_code == 200
    else:
        client.post("/api/agents/analytics-agent/quarantine", json={"reason":"Maintenance"})
        assert client.post("/api/agents/analytics-agent/release", json={"note":"Reviewed"}).status_code == 200
    async def complete():
        finish.set()
        await asyncio.gather(*list(c.analysis._tasks))
    client.portal.call(complete)
    agent = client.get("/api/agents/analytics-agent").json()["agent"]
    assert agent["status"] == "active"
    assert agent["riskScore"] == 9
    events = client.get("/api/events", params={"agentId":"analytics-agent"}).json()["items"]
    assert not any(e["reasonCode"] == "AI_SEMANTIC_QUARANTINE" for e in events)
    # New work is still permitted after the old work has completed.
    async def fresh():
        c.analysis._review_last.clear()
        c.analysis.schedule_review("analytics-agent")
        await asyncio.gather(*list(c.analysis._tasks))
    client.portal.call(fresh)
    assert client.get("/api/agents/analytics-agent").json()["agent"]["status"] == "quarantined"


def test_semantic_quarantine_records_reason_and_score_and_release(client):
    c = client.app.state.container
    async def run():
        async def analyze(telemetry):
            return critical()
        c.analyzer.analyze_incident = analyze
        c.analysis.schedule_review("analytics-agent")
        await asyncio.gather(*list(c.analysis._tasks))
    client.portal.call(run)
    events = client.get("/api/events", params={"agentId":"analytics-agent"}).json()["items"]
    event = next(e for e in events if e["kind"] == "quarantine")
    assert event["reasonCode"] == "AI_SEMANTIC_QUARANTINE"
    assert event["riskBefore"] == 9
    assert event["riskAfter"] == 49
    client.post("/api/agents/analytics-agent/release", json={"note":"Reviewed evidence"})
    detail = client.get("/api/incidents/" + event["incidentId"]).json()
    releases = [e for e in detail["events"] if e["kind"] == "release"]
    assert len(releases) == 1
    assert releases[0]["reason"] == "Reviewed evidence"
