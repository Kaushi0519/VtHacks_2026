from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_container
from app.container import Container
from app.core.ids import utcnow
from app.models.gateway import AgentRequest, GatewayDecision

router = APIRouter(tags=["gateway"])


@router.post("/gateway/evaluate", response_model=GatewayDecision)
async def evaluate(req: AgentRequest, c: Container = Depends(get_container)) -> GatewayDecision:
    """The interception point: every agent action goes through here (via SDK / sidecar / proxy)."""
    if req.observed_at is not None:
        if not c.settings.allow_backfill:
            raise HTTPException(400, "observedAt is only accepted when ALLOW_BACKFILL=true")
        if req.observed_at.tzinfo is None:
            raise HTTPException(422, "observedAt must include a timezone")
        if req.observed_at > utcnow() + timedelta(seconds=5):
            raise HTTPException(422, "observedAt cannot be in the future")
    return await c.gateway.evaluate(req)
