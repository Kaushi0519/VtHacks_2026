from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db import repo
from app.models.incident import Incident, IncidentDetail, IncidentStatus

router = APIRouter(tags=["incidents"])


@router.get("/incidents", response_model=list[Incident])
def list_incidents(
    status: IncidentStatus | None = None,
    agent_id: str | None = Query(None, alias="agentId"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[Incident]:
    return repo.list_incidents(db, status=status, agent_id=agent_id, limit=limit)


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: str, db: Session = Depends(get_db)) -> IncidentDetail:
    incident = repo.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(404, f"incident {incident_id} not found")
    return IncidentDetail(incident=incident, events=repo.get_events_by_ids(db, incident.event_ids))
