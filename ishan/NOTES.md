# Ishan's notes: everything open

One place for every glitch I've found and every change I want. Role and task plan live in
[Ishan.MD](Ishan.MD). Last updated 2026-09-19.

Status: 🔴 needs someone else · ✅ done (kept only as a one-liner at the bottom)

---

## 🔴 Waiting on other owners

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
- **G5 React Flow badge** — hidden by Kiernan (`a54190d`), so nothing links a judge off-product
  mid-demo. Credit React Flow in the README / submission write-up instead.
- **G6 mesh panel goes blank** — fixed by Kiernan (`ee467be` + 3 follow-ups). Root cause was not the
  pan bounds I guessed at: React Flow keeps a node `visibility: hidden` until it has measured it, and
  Chrome freezes the ResizeObserver that measures while the tab is in the background, so the
  measurement never landed and every node stayed hidden. That also explains why RECENTER did nothing
  (no measured nodes -> empty bounds -> fitView bails). Now force-re-measures stuck nodes, re-frames
  on tab return, and re-frames once a second if no node intersects the panel. Verified: switch away
  mid-scenario, come back, mesh is still there.
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
