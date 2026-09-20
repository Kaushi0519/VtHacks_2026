# Ishan's notes: everything open

One place for every glitch I've found and every change I want. Role and task plan live in
[Ishan.MD](Ishan.MD). Last updated 2026-09-19.

Status: 🔴 needs someone else · ✅ done (kept only as a one-liner at the bottom)

---

## 🔴 Waiting on other owners

### G4 — "open" in the accountability Incidents list looks like a button (Person 2 / Kiernan)
In an agent report, each incident row ends with the word `open`. That's the incident **status**
(`AgentReportPanel.tsx`, `{i.status}`), not a control, but the title beside it is truncated, so it
reads like "show more" and clicking does nothing. I clicked it repeatedly before reading the code;
a judge will too. Suggestion: style status as a badge (● OPEN / RESOLVED) and make the row itself
open the incident — a long incident title currently can't be read in full anywhere on that page.

---|---|---|
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

### G5 — "React Flow" badge in the mesh links off to reactflow.dev (Person 2 / Kiernan)
Bottom-right of the mesh panel. It's a live link to `reactflow.dev/remove-attribution`, so a judge
who clicks it leaves our product mid-demo and lands on a third-party site.

Removing it is one prop on `<ReactFlow>` in `components/graph/AgentMesh.tsx`:
```tsx
proOptions={{ hideAttribution: true }}
```
`@xyflow/react` is MIT-licensed, so removing the badge is permitted; React Flow asks that projects
which hide it consider a Pro subscription to support them. Team's call — but for a judged demo I'd
hide it, and we can credit React Flow in the submission write-up and README instead.

### G6 — the mesh panel sometimes goes blank (Person 2 / Kiernan)
**Repro:** click several demo buttons in quick succession and let them run. The mesh panel empties
out, keeping only the background dots and the badge. The agent list, live feed and top bar keep
working, so the app itself is fine. It doesn't come back on its own.

**What that narrows it to:** the three zone headers (UNVERIFIED CALLERS / ENROLLED AGENTS /
RESOURCES) are added to the node list unconditionally, so the node list can never be empty. Their
disappearing means the **viewport** has moved off the nodes, not that the data is gone.

**Two suspects in `AgentMesh.tsx`:**
1. `translateExtent` (the R3 pan bounds) is derived from `nodes`, and `nodes` is recomputed on every
   pulse. So the drag bounds are re-created many times a second during heavy traffic, while
   `fitView` runs from a ResizeObserver *and* from the node-count effect. A clamp landing between
   those two fits could park the viewport outside the bounds with nothing to pull it back.
2. The extent's vertical bounds look asymmetric: the minimum adds `HEADER_Y` (`Math.min(...ys) +
   HEADER_Y - M`) while the maximum doesn't (`Math.max(...ys) + NODE_H + M`). Worth a second look —
   if the two ever cross, the clamp has no valid area.

**Suggested fixes:** memoize the extent from the stable nodes only (graph + ghosts, not pulses);
guard against an inverted extent; and consider refitting on a trailing debounce rather than on every
node-count change.

**Demo workaround until it's fixed:** press **RECENTER** (top-right of the mesh). If that restores
it, suspect 1 is confirmed. Also start scenarios **one at a time** — see the next note.

### G7 — overlapping scenarios break the scripted risk numbers (mine, worth saying out loud)
In the screenshot from the blank-mesh repro, FacilitiesAgent went `40 → 75` then `75 → 100`, but
`DEMO.md` step 3 promises `8 → 23 → 78 → 100`. Nothing is wrong: ambient traffic and a second
scenario were running at the same time, and every extra request feeds the same risk window.
PayrollAgent also sat at 21 instead of 6 for the same reason.
**Rule for the demo: one scenario at a time, ambient off, and reset between runs.** If judges ask
why the numbers differ from the script, the honest answer is that the score reflects everything the
agent did in the window, which is the point of the feature.

### G8 — decoy resource name truncates in the mesh (minor, mine)
The honeypot renders as `finance_master_crede…`. The full name `finance_master_credentials`
(`world.yaml`) is deliberate — a decoy should look like a real secrets file, not like "Honeypot" —
but it's the only node whose label is cut off. Either shorten it (`finance_master_creds`) or ask for
a tooltip. Cosmetic; do it only if nothing more useful is open.

## Not a bug (say it in the demo)
**Two QUARANTINE rows at the same second** in the live feed are correct, not a duplicate. One is the
*request* that crossed the line (carries the action, `RISK_THRESHOLD`, and risk 75→100); the other
is the *lifecycle* event recording that the agent was isolated. The pipeline appends the request
event, then the quarantine service appends its own. Two different facts, both auditable.


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
