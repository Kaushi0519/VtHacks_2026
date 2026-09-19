from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_container, get_db
from app.container import Container
from app.core.ids import utcnow
from app.db import repo
from app.db.repo import EventFilter
from app.db.seed import seed_if_empty
from app.db.session import drop_and_create_tables
from app.models.incident import IncidentStatus
from app.models.policy import GrantStatus, World
from app.models.system import Graph, GraphEdge, GraphNode, Snapshot, SystemInfo

router = APIRouter(tags=["system"])


@router.get("/health")
def health(c: Container = Depends(get_container)) -> dict:
    return {"status": "ok", "ansMode": c.ans.mode, "analyzerMode": c.analyzer.mode}


@router.get("/system", response_model=SystemInfo)
def system_info(c: Container = Depends(get_container)) -> SystemInfo:
    return _system_info(c)


@router.get("/graph", response_model=Graph)
def graph(c: Container = Depends(get_container)) -> Graph:
    return build_graph(c.world)


@router.get("/snapshot", response_model=Snapshot)
def snapshot(c: Container = Depends(get_container), db: Session = Depends(get_db)) -> Snapshot:
    now = utcnow()
    recent_cutoff = now - timedelta(minutes=10)
    grants = [
        g for g in repo.list_grants(db)
        if g.status == GrantStatus.ACTIVE or (g.ended_at is not None and g.ended_at >= recent_cutoff)
    ]
    incidents = repo.list_incidents(db, status=IncidentStatus.OPEN) + [
        i for i in repo.list_incidents(db, status=IncidentStatus.RESOLVED, limit=10)
    ]
    return Snapshot(
        system=_system_info(c),
        agents=repo.list_agents(db),
        resources=c.world.resources,
        graph=build_graph(c.world),
        grants=grants,
        incidents=incidents,
        events=repo.query_events(db, EventFilter(limit=100)),
        last_seq=repo.last_seq(db),
    )


@router.post("/admin/reset")
async def reset(c: Container = Depends(get_container)) -> dict:
    """Demo reset: wipe state, reload the world file, reseed. Clients get a `resync` message."""
    async with c.state_lock:
        c.reload_world()
        drop_and_create_tables(c.engine)
        with c.session_factory() as db:
            seed_if_empty(db, c.world)
            db.commit()
        c.ans.invalidate()
    c.broadcaster.resync()
    return {"status": "reset", "agents": len(c.world.agents)}


@router.post("/admin/resync")
def resync(c: Container = Depends(get_container)) -> dict:
    """Tell dashboards to refetch /api/snapshot (used after history backfill)."""
    c.broadcaster.resync()
    return {"status": "ok"}


def _system_info(c: Container) -> SystemInfo:
    return SystemInfo(
        tenant_name=c.world.tenant.name,
        ans_mode=c.ans.mode,
        ans_base_url=c.ans.base_url,
        analyzer_mode=c.analyzer.mode,
        gemini_model=c.analyzer.model,
        risk_policy=c.world.risk_policy,
        backfill_enabled=c.settings.allow_backfill,
        server_time=utcnow(),
    )


def build_graph(world: World) -> Graph:
    """Baseline topology from the world file. Live traffic is animated on top by the frontend."""
    nodes = [GraphNode(id=a.id, kind="agent", label=a.display_name, group=a.role) for a in world.agents]
    nodes += [GraphNode(id=r.id, kind="resource", label=r.display_name, group=r.sensitivity.value) for r in world.resources]
    edges: dict[str, GraphEdge] = {}
    for a in world.agents:
        for peer in a.peers:
            key = "--".join(sorted([a.id, peer]))
            edges.setdefault(key, GraphEdge(id=key, source=a.id, target=peer, kind="peer"))
        for scope in world.role(a.role).baseline:
            r = world.resource_for_scope(scope)
            if r is not None:
                key = f"{a.id}->{r.id}"
                edges.setdefault(key, GraphEdge(id=key, source=a.id, target=r.id, kind="access"))
    return Graph(nodes=nodes, edges=list(edges.values()))
