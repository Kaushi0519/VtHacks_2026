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
- **Ask Person 1** to add `OPERATOR_TOKEN=` to the simulator section of `.env.example` (config is
  theirs to edit). The simulator reads it already; it's just undocumented for the next person.

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
- **Simulator + `OPERATOR_TOKEN`** (`c3ef115`, mine) — the simulator now sends `X-Operator-Token` on
  operator routes when `OPERATOR_TOKEN` is set; agent traffic never sends it. Verified: 401 without,
  PASSED with.
- **R1 bigger mesh panel** — shipped by Kiernan (`78257c6`).
- **R3 mesh pan bounds + recenter button** — shipped by Kiernan (`655b732`).
- **Simulator + `OPERATOR_TOKEN`** — the simulator now sends `X-Operator-Token` on operator routes
  (grant/reset/resync) when `OPERATOR_TOKEN` is set in its environment; agent traffic through the
  gateway never sends it. Verified against a backend with a token: 401 without, PASSED with.
- **G1** — `DEMO.md` step 3 claimed "risk under 10"; SchedulingAgent opens ~27 after backfill. Fixed
  in the script by me.
- **G2** — same agent showed 27 on the dashboard card and 7 in accountability. Fixed by Kaushal
  (`be3fa4f`): the overview now carries both `riskScore` (live) and `peakRisk` (worst in window).
- **G3** — PayrollAgent wrongly flagged over-privileged, because `payroll.salary.write` needs human
  approval so its grant never recorded a use. Fixed by Kaushal (`8b2748b`, with tests). Verified:
  PayrollAgent is `healthy` and AnalyticsAgent is the only over-privileged agent.
