"""Scenario model + runner. Owner: Ishan.

A scenario is a list of declarative steps. Request steps can declare the outcome we expect
(`expect="deny", expect_reason="FORBIDDEN_FOR_ROLE"`), so every scenario doubles as an
integration test: `python -m sentinel_sim run <id> --check`.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from sentinel_sim.client import SentinelClient
from sentinel_sim.world import actor

log = logging.getLogger("sentinel_sim")

# --- steps --------------------------------------------------------------------------------


@dataclass
class Note:
    """Narration. Shown in the CLI and (P1) as a caption in the dashboard's demo controls."""

    text: str


@dataclass
class Wait:
    seconds: float
    note: str | None = None


@dataclass
class Request:
    actor: str  # agent id from world.yaml, or an IMPOSTORS key
    action: str
    target: str | None = None
    delegation: list[str] = field(default_factory=list)
    chain: bool = False  # continue the previous request's trace (delegation / follow-up call)
    repeat: int = 1
    interval: float = 0.15  # seconds between repeats
    pause: float = 0.8  # seconds after the step (pacing for the audience)
    ago: timedelta | None = None  # history backfill: observedAt = run start - ago
    expect: str | None = None  # allow | deny | require_human | quarantine
    expect_reason: str | None = None  # a ReasonCode


@dataclass
class Grant:
    """Operator issues a just-in-time, decaying permission."""

    agent: str
    scope: str
    ttl_seconds: int
    reason: str


@dataclass
class Reset:
    """Wipe backend state back to the seeded world."""


@dataclass
class Resync:
    """Tell dashboards to refetch (after backfill, which is not broadcast live)."""


Step = Note | Wait | Request | Grant | Reset | Resync


@dataclass
class Scenario:
    id: str
    title: str
    description: str
    steps: list[Step]
    loop: bool = False  # ambient traffic: repeat until stopped


ScenarioFactory = Callable[..., Scenario]

# --- run state (served by the control API, camelCase for the frontend) ---------------------


class _Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, serialize_by_alias=True)


class StepResult(_Model):
    index: int
    label: str
    ok: bool | None = None  # None: nothing to check
    detail: str = ""
    decision: str | None = None
    reason_code: str | None = None
    risk_after: int | None = None


class RunState(_Model):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    scenario_id: str
    title: str
    status: str = "running"  # running | passed | failed | done | stopped | error
    check: bool = False
    step_index: int = 0
    total_steps: int = 0
    caption: str | None = None  # latest Note text
    results: list[StepResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    error: str | None = None


# --- runner --------------------------------------------------------------------------------


def describe(step: Step) -> str:
    match step:
        case Request():
            target = f" -> {step.target}" if step.target else ""
            times = f" x{step.repeat}" if step.repeat > 1 else ""
            return f"{step.actor}{target}: {step.action}{times}"
        case Grant():
            return f"grant {step.agent} {step.scope} for {step.ttl_seconds}s"
        case Wait():
            return f"wait {step.seconds:g}s" + (f" ({step.note})" if step.note else "")
        case Note():
            return step.text
        case Reset():
            return "reset demo state"
        case Resync():
            return "resync dashboards"
    return type(step).__name__


async def run_scenario(
    scenario: Scenario,
    client: SentinelClient,
    *,
    state: RunState,
    on_result: Callable[[StepResult], None] | None = None,
) -> RunState:
    source = f"scenario:{scenario.id}"
    run_start = datetime.now(timezone.utc)
    last: dict[str, Any] | None = None
    state.total_steps = len(scenario.steps)
    try:
        while True:
            for i, step in enumerate(scenario.steps):
                state.step_index = i
                result = StepResult(index=i, label=describe(step))
                match step:
                    case Note():
                        state.caption = step.text
                    case Wait():
                        await asyncio.sleep(step.seconds)
                    case Reset():
                        await client.reset()
                    case Resync():
                        await client.resync()
                    case Grant():
                        g = await client.grant(step.agent, step.scope, step.ttl_seconds, step.reason, granted_by=source)
                        result.detail = f"grant {g['id']} expires {g.get('expiresAt')}"
                    case Request():
                        last = await _run_request(step, client, source, run_start, last, result)
                        await asyncio.sleep(step.pause)
                state.results.append(result)
                if on_result:
                    on_result(result)
            if not scenario.loop:
                break
        failed = any(r.ok is False for r in state.results)
        state.status = ("failed" if failed else "passed") if state.check else "done"
    except asyncio.CancelledError:
        state.status = "stopped"
        raise
    except Exception as exc:  # backend down, validation error, etc.
        log.exception("scenario %s failed", scenario.id)
        state.status, state.error = "error", f"{type(exc).__name__}: {exc}"
    finally:
        state.finished_at = datetime.now(timezone.utc)
    return state


async def _run_request(
    step: Request,
    client: SentinelClient,
    source: str,
    run_start: datetime,
    last: dict[str, Any] | None,
    result: StepResult,
) -> dict[str, Any]:
    who = actor(step.actor)
    response: dict[str, Any] = {}
    for n in range(step.repeat):
        response = await client.request(
            who,
            step.action,
            target=step.target,
            trace_id=last["traceId"] if (step.chain and last) else None,
            parent_event_id=last["eventId"] if (step.chain and last) else None,
            delegation_chain=step.delegation,
            observed_at=(run_start - step.ago) if step.ago else None,
            source=source,
        )
        if n + 1 < step.repeat:
            await asyncio.sleep(step.interval)

    result.decision = response["decision"]
    result.reason_code = response["reasonCode"]
    result.risk_after = response.get("riskAfter")
    result.detail = response.get("reason", "")
    if step.expect or step.expect_reason:
        ok = (step.expect is None or response["decision"] == step.expect) and (
            step.expect_reason is None or response["reasonCode"] == step.expect_reason
        )
        result.ok = ok
        if not ok:
            result.detail = (
                f"expected {step.expect or '*'}/{step.expect_reason or '*'}, "
                f"got {response['decision']}/{response['reasonCode']}: {response.get('reason')}"
            )
    return response
