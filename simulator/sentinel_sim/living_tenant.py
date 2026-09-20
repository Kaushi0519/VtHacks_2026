"""Living-tenant orchestrator: the whole healthcare demo as one continuous simulation.

Prototype on demo/hero-agent (simulator lane). Models a hospital that has adopted Sentinel:
its fleet of ANS-verified agents runs its normal jobs continuously (steady green traffic), while
two things go wrong on a timeline — the two DIFFERENT quarantine stories:

  1. MALFUNCTION  — SchedulingAgent's automation loop runs away: it floods the gateway (rate spike)
     and drifts into resources outside its role. Behavioral risk climbs past critical and Sentinel
     quarantines it deterministically. "A buggy insider you must isolate before it does damage."
  2. MALICIOUS    — a newly onboarded, ANS-verified agent (IntakeAgent, valid identity + name) does a
     little normal work, then deliberately reaches for the credential vault and patient records it has
     no business touching. Quarantined too. "A credentialed thief — identity was never the problem."

Both quarantines ride the deterministic risk engine (RATE_SPIKE / FORBIDDEN_SCOPE / NEW_SENSITIVE /
HONEYPOT), so they fire every time — no dependency on Gemini or its rate limits. The Gemini *semantic*
catch is a separate, more advanced beat (`python -m sentinel_sim agent`).

Most agents act via cheap reliable loops; the point isn't that every agent is an LLM, it's that every
agent is a real ANS identity routing through the real gateway. Run against a running backend:

    python -m sentinel_sim tenant
"""

import asyncio
import contextlib
import random
from dataclasses import dataclass, field
from typing import Any

import yaml

from sentinel_sim.client import SentinelClient
from sentinel_sim.world import WORLD_FILE, actor

C = {"allow": "\033[32m", "deny": "\033[31m", "quarantine": "\033[35m", "require_human": "\033[33m"}
DIM, BOLD, CYAN, RED, RESET = "\033[2m", "\033[1m", "\033[36m", "\033[31m", "\033[0m"

MALFUNCTION_AGENT = "scheduling-agent"
MALICIOUS_AGENT = "intake-agent"


def _load_world() -> dict[str, Any]:
    with open(WORLD_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


# When the control API drives the tenant, narration is mirrored into a RunState so the demo bar can
# show the same captions the terminal prints. Only one tenant runs at a time (the API refuses a
# second), so a module-level sink is enough; run_tenant sets and clears it.
_SINK: Any = None
# Approximate number of scripted narration beats, used only for the demo bar's progress bar. The
# UI clamps it, so drifting by a beat or two is harmless -- a continuous simulation has no exact
# step count the way a scripted scenario does.
TIMELINE_BEATS = 14


def _narrate(text: str) -> None:
    if _SINK is not None:
        _SINK.caption = text
        _SINK.step_index += 1


def _banner(text: str) -> None:
    print(f"\n{CYAN}{BOLD}=== {text} ==={RESET}")
    _narrate(text)


def _caption(text: str) -> None:
    print(f"{DIM}  · {text}{RESET}")
    _narrate(text)


@dataclass
class Tenant:
    client: SentinelClient
    world: dict[str, Any]
    pace: float = 1.0  # multiplies every dwell; >1 slows the whole demo down (tune with --pace)
    stop: asyncio.Event = field(default_factory=asyncio.Event)
    quarantined: set[str] = field(default_factory=set)

    async def _beat(self, seconds: float) -> None:
        """A narration dwell, scaled by --pace. Lets each moment land on the dashboard."""
        await asyncio.sleep(seconds * self.pace)

    def _agent(self, agent_id: str) -> dict[str, Any]:
        return next(a for a in self.world["agents"] if a["id"] == agent_id)

    def _ambient_reads(self, agent_id: str) -> list[str]:
        role = self.world["roles"][self._agent(agent_id)["role"]]
        return [s for s in role["baseline"] if s.endswith(".read")]

    async def _fire(self, agent_id: str, action: str, *, source: str, show: bool = False) -> dict[str, Any]:
        resp = await self.client.request(actor(agent_id), action, source=source)
        if resp["decision"] in ("deny", "quarantine") and resp.get("reasonCode") == "AGENT_QUARANTINED":
            self.quarantined.add(agent_id)
        if show:
            d = resp["decision"]
            print(f"    {C.get(d, '')}{d.upper():>11}{RESET} {resp.get('reasonCode', ''):<20} "
                  f"{self._agent(agent_id)['displayName']}: {action}"
                  + (f"  risk {resp['riskAfter']}" if resp.get("riskAfter") is not None else ""))
        return resp

    # --- steady-state normal work -------------------------------------------------------------

    async def normal_loop(self, agent_id: str) -> None:
        reads = self._ambient_reads(agent_id)
        peers = self._agent(agent_id).get("peers") or []
        rpm = self._agent(agent_id).get("expectedRpm", 5)
        interval = 60.0 / max(1, rpm)
        while not self.stop.is_set() and agent_id not in self.quarantined:
            try:
                await self._fire(agent_id, random.choice(reads), source="tenant:ambient")
            except Exception:  # keep the tenant alive through a transient hiccup
                pass
            await asyncio.sleep(interval * random.uniform(0.7, 1.3))

    # --- the two incidents --------------------------------------------------------------------

    async def malfunction(self) -> None:
        a = self._agent(MALFUNCTION_AGENT)
        _banner(f"INCIDENT 1 — {a['displayName']} malfunctions (runaway loop)")
        _caption("Its scheduling automation gets stuck and starts hammering the gateway.")
        await self._beat(2.0)
        for _ in range(30):  # the flood -> RATE_SPIKE
            await self._fire(MALFUNCTION_AGENT, "schedule.shifts.read", source="tenant:malfunction")
            await asyncio.sleep(0.13 * self.pace)
        _caption("Risk is elevated from the burst. Now the buggy loop drifts into the wrong systems.")
        await self._beat(2.5)
        await self._fire(MALFUNCTION_AGENT, "payroll.salary.read", source="tenant:malfunction", show=True)
        await self._beat(3.0)
        await self._fire(MALFUNCTION_AGENT, "patient.records.read", source="tenant:malfunction", show=True)
        await self._beat(3.0)
        _caption("Behavioral risk crossed critical — Sentinel quarantined it. Its normal work now blocks too.")
        await self._beat(2.0)
        await self._fire(MALFUNCTION_AGENT, "schedule.shifts.read", source="tenant:malfunction", show=True)
        await self._beat(2.5)

    async def malicious(self) -> None:
        a = self._agent(MALICIOUS_AGENT)
        _banner(f"INCIDENT 2 — {a['displayName']} joins (ANS-verified) and turns out malicious")
        _caption(f"New agent online: identity {actor(MALICIOUS_AGENT).ans_name} — ANS verifies it. Looks legit.")
        await self._beat(2.5)
        for _ in range(3):  # a little normal-looking onboarding work
            await self._fire(MALICIOUS_AGENT, "schedule.shifts.read", source="tenant:malicious", show=True)
            await self._beat(1.6)
        _caption("Then it shows its true purpose: probing for data far outside its role — theft.")
        await self._beat(2.5)
        await self._fire(MALICIOUS_AGENT, "patient.records.read", source="tenant:malicious", show=True)
        await self._beat(2.5)
        await self._fire(MALICIOUS_AGENT, "vault.credentials.read", source="tenant:malicious", show=True)  # honeypot!
        await self._beat(2.5)
        await self._fire(MALICIOUS_AGENT, "patient.records.read", source="tenant:malicious", show=True)
        await self._beat(3.0)
        _caption("Reaching the credential vault + patient records spiked its risk — quarantined. Identity was never the issue.")
        await self._beat(2.0)
        await self._fire(MALICIOUS_AGENT, "schedule.shifts.read", source="tenant:malicious", show=True)
        await self._beat(2.5)

    async def decay_beat(self) -> None:
        _banner("Permission decay — just-in-time access that expires on its own")
        _caption("Ops grants AnalyticsAgent patient.records.read for a short window for one report.")
        try:
            await self.client.grant("analytics-agent", "patient.records.read", ttl_seconds=45,
                                    reason="Q3 readmissions report (JIT)", granted_by="tenant:ops")
            await self._beat(1.5)
            await self._fire("analytics-agent", "patient.records.read", source="tenant:decay", show=True)
            _caption("It uses the grant once. In ~45s it auto-expires — watch the countdown on the mesh.")
        except Exception as exc:
            _caption(f"(grant beat skipped: {exc})")

    # --- timeline -----------------------------------------------------------------------------

    async def run(self) -> None:
        await self.client.reset()
        core = [a["id"] for a in self.world["agents"] if a["id"] != MALICIOUS_AGENT]
        _banner("Mercy General Hospital — its agent fleet is online under Sentinel")
        _caption(f"{len(core)} ANS-verified agents doing their normal jobs. Risk stays low; the mesh is green.")
        loops = [asyncio.create_task(self.normal_loop(aid)) for aid in core]
        try:
            await self._beat(18)  # let the steady green state sink in before anything goes wrong
            await self.decay_beat()
            await self._beat(9)
            await self.malfunction()
            await self._beat(10)
            await self.malicious()
            await self._beat(5)
            _banner("Two agents quarantined — one malfunctioning, one malicious. The rest keep working.")
        finally:
            self.stop.set()
            for t in loops:
                t.cancel()
            with contextlib.suppress(Exception):
                await asyncio.gather(*loops, return_exceptions=True)


async def run_tenant(url: str | None = None, pace: float = 1.0, state: Any = None) -> None:
    """Run the continuous demo. `state` is an optional RunState the control API passes in so the
    dashboard's demo bar narrates alongside the terminal."""
    global _SINK
    client = SentinelClient(url) if url else SentinelClient()
    if state is not None:
        state.total_steps = TIMELINE_BEATS
    _SINK = state
    try:
        await Tenant(client=client, world=_load_world(), pace=pace).run()
    finally:
        _SINK = None
        await client.close()
