# Task board

## Completed audit fixes

- [x] Person 3: require repeated forbidden-request evidence for the accountability
  out-of-role finding; manual quarantine alone is insufficient. Regression tests
  cover fleet and agent reports before/after release. See `SECURITY-VALIDATION.md`.

**Already done (scaffold):** contracts, gateway pipeline, mock + GoDaddy ANS adapters, policy engine,
risk signals, quarantine, permission decay + sweeper, incidents, rule-based analyzer + Gemini adapter,
accountability API, SSE, simulator with 6 scenarios + smoke test, minimal dashboard + accountability
page. `make test` (18 tests) and `make smoke` pass. Everyone starts by running it locally (30 min).

Owners: **P1** backend lead · **P2** frontend lead · **P3** security/AI/ANS · **I** Ishan (demo/sim)

Status: ⬜ todo · 🟨 in progress (add your name) · ✅ done. Update it in the same commit as the work.

## P0: required for the demo

| ID | Task | Owner | Deps | Done when | Files | Status |
|---|---|---|---|---|---|---|
| S1 | **Stand up ANS locally + register the 5 agents** (reference impl, no PAT/DNS lead time). See checklist below | P3 | - | reference stack running; 5 agents ACTIVE; real agentIds in `world.yaml` | `world.yaml` | ⬜ |
| S2 | **Validate `reference.py` against the live stack** (confirm the 3 TODO assumptions) | P3 | S1 | `ANS_MODE=real`: agents verified, impostor NOT_FOUND, `tlVerified=true`, top bar "ANS LIVE" | `services/ans/reference.py` | ⬜ |
| S3 | Gemini incident analysis live (key, prompt tuning, timeout) | P3 | - | quarantine incident shows a Gemini reason in <5s; key removed → labeled rule-based | `services/gemini/*` | ⬜ |
| S4 | Tune signals/weights with Ishan so scenario numbers read well | P3, I | - | `make smoke` passes; risk story reads 8→23→78→quarantine | `behavior/*`, `world.yaml riskPolicy` | ⬜ |
| B1 | Own the pipeline: review scaffold, decision logs, edge cases (unknown resource, bad scope) | P1 | - | tests for each ReasonCode path | `services/gateway/pipeline.py`, `tests/` | ⬜ |
| B2 | SSE hardening: reconnect, resync after reset, no duplicates | P1 | - | kill/restart backend mid-demo, dashboard recovers | `api/events.py`, `frontend/lib/stream.ts` (with P2) | ⬜ |
| B3 | Accountability API polish: window param, performance with 5k events, report fields the UI needs | P1 | - | overview <200ms after backfill | `services/accountability/service.py` | ⬜ |
| F1 | Mission-control look: dark theme, top bar status, agent list with risk meters | P2 | - | a judge understands the state without reading text | `app/page.tsx`, `components/layout`, `components/agents` | ✅ Kiernan |
| F2 | **Agent mesh graph**: fixed layout, per-event edge animation (green/red), quarantine isolation, ghost node for unknown actors | P2 | - | compromised scenario is visually obvious | `components/graph/*` | ✅ Kiernan |
| F3 | Live feed + inspector: identity vs behavior split, risk before→after, signals, AI reason | P2 | - | incident click shows the full "why" | `components/activity`, `components/agents/Inspector.tsx` | ✅ Kiernan |
| F4 | **Permission decay UI**: countdown bar, expire animation, dashed temp-grant edge | P2 | - | expiry visible from across the room | `Inspector.tsx`, new `components/permissions/` | ✅ Kiernan |
| F5 | **Accountability page**: fleet table w/ hypothesis badges, agent report (findings, reasons, scopes, risk sparkline), audit log filters | P2 | B3 | step 5 of DEMO.md works | `app/accountability`, `components/accountability/*` | ✅ Kiernan |
| I1 | Run everything locally; walk each scenario from the CLI (pair with P1) | I | - | can explain each step's decision | `simulator/` | ✅ Ishan |
| I2 | Scenario polish: pacing, captions, expectations; keep smoke green | I | I1 | `make smoke` passes 3× in a row | `simulator/sentinel_sim/scenarios/*` | ✅ Ishan |
| I3 | History backfill stories (see file docstring) | I | I1 | overview shows all 5 intended hypotheses | `scenarios/history_backfill.py`, `world.yaml` | ✅ Ishan |
| I4 | Demo controls: captions/progress from `GET /runs`, keyboard toggle, reset flow | I | - | presenter can run the demo with only this panel | `components/demo/DemoControls.tsx` | ✅ Kiernan (for Ishan) |
| I5 | Rehearsal owner: run DEMO.md end-to-end, log every glitch as a task | I | all | 3 clean run-throughs | `docs/DEMO.md` | 🟨 Ishan |

### ANS setup checklist (S1 + S2) — full runbook in `docs/ANS.md`

The `reference.py` adapter is written to the ANS v2 spec but has **never run against a live ANS stack**.
This is the critical path (surprises hide here). It's all local now — no GoDaddy PAT, no public DNS.

**S1 — stand up ANS + register agents** (needs Go 1.26+, openssl, curl, jq):
- [ ] `git clone github.com/agentnameservice/ans && cd ans && make build`
- [ ] `scripts/demo/start.sh` → confirm `ans-ra` :18080 and `ans-tl` :18081 respond at `/docs`
- [ ] register the 5 hospital agents (reference-impl tooling / `run-lifecycle.sh` as a template)
- [ ] paste each real `agentId` into the matching `ansMockRegistry` entry in `world.yaml`
- [ ] register 1 impostor agent OR leave it unregistered so it resolves NOT_FOUND
- [ ] ensure the `ans-verify` binary is on PATH (or set `ANS_VERIFY_BIN`)

**S2 — validate `reference.py` against the live stack** (fix the code if any assumption is wrong):
- [ ] confirm the TL badge JSON key for lifecycle status (code assumes `status`)
- [ ] confirm the `ans-verify` success output (code assumes exit 0 + a line containing `VERIFIED`)
- [ ] set `ANS_MODE=real` in `.env`, restart backend, run `make smoke`
- [ ] verify: 5 agents `verified=true` + `tlVerified=true`, impostor `NOT_FOUND`, top bar "ANS LIVE"
- [ ] (optional/P2) swap the world-registry map for real `_ans` DNS TXT resolution via `ans-dns`

Until S1/S2 are done, run everything in `ANS_MODE=mock` — the full demo works on mock.

## P1: high value

| Task | Owner | Notes |
|---|---|---|
| Gemini accountability summary per agent (cached) | P3 | fill `AgentReport.summary`; label source |
| Bounded `AI_ASSESSMENT` signal from validated Gemini output (≤ +20, confidence ≥ 0.7) | P3 | deterministic code applies it |
| HIGH risk + sensitive resource → REQUIRE_HUMAN ("restrict") | P3 | `policy/enforcement.py` |
| Proof-of-possession demo: spoofed ANS name without key → deny | P3 | per-agent signing secret; documents the mTLS story |
| Ambient traffic running during the demo | I | `ambient` scenario exists |
| Grant/revoke UI buttons (JIT grant form) | P2 | ✅ Kiernan: grant form in inspector + "fix" button on the accountability report; revoke on grant cards |
| Loading/error/offline states | I, P2 | |
| ✅ Simulator sends `X-Operator-Token` when `OPERATOR_TOKEN` is set | I | operator routes (reset/grant/resync) are open while it's empty; set it and `make smoke` + demo buttons fail |
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
