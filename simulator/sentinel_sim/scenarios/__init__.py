"""Scenario registry. Add new scenarios here; the CLI, control API and demo panel pick them up."""

from sentinel_sim.scenario import ScenarioFactory
from sentinel_sim.scenarios import compromised_agent, fake_agent, history_backfill, normal_operation, permission_decay

SCENARIOS: dict[str, ScenarioFactory] = {
    "history_backfill": history_backfill.build,
    "normal_operation": normal_operation.build,
    "permission_decay": permission_decay.build,
    "fake_agent": fake_agent.build,
    "compromised_agent": compromised_agent.build,
    "ambient": normal_operation.build_ambient,
    # Stretch: delegation_incident, honeypot_attack
}
