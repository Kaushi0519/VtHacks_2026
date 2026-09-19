from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_container, get_db
from app.container import Container
from app.core.ids import utcnow
from app.models.accountability import AgentReport, FleetOverview
from app.services.accountability import service as accountability

router = APIRouter(tags=["accountability"])


@router.get("/accountability/overview", response_model=FleetOverview)
def overview(
    days: float = Query(7, gt=0, le=90), c: Container = Depends(get_container), db: Session = Depends(get_db)
) -> FleetOverview:
    """Every agent (and unknown caller) ranked by how problematic its history is."""
    end = utcnow()
    return accountability.fleet_overview(db, c.world, end - timedelta(days=days), end)


@router.get("/accountability/agents/{agent_id}", response_model=AgentReport)
def agent_report(
    agent_id: str,
    days: float = Query(7, gt=0, le=90),
    c: Container = Depends(get_container),
    db: Session = Depends(get_db),
) -> AgentReport:
    """Works for unknown actor ids too (known=false)."""
    end = utcnow()
    return accountability.agent_report(db, c.world, agent_id, end - timedelta(days=days), end)
