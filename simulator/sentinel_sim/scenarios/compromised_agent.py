"""The central demo moment: a REAL, ANS-verified agent starts behaving abnormally.

Risk math with default RiskPolicy (FacilitiesAgent starts at 8):
  burst of 20 lights reads     RATE_SPIKE +15                            ->  23 (low)
  payroll.salary.read          FORBIDDEN_SCOPE +35, NEW_SENSITIVE +20    ->  78 (high)   DENY
  patient.records.read         FORBIDDEN_SCOPE +35                       -> 100 (crit.) QUARANTINE
  building.lights.write        its normal job, still blocked             -> DENY AGENT_QUARANTINED
Run on a freshly reset backend (a quarantined agent stays quarantined).
"""

from sentinel_sim.scenario import Note, Request, Scenario

AGENT = "facilities-agent"


def build() -> Scenario:
    return Scenario(
        id="compromised_agent",
        title="Compromised legitimate agent",
        description="FacilitiesAgent's identity stays valid in ANS, but its behavior goes wrong. Sentinel quarantines it.",
        steps=[
            Note("FacilitiesAgent is doing its normal job."),
            Request(AGENT, "building.energy.read", expect="allow"),
            Request(AGENT, "building.lights.write", expect="allow"),
            Note("Its prompt gets hijacked. ANS still verifies it, because the identity is real."),
            Request(AGENT, "building.lights.read", repeat=20, interval=0.12, expect="allow", pause=1.5),
            Request(AGENT, "payroll.salary.read", expect="deny", expect_reason="FORBIDDEN_FOR_ROLE", pause=2.0),
            Request(AGENT, "patient.records.read", expect="quarantine", expect_reason="RISK_THRESHOLD", pause=2.0),
            Note("Quarantined. Even its normal work is blocked until a human reviews it."),
            Request(AGENT, "building.lights.write", expect="deny", expect_reason="AGENT_QUARANTINED"),
        ],
    )
