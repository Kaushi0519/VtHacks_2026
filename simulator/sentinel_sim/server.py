"""Simulator control API (port 8001). The dashboard's demo panel calls this to start scenarios.
The scenarios themselves only talk to Sentinel through its public gateway API."""

import asyncio
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from sentinel_sim.client import DEFAULT_URL, SentinelClient
from sentinel_sim.scenario import RunState, run_scenario
from sentinel_sim.scenarios import SCENARIOS

app = FastAPI(title="Sentinel Mesh Simulator", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("SIM_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

_runs: dict[str, RunState] = {}
_tasks: dict[str, asyncio.Task] = {}

# The continuous demos. They are not Scenarios -- a Scenario is a declarative list of steps, while
# these run several agent loops concurrently -- so they cannot live in SCENARIOS. They are listed
# and started through the same endpoints anyway, which is what puts a button for each on the
# dashboard's demo bar next to the scripted scenarios.
SPECIALS: dict[str, dict] = {
    "living_tenant": {
        "title": "Living hospital (full demo)",
        "description": "The whole story as one continuous simulation: six agents working, a grant "
                       "expiring, SchedulingAgent malfunctioning, then IntakeAgent turning malicious.",
    },
    "hero_agent": {
        "title": "Real LLM agent (Gemini catches it)",
        "description": "A genuine model-driven agent is given a task, gets prompt-hijacked mid-run, "
                       "and the backend's semantic review quarantines it. Needs GEMINI_MODE=real to enforce.",
    },
}


def _running(scenario_id: str) -> bool:
    return any(r.scenario_id == scenario_id and r.status == "running" for r in _runs.values())


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "sentinelUrl": DEFAULT_URL}


@app.get("/scenarios")
def list_scenarios() -> list[dict]:
    out = []
    for sid, factory in SCENARIOS.items():
        s = factory()
        out.append({"id": sid, "title": s.title, "description": s.description, "loop": s.loop, "steps": len(s.steps)})
    for sid, meta in SPECIALS.items():
        out.append({"id": sid, "title": meta["title"], "description": meta["description"], "loop": False, "steps": 0})
    return out


@app.post("/scenarios/{scenario_id}/run", response_model=RunState)
async def run(scenario_id: str, check: bool = False, ttl_seconds: int | None = None) -> RunState:
    if scenario_id in SPECIALS:
        return _run_special(scenario_id)
    factory = SCENARIOS.get(scenario_id)
    if factory is None:
        raise HTTPException(404, f"unknown scenario {scenario_id}")
    scenario = factory(ttl_seconds=ttl_seconds) if (ttl_seconds and scenario_id == "permission_decay") else factory()
    state = RunState(scenario_id=scenario_id, title=scenario.title, check=check)
    _runs[state.id] = state

    async def go() -> None:
        client = SentinelClient()
        try:
            await run_scenario(scenario, client, state=state)
        finally:
            await client.close()
            _tasks.pop(state.id, None)

    _tasks[state.id] = asyncio.create_task(go())
    return state


def _run_special(scenario_id: str, pace: float = 1.3) -> RunState:
    """Start a continuous demo. Both reset the world themselves, so starting one while it is already
    running would fight itself -- refuse instead, the way a double-clicked scenario button does."""
    if _running(scenario_id):
        raise HTTPException(409, f"{scenario_id} is already running")
    meta = SPECIALS[scenario_id]
    state = RunState(scenario_id=scenario_id, title=meta["title"])
    _runs[state.id] = state

    async def go() -> None:
        try:
            if scenario_id == "living_tenant":
                from sentinel_sim.living_tenant import run_tenant

                await run_tenant(pace=pace, state=state)
            else:
                from sentinel_sim.agent import run_hero

                await run_hero(state=state)
            state.status = "done"
        except asyncio.CancelledError:
            state.status = "stopped"
            raise
        except Exception as exc:  # surfaced on the demo bar rather than dying silently
            state.status = "error"
            state.error = f"{type(exc).__name__}: {exc}"
        finally:
            state.finished_at = datetime.now(timezone.utc)
            _tasks.pop(state.id, None)

    _tasks[state.id] = asyncio.create_task(go())
    return state


@app.get("/runs", response_model=list[RunState])
def list_runs() -> list[RunState]:
    return sorted(_runs.values(), key=lambda r: r.started_at, reverse=True)[:20]


@app.get("/runs/{run_id}", response_model=RunState)
def get_run(run_id: str) -> RunState:
    if run_id not in _runs:
        raise HTTPException(404, "unknown run")
    return _runs[run_id]


@app.post("/runs/{run_id}/stop", response_model=RunState)
def stop(run_id: str) -> RunState:
    task = _tasks.get(run_id)
    if task:
        task.cancel()
    if run_id not in _runs:
        raise HTTPException(404, "unknown run")
    return _runs[run_id]


@app.post("/runs/stop-all")
def stop_all() -> dict:
    for task in list(_tasks.values()):
        task.cancel()
    return {"stopped": len(_tasks)}
