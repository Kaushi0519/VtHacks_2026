# Task board

**Already done (scaffold):** contracts, gateway pipeline, mock + GoDaddy ANS adapters, policy engine,
risk signals, quarantine, permission decay + sweeper, incidents, rule-based analyzer + Gemini adapter,
accountability API, SSE, simulator with 6 scenarios + smoke test, minimal dashboard + accountability
page. `make test` (18 tests) and `make smoke` pass. Everyone starts by running it locally (30 min).

Owners: **P1** backend lead · **P2** frontend lead · **P3** security/AI/ANS · **I** Ishan (demo/sim)

Status: ⬜ todo · 🟨 in progress (add your name) · ✅ done. Update it in the same commit as the work.

## P0: required for the demo

| ID | Task | Owner | Deps | Done when | Files | Status |
|---|---|---|---|---|---|---|
| S1 | **Get ANS access + register the 5 agents** (PAT, domain, ACME/DNS). Start hour 0; it has external lead time | P3 | - | `curl` resolution returns ACTIVE for all 5; real names in world.yaml | `world.yaml`, `.env` | ⬜ |
| S2 | Verify GoDaddy adapter against the live API (auth header, ownership-scoped GET) | P3 | S1 | `ANS_MODE=real`: agents verified, fake agent NOT_FOUND, top bar "ANS LIVE" | `services/ans/godaddy.py` | ⬜ |
| S3 | Gemini incident analysis live (key, prompt tuning, timeout) | P3 | - | quarantine incident shows a Gemini reason in <5s; key removed → labeled rule-based | `services/gemini/*` | ⬜ |
| S4 | Tune signals/weights with Ishan so scenario numbers read well | P3, I | - | `make smoke` passes; risk story reads 8→23→78→quarantine | `behavior/*`, `world.yaml riskPolicy` | ⬜ |
| B1 | Own the pipeline: review scaffold, decision logs, edge cases (unknown resource, bad scope) | P1 | - | tests for each ReasonCode path | `services/gateway/pipeline.py`, `tests/` | ⬜ |
| B2 | SSE hardening: reconnect, resync after reset, no duplicates | P1 | - | kill/restart backend mid-demo, dashboard recovers | `api/events.py`, `frontend/lib/stream.ts` (with P2) | ⬜ |
| B3 | Accountability API polish: window param, performance with 5k events, report fields the UI needs | P1 | - | overview <200ms after backfill | `services/accountability/service.py` | ⬜ |
| F1 | Mission-control look: dark theme, top bar status, agent list with risk meters | P2 | - | a judge understands the state without reading text | `app/page.tsx`, `components/layout`, `components/agents` | ⬜ |
| F2 | **Agent mesh graph**: fixed layout, per-event edge animation (green/red), quarantine isolation, ghost node for unknown actors | P2 | - | compromised scenario is visually obvious | `components/graph/*` | ⬜ |
| F3 | Live feed + inspector: identity vs behavior split, risk before→after, signals, AI reason | P2 | - | incident click shows the full "why" | `components/activity`, `components/agents/Inspector.tsx` | ⬜ |
| F4 | **Permission decay UI**: countdown bar, expire animation, dashed temp-grant edge | P2 | - | expiry visible from across the room | `Inspector.tsx`, new `components/permissions/` | ⬜ |
| F5 | **Accountability page**: fleet table w/ hypothesis badges, agent report (findings, reasons, scopes, risk sparkline), audit log filters | P2 | B3 | step 5 of DEMO.md works | `app/accountability`, `components/accountability/*` | ⬜ |
| I1 | Run everything locally; walk each scenario from the CLI (pair with P1) | I | - | can explain each step's decision | `simulator/` | ⬜ |
| I2 | Scenario polish: pacing, captions, expectations; keep smoke green | I | I1 | `make smoke` passes 3× in a row | `simulator/sentinel_sim/scenarios/*` | ⬜ |
| I3 | History backfill stories (see file docstring) | I | I1 | overview shows all 5 intended hypotheses | `scenarios/history_backfill.py`, `world.yaml` | ⬜ |
| I4 | Demo controls: captions/progress from `GET /runs`, keyboard toggle, reset flow | I | - | presenter can run the demo with only this panel | `components/demo/DemoControls.tsx` | ⬜ |
| I5 | Rehearsal owner: run DEMO.md end-to-end, log every glitch as a task | I | all | 3 clean run-throughs | `docs/DEMO.md` | ⬜ |

## P1: high value

| Task | Owner | Notes |
|---|---|---|
| Gemini accountability summary per agent (cached) | P3 | fill `AgentReport.summary`; label source |
| Bounded `AI_ASSESSMENT` signal from validated Gemini output (≤ +20, confidence ≥ 0.7) | P3 | deterministic code applies it |
| HIGH risk + sensitive resource → REQUIRE_HUMAN ("restrict") | P3 | `policy/enforcement.py` |
| Proof-of-possession demo: spoofed ANS name without key → deny | P3 | per-agent signing secret; documents the mTLS story |
| Ambient traffic running during the demo | I | `ambient` scenario exists |
| Grant/revoke UI buttons (JIT grant form) | P2 | `POST /api/agents/{id}/grants` |
| Loading/error/offline states | I, P2 | |
| Postgres via `DATABASE_URL` (only if needed) | P1 | |

## P2: stretch (don't start before P0 is green)

Forensic replay (animate an incident's events by `traceId`/`parentEventId`) · blast-radius
simulator (graph traversal from `/api/graph`) · human-approval cards for `require_human` · honeypot
scenario (`credential-vault` resource exists) · kill switch → ANS revoke (permanent, confirm) ·
ANS lifecycle feed sync (`GET /v1/agents/events`) · delegation-chain policies.

## Integration order (vertical slices)
1. Everyone runs the scaffold (already works end-to-end on mock ANS).
2. Normal ops + fake agent visible in graph (F2, I2)
3. Compromised → quarantine, the wow moment (F2, F3, S4)
4. Permission decay visible (F4)
5. Backfill + accountability page (I3, B3, F5)
6. Swap in real ANS (S2) and Gemini (S3): no interface changes
7. Freeze main → rehearse (I5) → record backup video
