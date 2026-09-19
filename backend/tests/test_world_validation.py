import pytest
from pydantic import ValidationError
from app.models.policy import RiskPolicy, World, AgentSpec
from app.core.config import Settings
from app.db.seed import load_world


@pytest.mark.parametrize("change", [
    {"thresholdCritical":101}, {"weightForbiddenScope":-1}, {"thresholdHigh":20},
    {"cooldownPerMinute":-1}, {"aiQuarantineMinConfidence":1.1}, {"typo":5},
    {"rateWindowSeconds":0},
])
def test_invalid_risk_policy_rejected(change):
    with pytest.raises(ValidationError):
        RiskPolicy.model_validate(change)


def test_invalid_initial_risk_rejected():
    with pytest.raises(ValidationError):
        AgentSpec(id="x", display_name="X", role="x", ans_name="x", initial_risk=150)


@pytest.mark.parametrize("mutation", ["agent", "prefix", "role", "peer", "conflict", "typo"])
def test_world_inconsistencies_rejected(mutation):
    world=load_world(Settings().world_file).to_json()
    if mutation == "agent":
        world["agents"].append(world["agents"][0])
    elif mutation == "prefix":
        world["resources"][1]["scopePrefix"] = world["resources"][0]["scopePrefix"]
    elif mutation == "role":
        world["agents"][0]["role"] = "missing"
    elif mutation == "peer":
        world["agents"][0]["peers"] = ["missing"]
    elif mutation == "conflict":
        world["roles"]["facilities"]["baseline"].append("payroll.salary.read")
    else:
        world["agents"][0]["typo"] = 123
    with pytest.raises(ValidationError):
        World.model_validate(world)
