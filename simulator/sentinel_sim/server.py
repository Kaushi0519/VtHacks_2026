"""Simulator control API (port 8001). The dashboard's demo panel calls this to start scenarios.
The scenarios themselves only talk to Sentinel through its public gateway API."""

import asyncio
import os

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "sentinelUrl": DEFAULT_URL}


@app.get("/scenarios")
def list_scenarios() -> list[dict]:
    out = []
    for sid, factory in SCENARIOS.items():
        s = factory()
        out.append({"id": sid, "title": s.title, "description": s.description, "loop": s.loop, "steps": len(s.steps)})
    return out


@app.post("/scenarios/{scenario_id}/run", response_model=RunState)
async def run(scenario_id: str, check: bool = False, ttl_seconds: int | None = None) -> RunState:
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
