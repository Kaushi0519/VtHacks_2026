"""Who can act in the simulation: the enrolled hospital agents (from world.yaml) + impostors."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

WORLD_FILE = Path(os.environ.get("WORLD_FILE", Path(__file__).resolve().parents[1] / "fixtures" / "world.yaml"))


@dataclass(frozen=True)
class SimActor:
    id: str
    ans_name: str
    display_name: str
    enrolled: bool = True


# NOT in world.yaml's agents and NOT registered in (mock) ANS. The backend must not know them.
IMPOSTORS = {
    "payroll-sync-bot": SimActor(
        id="payroll-sync-bot",
        ans_name="ans://v1.0.0.payroll-sync.unknown-vendor.example",
        display_name="payroll-sync-bot",
        enrolled=False,
    ),
    # Registered in ANS (ACTIVE) but belongs to another organization -> AGENT_NOT_ENROLLED.
    "partner-courier": SimActor(
        id="partner-courier",
        ans_name="ans://v1.0.0.courier.partner-clinic.example",
        display_name="PartnerCourierAgent",
        enrolled=False,
    ),
}


@lru_cache
def actors() -> dict[str, SimActor]:
    with open(WORLD_FILE, encoding="utf-8") as f:
        world = yaml.safe_load(f)
    enrolled = {a["id"]: SimActor(id=a["id"], ans_name=a["ansName"], display_name=a["displayName"]) for a in world["agents"]}
    return {**enrolled, **IMPOSTORS}


def actor(actor_id: str) -> SimActor:
    try:
        return actors()[actor_id]
    except KeyError:
        raise KeyError(f"unknown actor {actor_id!r}; add it to fixtures/world.yaml or IMPOSTORS") from None
