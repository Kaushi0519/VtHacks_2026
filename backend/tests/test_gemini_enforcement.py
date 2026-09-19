"""Tests for the Gemini semantic-enforcement model: Sentinel owns the score, fallback never enforces."""

import asyncio

from app.models.common import Severity
from app.models.policy import RiskPolicy
from app.services.behavior.risk import semantic_points
from app.services.gemini.analyzer import FallbackAnalyzer

RP = RiskPolicy()


def test_semantic_points_only_real_gemini_moves_the_score():
    assert semantic_points("gemini", Severity.MEDIUM, RP) == RP.weight_ai_semantic_medium
    assert semantic_points("gemini", Severity.HIGH, RP) == RP.weight_ai_semantic_high
    assert semantic_points("gemini", Severity.CRITICAL, RP) == RP.weight_ai_semantic_critical
    assert semantic_points("gemini", Severity.LOW, RP) == 0
    # the rule-based fallback must never contribute to the score
    assert semantic_points("fallback", Severity.CRITICAL, RP) == 0


def test_fallback_is_labelled_and_cannot_enforce():
    telemetry = {
        "agent": {"id": "analytics-agent", "role": "analytics"},
        "identity": None,
        "signals": [],
        "requested_action": "patient.records.read",
        "risk_peak": 20,
    }
    analysis = asyncio.run(FallbackAnalyzer().analyze_incident(telemetry))
    assert analysis.source == "fallback"
    assert analysis.violations == []  # fallback is rule-based, not semantic
    # even if the fallback says CRITICAL, it can neither move the score nor quarantine
    assert semantic_points(analysis.source, analysis.severity, RP) == 0


def test_current_task_is_seeded_for_semantic_analysis(client):
    agents = {a["id"]: a for a in client.get("/api/agents").json()}
    # Gemini needs the current task to judge consistency; the demo agent must have one.
    assert agents["analytics-agent"]["currentTask"]
