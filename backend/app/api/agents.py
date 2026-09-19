from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_container, get_db
from app.container import Container
from app.core.ids import utcnow
from app.db import repo
from app.db.repo import EventFilter
from app.models.agent import Agent
from app.models.gateway import AgentDetail, GrantCommand, QuarantineCommand, ReleaseCommand, RevokeCommand
from app.models.policy import GrantStatus, PermissionGrant
from app.services.grants import service as grants
from app.services.quarantine import service as quarantine

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=list[Agent])
def list_agents(db: Session = Depends(get_db)) -> list[Agent]:
    return repo.list_agents(db)


@router.get("/agents/{agent_id}", response_model=AgentDetail)
def get_agent(agent_id: str, db: Session = Depends(get_db)) -> AgentDetail:
    agent = _require_agent(db, agent_id)
    return AgentDetail(
        agent=agent,
        profile=repo.get_profile(db, agent_id),
        grants=repo.list_grants(db, agent_id=agent_id),
        recent_events=repo.query_events(db, EventFilter(agent_id=agent_id, limit=50)),
        open_incident=repo.find_open_incident(db, agent_id),
    )


@router.post("/agents/{agent_id}/quarantine", response_model=Agent)
async def quarantine_agent(agent_id: str, cmd: QuarantineCommand, c: Container = Depends(get_container)) -> Agent:
    """Operator kill switch (Sentinel-level isolation)."""
    async with c.state_lock:
        with c.session_factory() as db:
            agent = _require_agent(db, agent_id)
            changes = quarantine.quarantine(
                db, agent, utcnow(), c.world.risk_policy, reason=cmd.reason, triggered_by="operator"
            )
            db.commit()
    changes.publish(c.broadcaster)
    for incident_id in changes.analyze_incident_ids:
        c.analysis.schedule(incident_id)
    return changes.agents.get(agent_id, agent)


@router.post("/agents/{agent_id}/release", response_model=Agent)
async def release_agent(agent_id: str, cmd: ReleaseCommand, c: Container = Depends(get_container)) -> Agent:
    async with c.state_lock:
        with c.session_factory() as db:
            agent = _require_agent(db, agent_id)
            changes = quarantine.release(db, agent, utcnow(), c.world.risk_policy, note=cmd.note)
            db.commit()
    changes.publish(c.broadcaster)
    return changes.agents.get(agent_id, agent)


@router.get("/agents/{agent_id}/grants", response_model=list[PermissionGrant])
def list_agent_grants(agent_id: str, db: Session = Depends(get_db)) -> list[PermissionGrant]:
    return repo.list_grants(db, agent_id=agent_id)


@router.post("/agents/{agent_id}/grants", response_model=PermissionGrant, status_code=201)
async def issue_grant(agent_id: str, cmd: GrantCommand, c: Container = Depends(get_container)) -> PermissionGrant:
    """Just-in-time, decaying permission. Must be within the role's `grantable` scopes."""
    async with c.state_lock:
        with c.session_factory() as db:
            agent = _require_agent(db, agent_id)
            try:
                changes = grants.issue_temporary(db, c.world, agent, cmd, utcnow())
            except grants.GrantPolicyError as exc:
                raise HTTPException(403, str(exc)) from exc
            db.commit()
    changes.publish(c.broadcaster)
    return next(iter(changes.grants.values()))


@router.get("/grants", response_model=list[PermissionGrant])
def list_grants(
    status: GrantStatus | None = None,
    agent_id: str | None = Query(None, alias="agentId"),
    db: Session = Depends(get_db),
) -> list[PermissionGrant]:
    return repo.list_grants(db, agent_id=agent_id, status=status)


@router.post("/grants/{grant_id}/revoke", response_model=PermissionGrant)
async def revoke_grant(grant_id: str, cmd: RevokeCommand, c: Container = Depends(get_container)) -> PermissionGrant:
    async with c.state_lock:
        with c.session_factory() as db:
            grant = repo.get_grant(db, grant_id)
            if grant is None:
                raise HTTPException(404, f"grant {grant_id} not found")
            changes = grants.revoke(db, grant, utcnow(), reason=cmd.reason)
            db.commit()
    changes.publish(c.broadcaster)
    return changes.grants.get(grant_id, grant)


def _require_agent(db: Session, agent_id: str) -> Agent:
    agent = repo.get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(404, f"agent {agent_id} not found")
    return agent
