"""Step 1 of the demo: the hospital brings its agent fleet online under Sentinel.

Deliberately short (~15s). Each agent checks in with one request in its own baseline scope, so the
mesh lights up column by column and the presenter can name each agent as it appears. Every call is
allowed and every identity resolves: this is the "before" picture the rest of the demo breaks.

Resets first, so the demo always starts from the same clean slate no matter what ran before.
"""

from sentinel_sim.scenario import Note, Request, Reset, Scenario

# (agent, first action, delegated target) in the order they should appear on the mesh.
ONBOARDING: list[tuple[str, str, str | None]] = [
    ("facilities-agent", "building.energy.read", None),
    ("scheduling-agent", "schedule.shifts.read", None),
    ("intake-agent", "schedule.shifts.read", None),
    ("payroll-agent", "payroll.hours.read", None),
    ("analytics-agent", "analytics.reports.read", None),
    ("database-agent", "analytics.warehouse.read", None),
]


def build() -> Scenario:
    steps = [
        Reset(),
        Note("Mercy General brings its AI agents online. Every one of them is registered in ANS."),
    ]
    for agent, action, target in ONBOARDING:
        steps.append(Request(agent, action, target=target, expect="allow", pause=1.4))
    steps.append(Note("Six agents, all ANS-verified, all doing their own jobs. This is normal."))
    return Scenario(
        id="agents_online",
        title="Agents come online",
        description="The hospital's six agents check in one by one, each ANS-verified and doing its own job.",
        steps=steps,
    )
