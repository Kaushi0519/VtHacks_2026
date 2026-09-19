"""Behavioral analysis adapters. Owner: Person 3.

Gemini is an ANALYSIS component, not the authorization authority. It runs off the request path
(after the deterministic decision), its output is schema-validated and clamped, and if it fails
we fall back to a clearly labeled rule-based analysis. The demo must work with GEMINI_MODE=mock.
"""

import asyncio
import logging
from typing import Any, Literal, Protocol

from app.core.config import Settings
from app.core.ids import utcnow
from app.models.common import Severity
from app.models.incident import AnomalyType, BehaviorAnalysis, GeminiAnalysisOutput, RecommendedAction
from app.services.gemini.prompts import INCIDENT_SYSTEM, incident_prompt

log = logging.getLogger("sentinel.gemini")


class BehaviorAnalyzer(Protocol):
    mode: Literal["gemini", "fallback"]
    model: str | None

    async def analyze_incident(self, telemetry: dict[str, Any]) -> BehaviorAnalysis: ...


class FallbackAnalyzer:
    """Deterministic, rule-based explanation. Labeled source="fallback" everywhere."""

    mode: Literal["fallback"] = "fallback"
    model = None

    async def analyze_incident(self, telemetry: dict[str, Any]) -> BehaviorAnalysis:
        signals = " ".join(telemetry.get("signals", []))
        identity = telemetry.get("identity") or {}
        agent = telemetry.get("agent", {})
        action = telemetry.get("requested_action")
        peak = telemetry.get("risk_peak") or 0

        if (identity and not identity.get("ans_verified", True)) or agent.get("enrolled") is False:
            kind, reason = AnomalyType.IDENTITY_FAILURE, f"Caller {agent.get('id')} could not be verified as an enrolled agent (ANS status {identity.get('ans_status')}); {action} was blocked before any policy evaluation."
        elif "FORBIDDEN_SCOPE" in signals or "NEW_SENSITIVE_RESOURCE" in signals:
            kind, reason = AnomalyType.ROLE_RESOURCE_MISMATCH, f"The {agent.get('role')} agent requested {action}, which is outside its declared role and its observed history."
        elif "RATE_SPIKE" in signals:
            kind, reason = AnomalyType.RATE_ANOMALY, "Request volume far above this agent's normal rate."
        elif "UNEXPECTED_PEER" in signals:
            kind, reason = AnomalyType.UNUSUAL_PEER, "The agent contacted a peer it has never communicated with."
        elif "EXPIRED_GRANT_USE" in signals:
            kind, reason = AnomalyType.EXPIRED_ACCESS_REUSE, f"The agent kept using {action} after its access decayed."
        else:
            kind, reason = AnomalyType.OTHER, "Deterministic signals flagged abnormal behavior."

        if telemetry.get("quarantined") or peak >= 80:
            severity, action_rec = Severity.CRITICAL, RecommendedAction.QUARANTINE
        elif peak >= 60 or kind == AnomalyType.IDENTITY_FAILURE:
            severity, action_rec = Severity.HIGH, RecommendedAction.REQUIRE_HUMAN
        else:
            severity, action_rec = Severity.MEDIUM, RecommendedAction.MONITOR
        return BehaviorAnalysis(
            anomaly_type=kind, severity=severity, confidence=1.0, reason=reason,
            recommended_action=action_rec, source="fallback", analyzed_at=utcnow(),
        )


class GeminiAnalyzer:
    mode: Literal["gemini"] = "gemini"

    def __init__(self, settings: Settings):
        from google import genai  # imported lazily so mock mode needs no key

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_model
        self._timeout = settings.gemini_timeout_seconds
        self._fallback = FallbackAnalyzer()

    async def analyze_incident(self, telemetry: dict[str, Any]) -> BehaviorAnalysis:
        from google.genai import types

        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self.model,
                    contents=incident_prompt(telemetry),
                    config=types.GenerateContentConfig(
                        system_instruction=INCIDENT_SYSTEM,
                        response_mime_type="application/json",
                        response_schema=GeminiAnalysisOutput,
                        temperature=0.2,
                    ),
                ),
                timeout=self._timeout,
            )
            out = GeminiAnalysisOutput.model_validate_json(response.text or "")
            return BehaviorAnalysis(
                anomaly_type=out.anomaly_type,
                severity=out.severity,
                confidence=min(1.0, max(0.0, out.confidence)),
                violations=[v.strip()[:60] for v in out.violations][:6],
                reason=out.reason.strip()[:400],
                recommended_action=out.recommended_action,
                source="gemini",
                model=self.model,
                analyzed_at=utcnow(),
            )
        except Exception as exc:  # timeout, quota, network, invalid JSON, schema violation
            log.warning("Gemini analysis failed, using rule-based fallback: %r", exc)
            fallback = await self._fallback.analyze_incident(telemetry)
            return fallback.model_copy(update={"error": f"Gemini unavailable: {type(exc).__name__}"})


def build_analyzer(settings: Settings) -> BehaviorAnalyzer:
    if settings.gemini_mode == "real":
        if not settings.gemini_api_key:
            log.warning("GEMINI_MODE=real but GEMINI_API_KEY is empty; using rule-based fallback")
            return FallbackAnalyzer()
        return GeminiAnalyzer(settings)
    return FallbackAnalyzer()
