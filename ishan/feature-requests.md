# Feature requests for teammates (proposed by Ishan)

Sent to owners as messages; this file is the full write-up. Owners decide.

| ID | Request | Suggested owners | Priority |
|---|---|---|---|
| R1 | Bigger central mesh panel, especially with an agent selected | P2 | P1 (cheap, very visible) |
| R2 | Tunable risk policy per tenant: recovery rate + signal weights (settings sliders + presets) | P3 (semantics), P1 (endpoint + contract), P2 (UI) | P2 (after P0 is green) |
| R3 | Mesh navigation: pan bounds + a "recenter" button | P2 | P1 (cheap) |

### R1: bigger central mesh panel
The inspector steals the mesh's height: `app/page.tsx` rows are `auto_1fr_auto_auto` and
`<Inspector />` sits in an `auto` row, so selecting a node shrinks the `1fr` mesh row. Side columns
are fixed at `260px` / `380px`. Options: cap the inspector height (`max-h-[35vh]` + scroll), move it
into the right column as a slide-over, or narrow the side columns on smaller screens.
**Done when:** the mesh stays readable from across the room with an agent selected.

### R2: tunable risk policy per tenant (recovery rate + signal weights)
Different companies weigh the same behavior differently: a finance firm may want an out-of-role
request to count heavily and linger; a low-activity system (e.g. building plumbing) may not.
Everything to tune already lives in one object, `RiskPolicy` (`backend/app/models/policy.py`),
seeded from `world.yaml` `riskPolicy` and read-only today via `GET /api/system`.

**What to expose** (current defaults):

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

Note: a single in-role request with no grant (`NO_GRANT`) adds nothing on its own today; it only
counts through `REPEATED_DENIALS`. If tenants want that to cost points, it needs a new signal (P3).

**Proposal:** a settings page with a slider per knob plus presets (e.g. Strict / Standard / Relaxed).
Preset values are hand-picked and labeled that way. This is a heuristic, not a calibrated model.

**Guardrails (these are what make it survive judges' questions):**
- **Contract change.** Needs a write endpoint (e.g. `PATCH /api/system/risk-policy`), so the Pydantic
  model, `frontend/types/sentinel.ts` and `docs/API.md` change in one commit, reviewed by Person 1.
- **Operator-only and audited.** Gate it like the other operator routes (`OPERATOR_TOKEN`), and
  append an audit event for every change (who, when, old → new). Otherwise lowering weights is a
  quiet way to switch detection off.
- **Bounded.** Clamp each weight (e.g. 0–50) and warn when a setting makes quarantine unreachable
  for the reference compromise pattern (e.g. "with these weights, the compromised-agent sequence
  now peaks at 62 and never quarantines").
- **Past decisions don't change.** Every stored event already records the weight of each signal
  that fired, so history stays explainable after a change. Only new requests use new weights.
- **Demo safety.** `POST /api/admin/reset` must restore defaults, or `make smoke` and the scripted
  8 → 23 → 78 → quarantine story drift.
- Quarantined agents stay frozen regardless of the recovery rate.

**Open design question (P3):** recovery is per wall-clock minute. For low-activity agents, recovering
per N clean requests may fit better. `RATE_SPIKE` already scales with each agent's `expectedRpm`.
**Optional, very visible:** a "what-if" preview that replays the compromised-agent sequence against
the draft weights before saving.

### R3: mesh navigation (pan bounds + recenter button)
Today the mesh pans freely (drag is on, scroll-zoom is off) and auto-fits only when the panel
resizes or a node appears (`components/graph/AgentMesh.tsx`). Dragging past the agents leaves an
empty canvas with no way back except a resize.

- **Bound the pan:** React Flow's `translateExtent`, computed from the nodes' bounding box plus a
  margin. It grows with the mesh automatically, so a 50-agent tenant still has room to explore.
- **Recenter button:** a small "⌖ Recenter" control that calls the existing `fitView(FIT)`
  (React Flow `<Controls showFitView>` or a custom button). A keyboard shortcut for the presenter
  can come with I4.
- **Not an auto-recenter on inactivity.** On stage the presenter is often pointing at a node without
  touching the mouse, and a timer snap would yank the view mid-sentence. In a large mesh, operators
  pan deliberately to inspect one area, and an idle snap fights them.
**Done when:** you can't lose the mesh by dragging, and one click always brings it back.

