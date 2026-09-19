from sentinel_sim.scenario import Note, Request, Scenario

STEPS = [
    Request("facilities-agent", "building.energy.read", expect="allow"),
    Request("scheduling-agent", "schedule.shifts.write", expect="allow"),
    Request("payroll-agent", "schedule.shifts.read", target="scheduling-agent", expect="allow"),
    Request("analytics-agent", "analytics.warehouse.read", target="database-agent", expect="allow"),
    Request("database-agent", "analytics.warehouse.read", delegation=["analytics-agent"], chain=True, expect="allow"),
    Request("facilities-agent", "building.hvac.write", expect="allow"),
    Request("payroll-agent", "payroll.hours.read", expect="allow"),
]


def build() -> Scenario:
    return Scenario(
        id="normal_operation",
        title="Normal operation",
        description="Every agent does its normal job. ANS verifies each one; Sentinel allows; risk stays low.",
        steps=[Note("Normal hospital operations. Every request is ANS-verified and policy-checked."), *STEPS],
    )


def build_ambient(pause: float = 2.5) -> Scenario:
    """Background traffic so the mesh always looks alive. Loops until stopped."""
    steps = [Request(**{**s.__dict__, "pause": pause}) for s in STEPS]
    return Scenario(
        id="ambient",
        title="Ambient traffic",
        description="Slow, looping normal traffic for the live dashboard.",
        steps=steps,
        loop=True,
    )
