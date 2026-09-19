"""Least privilege over time: a just-in-time grant that disappears on its own.

Tip for the live demo: start this FIRST. The countdown runs in the background while you show
the fake-agent and compromised-agent parts, and the grant expires on screen.
"""

from sentinel_sim.scenario import Grant, Note, Request, Scenario, Wait

AGENT = "analytics-agent"
SCOPE = "patient.records.read"


def build(ttl_seconds: int = 45) -> Scenario:
    return Scenario(
        id="permission_decay",
        title="Permission decay",
        description=f"AnalyticsAgent gets {SCOPE} for {ttl_seconds}s, uses it, and loses it automatically.",
        steps=[
            Note("AnalyticsAgent needs patient records for the monthly readmissions report."),
            Grant(AGENT, SCOPE, ttl_seconds=ttl_seconds, reason="Monthly readmissions report (just-in-time)"),
            Request(AGENT, SCOPE, expect="allow"),
            Wait(min(3.0, ttl_seconds / 4)),
            Request(AGENT, SCOPE, expect="allow"),
            Note(f"Nobody has to remember to revoke it. The access decays in {ttl_seconds}s."),
            Wait(ttl_seconds, note="grant decaying"),
            Request(AGENT, SCOPE, expect="deny", expect_reason="GRANT_EXPIRED"),
            Note("The decayed grant is denied. The agent holds only what it currently needs."),
        ],
    )
