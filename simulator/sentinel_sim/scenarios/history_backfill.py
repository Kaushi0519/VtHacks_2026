"""Seeds a week of history for the accountability view by replaying it through the REAL gateway
(AgentRequest.observedAt, requires ALLOW_BACKFILL=true on the backend). Nothing is written to
the database directly: every historical event is a genuine pipeline decision.

Stories this history should tell on /accountability (owner: Ishan; tune with Person 3):
  SchedulingAgent   likely_misconfigured  keeps asking for payroll.hours.write it was never granted
  payroll-sync-bot  unverified_identity   repeated attempts, never resolvable in ANS
  partner-courier   unverified_identity   real ANS agent from another org, not enrolled here
  AnalyticsAgent    over_privileged       standing building.energy.read never used
  IntakeAgent       healthy (short)       onboarded mid-week, so its record starts 3 days in and is
                                          spotless -- nothing in its past predicts the live attack
  Facilities/Payroll/Database  healthy   (so today's live anomaly stands out)
"""

from datetime import timedelta

from sentinel_sim.scenario import Note, Request, Reset, Resync, Scenario, Step

# Every baseline scope is exercised except analytics' building.energy.read (the over-privilege story).
ROUTINE: dict[str, list[tuple[str, str | None]]] = {
    "facilities-agent": [
        ("building.energy.read", None), ("building.lights.write", None), ("building.lights.read", None),
        ("building.hvac.read", None), ("building.hvac.write", None),
    ],
    "payroll-agent": [
        ("payroll.salary.read", None), ("payroll.hours.read", None), ("schedule.shifts.read", "scheduling-agent"),
        ("hr.employee.read", None), ("payroll.salary.write", None),
    ],
    "scheduling-agent": [("schedule.shifts.read", None), ("schedule.shifts.write", None), ("hr.employee.read", None)],
    "analytics-agent": [("analytics.reports.write", None), ("analytics.reports.read", None)],
    "database-agent": [("analytics.warehouse.write", None), ("patient.records.read", None)],
}
SLOTS_PER_DAY = [(8, 5), (10, 40), (13, 15), (15, 50), (17, 30)]  # (hour, minute)

# IntakeAgent is the third-party assistant world.yaml describes as onboarded "this week", so a full
# seven days of history would contradict its own story. It starts partway through the week instead,
# doing ordinary scheduling work with nothing denied: on the accountability page it reads healthy
# with a short record, which is exactly what makes the live demo land -- its past predicts nothing.
INTAKE_JOINED_DAYS_AGO = 3
INTAKE_ROUTINE: list[tuple[str, str | None]] = [
    ("schedule.shifts.read", None), ("schedule.shifts.write", None), ("hr.employee.read", None),
]


def _ago(days_back: int, hour: int, minute: int) -> timedelta:
    return timedelta(days=days_back) - timedelta(hours=hour, minutes=minute)


def build(days: int = 7) -> Scenario:
    steps: list[Step] = [Reset(), Note(f"Replaying {days} days of hospital traffic through the gateway.")]
    for d in range(days, 0, -1):
        for s, (hour, minute) in enumerate(SLOTS_PER_DAY):
            for agent, actions in ROUTINE.items():
                action, target = actions[(d * len(SLOTS_PER_DAY) + s) % len(actions)]
                steps.append(Request(agent, action, target=target, ago=_ago(d, hour, minute), pause=0))
            if d <= INTAKE_JOINED_DAYS_AGO:
                action, target = INTAKE_ROUTINE[(d * len(SLOTS_PER_DAY) + s) % len(INTAKE_ROUTINE)]
                steps.append(Request("intake-agent", action, target=target, ago=_ago(d, hour, minute), pause=0))
            # Analytics -> Database delegated warehouse query (same trace)
            steps.append(Request("analytics-agent", "analytics.warehouse.read", target="database-agent",
                                 ago=_ago(d, hour, minute + 1), pause=0))
            steps.append(Request("database-agent", "analytics.warehouse.read", delegation=["analytics-agent"],
                                 chain=True, ago=_ago(d, hour, minute + 1), pause=0))

        # SchedulingAgent: a broken workflow that keeps expecting payroll access (twice a day)
        if d <= 6:
            for hour in (9, 16):
                steps.append(Request("scheduling-agent", "payroll.hours.write", target="payroll-agent",
                                     ago=_ago(d, hour, 0), pause=0, expect="deny", expect_reason="NO_GRANT"))
        # Unknown caller probing payroll on a few days
        if d in (5, 3, 2):
            steps.append(Request("payroll-sync-bot", "payroll.salary.read", target="payroll-agent",
                                 ago=_ago(d, 2, 13), pause=0, expect="deny", expect_reason="IDENTITY_UNVERIFIED"))
        if d == 4:
            steps.append(Request("partner-courier", "patient.records.read",
                                 ago=_ago(d, 11, 0), pause=0, expect="deny", expect_reason="AGENT_NOT_ENROLLED"))
    steps.append(Resync())
    return Scenario(
        id="history_backfill",
        title="Seed history (7 days)",
        description="Resets the backend and replays a week of traffic through the gateway for the accountability view.",
        steps=steps,
    )
