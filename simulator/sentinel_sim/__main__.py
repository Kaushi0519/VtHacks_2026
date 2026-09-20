"""CLI.
  python -m sentinel_sim list
  python -m sentinel_sim run compromised_agent [--check] [--url http://localhost:8000]
  python -m sentinel_sim agent [--scripted]   # a REAL LLM agent acting through the gateway (hero demo)
  python -m sentinel_sim smoke        # reset + backfill + every demo scenario with checks
  python -m sentinel_sim serve        # control API on :8001 for the dashboard demo panel
"""

import argparse
import asyncio
import sys

from sentinel_sim.client import DEFAULT_URL, SentinelClient
from sentinel_sim.scenario import RunState, StepResult, run_scenario
from sentinel_sim.scenarios import SCENARIOS

COLORS = {"allow": "\033[32m", "deny": "\033[31m", "quarantine": "\033[35m", "require_human": "\033[33m"}
RESET = "\033[0m"

# The smoke test: the whole demo in order, with fast decay so it finishes in ~30s.
SMOKE = [("history_backfill", {}), ("normal_operation", {}), ("permission_decay", {"ttl_seconds": 4}),
         ("fake_agent", {}), ("compromised_agent", {})]


def _print(r: StepResult) -> None:
    mark = {True: "\033[32m PASS\033[0m", False: "\033[31m FAIL\033[0m", None: "     "}[r.ok]
    if r.decision:
        color = COLORS.get(r.decision, "")
        risk = f"  risk {r.risk_after}" if r.risk_after is not None else ""
        print(f"{mark} {color}{r.decision.upper():>13}{RESET} {r.reason_code:<20} {r.label}{risk}")
        if r.ok is False:
            print(f"       {r.detail}")
    else:
        print(f"{mark} {'':>13} {'':<20} {r.label}")


async def _run(scenario_id: str, url: str, check: bool, quiet: bool = False, **params) -> RunState:
    scenario = SCENARIOS[scenario_id](**params)
    print(f"\n== {scenario.title} ({scenario_id}) ==")
    client = SentinelClient(url)
    try:
        state = RunState(scenario_id=scenario_id, title=scenario.title, check=check)
        return await run_scenario(scenario, client, state=state, on_result=None if quiet else _print)
    finally:
        await client.close()


def main() -> None:
    p = argparse.ArgumentParser(prog="sentinel_sim")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    run = sub.add_parser("run")
    run.add_argument("scenario", choices=sorted(SCENARIOS))
    run.add_argument("--check", action="store_true", help="exit non-zero if any expectation fails")
    run.add_argument("--url", default=DEFAULT_URL)
    run.add_argument("--ttl", type=int, help="permission_decay grant TTL in seconds")
    ag = sub.add_parser("agent", help="run a real LLM agent through the gateway (hero demo)")
    ag.add_argument("--agent-id", default="analytics-agent")
    ag.add_argument("--url", default=DEFAULT_URL)
    ag.add_argument("--scripted", action="store_true", help="force the deterministic brain (no LLM key)")
    tn = sub.add_parser("tenant", help="the full healthcare demo as one continuous simulation")
    tn.add_argument("--url", default=DEFAULT_URL)
    smoke = sub.add_parser("smoke")
    smoke.add_argument("--url", default=DEFAULT_URL)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8001)
    args = p.parse_args()

    if args.cmd == "list":
        for sid, factory in SCENARIOS.items():
            s = factory()
            print(f"{sid:<20} {s.description}")
    elif args.cmd == "run":
        params = {"ttl_seconds": args.ttl} if (args.ttl and args.scenario == "permission_decay") else {}
        state = asyncio.run(_run(args.scenario, args.url, args.check, quiet=args.scenario == "history_backfill", **params))
        print(f"\n{state.status.upper()}" + (f": {state.error}" if state.error else ""))
        sys.exit(1 if state.status in ("failed", "error") else 0)
    elif args.cmd == "agent":
        from sentinel_sim.agent import run_hero

        quarantined = asyncio.run(run_hero(args.agent_id, args.url, scripted=args.scripted))
        sys.exit(0 if quarantined else 2)
    elif args.cmd == "tenant":
        from sentinel_sim.living_tenant import run_tenant

        asyncio.run(run_tenant(args.url))
    elif args.cmd == "smoke":
        async def all_() -> bool:
            ok = True
            for sid, params in SMOKE:
                state = await _run(sid, args.url, True, quiet=sid == "history_backfill", **params)
                print(f"-> {state.status.upper()}" + (f": {state.error}" if state.error else ""))
                ok &= state.status == "passed"
            return ok
        passed = asyncio.run(all_())
        print("\nSMOKE " + ("PASSED" if passed else "FAILED"))
        sys.exit(0 if passed else 1)
    elif args.cmd == "serve":
        import uvicorn

        uvicorn.run("sentinel_sim.server:app", host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
