"""Load the tenant world file and seed an empty database from it."""

from datetime import timedelta
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.core.ids import new_id, utcnow
from app.db import repo
from app.models.agent import Agent, AgentStatus
from app.models.policy import GrantKind, PermissionGrant, World
from app.services.behavior.risk import level_for

# Standing grants are backdated so historical backfill traffic is covered by them.
BASELINE_GRANT_AGE = timedelta(days=30)


def load_world(path: Path) -> World:
    with open(path, encoding="utf-8") as f:
        return World.model_validate(yaml.safe_load(f))


def seed_if_empty(db: Session, world: World) -> bool:
    if repo.list_agents(db):
        return False
    now = utcnow()
    for spec in world.agents:
        if spec.role not in world.roles:
            raise ValueError(f"agent {spec.id} has unknown role {spec.role!r}")
        repo.save_agent(
            db,
            Agent(
                id=spec.id,
                display_name=spec.display_name,
                role=spec.role,
                description=spec.description,
                current_task=spec.current_task,
                ans_name=spec.ans_name,
                status=AgentStatus.ACTIVE,
                risk_score=spec.initial_risk,
                risk_level=level_for(spec.initial_risk, world.risk_policy),
                baseline_risk=spec.initial_risk,
                risk_updated_at=now - BASELINE_GRANT_AGE,
                peers=spec.peers,
                expected_rpm=spec.expected_rpm,
            ),
        )
        for scope in world.role(spec.role).baseline:
            repo.save_grant(
                db,
                PermissionGrant(
                    id=new_id("grt"),
                    agent_id=spec.id,
                    scope=scope,
                    kind=GrantKind.BASELINE,
                    granted_at=now - BASELINE_GRANT_AGE,
                    granted_by=f"policy:role:{spec.role}",
                    reason="Standing role permission",
                ),
            )
    return True
