from sentinel_sim.scenario import Note, Request, Scenario


def build() -> Scenario:
    return Scenario(
        id="fake_agent",
        title="Fake agent",
        description="An agent that isn't registered in ANS tries to read salaries. Denied on identity alone.",
        steps=[
            Note("An unknown 'payroll sync' agent reaches for salary data."),
            Request("payroll-sync-bot", "payroll.salary.read", target="payroll-agent",
                    expect="deny", expect_reason="IDENTITY_UNVERIFIED", pause=1.5),
            Request("payroll-sync-bot", "hr.employee.read",
                    expect="deny", expect_reason="IDENTITY_UNVERIFIED"),
            Note("ANS can't resolve it, so Sentinel never even evaluates policy."),
        ],
    )
