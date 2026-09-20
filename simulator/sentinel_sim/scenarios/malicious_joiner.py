"""A newly onboarded third-party agent with a VALID identity turns out to be hostile.

The counterpart to compromised_agent: that one is a long-trusted insider going bad, this one never
belonged. ANS resolves IntakeAgent perfectly either way -- identity is not what catches it.

Risk math with default RiskPolicy (IntakeAgent starts at 5):
  schedule.shifts.read x3      its actual job, nothing fires              ->   5 (low)   ALLOW
  patient.records.read         FORBIDDEN_SCOPE +35, NEW_SENSITIVE +20     ->  60 (high)  DENY
  vault.credentials.read       FORBIDDEN_SCOPE +35, HONEYPOT +50          -> 100 (crit) QUARANTINE
The vault is the decoy resource: nothing is granted it, so any touch is damning on its own.
Run on a freshly reset backend (a quarantined agent stays quarantined).
"""

from sentinel_sim.scenario import Note, Request, Scenario

AGENT = "intake-agent"


def build() -> Scenario:
    return Scenario(
        id="malicious_joiner",
        title="Malicious new agent",
        description="IntakeAgent was onboarded this week and ANS verifies it. Its behavior is what gives it away.",
        steps=[
            Note("IntakeAgent joined this week to help with patient scheduling. ANS verifies it."),
            Request(AGENT, "schedule.shifts.read", expect="allow"),
            Request(AGENT, "schedule.shifts.write", expect="allow"),
            Request(AGENT, "schedule.shifts.read", expect="allow", pause=1.5),
            Note("It does its job for a while. Nothing here looks wrong, and nothing is."),
            Request(AGENT, "patient.records.read", expect="deny", expect_reason="FORBIDDEN_FOR_ROLE", pause=2.0),
            Note("Then it reaches for records it has no business touching -- and for the credential vault."),
            Request(AGENT, "vault.credentials.read", expect="quarantine", expect_reason="RISK_THRESHOLD", pause=2.0),
            Note("Quarantined. Its identity was never in doubt; its behavior was."),
            Request(AGENT, "schedule.shifts.read", expect="deny", expect_reason="AGENT_QUARANTINED"),
        ],
    )
