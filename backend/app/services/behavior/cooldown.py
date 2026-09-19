from datetime import datetime

from sqlalchemy.orm import Session

from app.core.changes import Changes
from app.db import repo
from app.models.agent import AgentStatus
from app.models.policy import RiskPolicy
from app.services.behavior.risk import cooled_score, level_for


def cool_down_agents(db: Session, rp: RiskPolicy, now: datetime) -> Changes:
    """Materialize risk decay so the dashboard shows scores drifting back toward baseline."""
    changes = Changes()
    for agent in repo.list_agents(db):
        if agent.status == AgentStatus.QUARANTINED:
            continue
        cooled = cooled_score(agent, now, rp)
        if cooled < agent.risk_score:
            updated = agent.model_copy(update={
                "risk_score": cooled, "risk_level": level_for(cooled, rp), "risk_updated_at": now,
            })
            repo.save_agent(db, updated)
            changes.agent(updated)
    return changes
