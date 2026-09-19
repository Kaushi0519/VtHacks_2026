import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_container, get_db
from app.container import Container
from app.db import repo
from app.db.repo import EventFilter
from app.models.common import Decision
from app.models.event import EventKind, EventPage

router = APIRouter(tags=["events"])

HEARTBEAT_SECONDS = 15


@router.get("/events/stream")
async def stream(request: Request, c: Container = Depends(get_container)) -> StreamingResponse:
    """Server-Sent Events. Each message: data: {"type": StreamType, "data": {...}}.
    On (re)connect the client should GET /api/snapshot; the stream only carries deltas."""
    queue = c.broadcaster.subscribe()

    async def gen():
        try:
            yield "retry: 2000\n\n"
            while not await request.is_disconnected():
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                    yield f"data: {message}\n\n"
                except TimeoutError:
                    yield ": ping\n\n"
        finally:
            c.broadcaster.unsubscribe(queue)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/events", response_model=EventPage)
def list_events(
    agent_id: str | None = Query(None, alias="agentId"),
    kind: EventKind | None = None,
    decision: Decision | None = None,
    reason_code: str | None = Query(None, alias="reasonCode"),
    trace_id: str | None = Query(None, alias="traceId"),
    incident_id: str | None = Query(None, alias="incidentId"),
    since: datetime | None = None,
    until: datetime | None = None,
    before_seq: int | None = Query(None, alias="beforeSeq"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> EventPage:
    """Audit log explorer. Newest first; page with beforeSeq=<nextBeforeSeq>."""
    items = repo.query_events(db, EventFilter(
        agent_id=agent_id, kind=kind, decision=decision, reason_code=reason_code, trace_id=trace_id,
        incident_id=incident_id, since=since, until=until, before_seq=before_seq, limit=limit,
    ))
    return EventPage(items=items, next_before_seq=items[-1].seq if len(items) == limit else None)
