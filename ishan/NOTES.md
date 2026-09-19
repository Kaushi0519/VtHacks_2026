# Ishan's notes: everything open

One place for every glitch I've found and every change I want. Role and task plan live in
[Ishan.MD](Ishan.MD). Last updated 2026-09-19.

Status: 🔴 needs someone else · 🟡 mine to do · ✅ done (kept only as a one-liner at the bottom)

---

## 🔴 Waiting on other owners

### G4 — "open" in the accountability Incidents list looks like a button (Person 2 / Kiernan)
In an agent report, each incident row ends with the word `open`. That's the incident **status**
(`AgentReportPanel.tsx`, `{i.status}`), not a control, but the title beside it is truncated, so it
reads like "show more" and clicking does nothing. I clicked it repeatedly before reading the code;
a judge will too. Suggestion: style status as a badge (● OPEN / RESOLVED) and make the row itself
open the incident — a long incident title currently can't be read in full anywhere on that page.

### R1 — bigger central mesh panel (Person 2, cheap and very visible)
The inspector steals the mesh's height: `app/page.tsx` rows are `auto_1fr_auto_auto` and
`<Inspector />` sits in an `auto` row, so selecting a node shrinks the `1fr` mesh row. Side columns
are fixed at `260px` / `380px`. Options: cap the inspector height (`max-h-[35vh]` + scroll), move it
into the right column as a slide-over, or narrow the side columns on smaller screens.
**Done when:** the mesh stays readable from across the room with an agent selected.

### R3 — mesh navigation: pan bounds + recenter button (Person 2, cheap)
The mesh pans freely (drag on, scroll-zoom off) and auto-fits only when the panel resizes or a node
appears (`components/graph/AgentMesh.tsx`). Drag past the agents and you get an empty canvas with no
way back except a resize.
- **Bound the pan:** React Flow's `translateExtent`, computed from the nodes' bounding box plus a
  margin. It grows with the mesh, so a 50-agent tenant still has room to explore.
- **Recenter button:** a small "⌖ Recenter" calling the existing `fitView(FIT)`
  (`<Controls showFitView>` or a custom button), plus a presenter keyboard shortcut.
- **Not an auto-recenter on inactivity.** On stage the presenter often points at a node without
  touching the mouse, and a timer snap would yank the view mid-sentence. In a large mesh, operators
  pan deliberately, and an idle snap fights them.
**Done when:** you can't lose the mesh by dragging, and one click always brings it back.

### R2 — tunable risk policy per tenant (Person 3 semantics · Person 1 endpoint · Person 2 UI)
*Stretch: only after P0 is green.* Different companies weigh the same behavior differently: a finance
firm may want an out-of-role request to count heavily and linger; a low-activity system (building
plumbing) may not. Everything tunable already lives in one object, `RiskPolicy`
(`backend/app/models/policy.py`), seeded from `world.yaml` and read-only via `GET /api/system`.

| Knob | Default | Fires when |
|---|---|---|
| `cooldownPerMinute` (recovery rate) | 1.0 / min | risk cools toward baseline while the agent behaves (`cooled_score`, `behavior/risk.py`) |
| `weightForbiddenScope` | +35 | request is outside the agent's role ("outside its domain") |
| `weightNewSensitiveResource` | +20 | first touch of high/critical data it holds no grant for |
| `weightRateSpike` | +15 | > 3× its normal request rate in 60s |
| `weightUnexpectedPeer` | +15 | calls an agent it has never talked to |
| `weightRepeatedDenials` | +10 | 3rd denial within 5 min |
| `weightExpiredGrantUse` | +5 | tries a grant that has decayed |
| `weightHoneypot` | +50 | touches a decoy resource |

A single in-role request with no grant (`NO_GRANT`) adds nothing on its own today; it only counts
through `REPEATED_DENIALS`. If tenants want that to cost points, it needs a new signal (P3).

**Proposal:** a settings page with a slider per knob plus presets (Strict / Standard / Relaxed),
hand-picked and labeled as such. A heuristic, not a calibrated model.

**Guardrails — these are what make it survive judges' questions:**
- **Contract change.** Needs a write endpoint (e.g. `PATCH /api/system/risk-policy`): Pydantic model,
  `frontend/types/sentinel.ts` and `docs/API.md` in one commit, reviewed by Person 1.
- **Operator-only and audited.** Gate it like the other operator routes (`OPERATOR_TOKEN`) and append
  an audit event per change (who, when, old → new). Otherwise lowering weights quietly disables
  detection.
- **Bounded.** Clamp each weight (e.g. 0–50) and warn when a setting makes quarantine unreachable for
  the reference compromise pattern ("with these weights it peaks at 62 and never quarantines").
- **Past decisions don't change.** Every stored event records the weight of each signal that fired, so
  history stays explainable. Only new requests use new weights.
- **Demo safety.** `POST /api/admin/reset` must restore defaults, or `make smoke` and the scripted
  8 → 23 → 78 → quarantine story drift.
- Quarantined agents stay frozen regardless of the recovery rate.

**Open question (P3):** recovery is per wall-clock minute; for low-activity agents, per N clean
requests may fit better. `RATE_SPIKE` already scales with each agent's `expectedRpm`.
**Optional, very visible:** a "what-if" preview replaying the compromised-agent sequence against the
draft weights before saving.

---

## 🟡 Mine to do

- **Gemini key.** `.env` is still `GEMINI_MODE=mock` with the stale `gemini-3.5-flash`. Demo steps
  5c/5d (semantic quarantine) only fire on real Gemini. Key: aistudio.google.com/apikey →
  `GEMINI_MODE=real`, `GEMINI_API_KEY=…`, `GEMINI_MODEL=gemini-flash-lite-latest`, restart backend.
- **I5 rehearsals:** 0 of 3 clean runs. Still to cover: steps 0–6 live with the demo bar
  (keys 1/2/3, A, R, D), recovery drills (reset mid-demo, simulator down, backend restart), then a
  backup screen recording.
- **Simulator + `OPERATOR_TOKEN`:** operator routes (reset/grant/resync) are open while the token is
  empty. If anyone sets it, `make smoke` and the demo buttons break until the simulator sends
  `X-Operator-Token`. Already a P1 row on the task board.

## ⚠️ Known hazard during the demo
`make backend` freezes after any backend file change (e.g. `git pull`) while a dashboard is open:
uvicorn's `--reload` waits for the dashboard's SSE stream, which never closes. Symptom: everything
hangs, no error. Fix: Ctrl+C in the backend tab, then `make backend`. Permanent fix is
`--timeout-graceful-shutdown 2` in the Makefile's `backend` target — verified locally, reported to
Person 1, their call.

## Not a bug (say it in the demo)
Clicking an agent in the mesh shows its **current** identity/behavior; clicking a decision in the
live feed shows the state **at that request** (`IdentityCard` takes `atRequest`; `BehaviorCard` shows
that event's risk before→after). Intentional, and it's the whole point: an agent can be verified at
10:02 and quarantined at 10:04.

---

## ✅ Closed
- **G1** — `DEMO.md` step 3 claimed "risk under 10"; SchedulingAgent opens ~27 after backfill. Fixed
  in the script by me.
- **G2** — same agent showed 27 on the dashboard card and 7 in accountability. Fixed by Kaushal
  (`be3fa4f`): the overview now carries both `riskScore` (live) and `peakRisk` (worst in window).
- **G3** — PayrollAgent wrongly flagged over-privileged, because `payroll.salary.write` needs human
  approval so its grant never recorded a use. Fixed by Kaushal (`8b2748b`, with tests). Verified:
  PayrollAgent is `healthy` and AnalyticsAgent is the only over-privileged agent.
