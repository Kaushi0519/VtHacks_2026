# I5 rehearsal log (owner: Ishan)

Every glitch found while running `docs/DEMO.md` end to end. Fixes inside Ishan's files are made
here; anything else goes to its owner as a message and is listed with "sent to".

## Run 1 — 2026-09-19, mock ANS, rule-based analyzer

Setup: `make backfill` (7 days) on a freshly restarted backend. `make smoke` green beforehand.

### G1 — SchedulingAgent opens at risk 27, but the script says "under 10" (fixed here)
`DEMO.md` step 3 said to confirm "all five agents green, risk under 10". After the backfill,
SchedulingAgent sits at **27** because of its 12 denied `payroll.hours.write` attempts. Still LOW
(elevated starts at 30), so the mesh is green and the story holds — the script's expectation was
just wrong. **Fixed:** step 3 now states the expected number. Worth saying out loud in the demo:
that agent is *supposed* to look slightly off, and step 5 explains why.

### G2 — Same agent shows two different risk scores (sent to Person 1)
The dashboard agent card shows SchedulingAgent at **27**; the accountability overview shows **7**
for the same agent in the same window. The overview appears to report the cooled/baseline score,
while `GET /api/agents` returns the stored score, which only recalculates on the agent's next
request. A judge comparing the two screens would see a contradiction.

### G3 — PayrollAgent is flagged "over-privileged" and shouldn't be (sent to Person 3, cc Person 1)
Step 5 expects exactly one over-privileged agent (AnalyticsAgent, never uses `building.energy.read`).
PayrollAgent now also appears, which dilutes the story.

Cause: `payroll.salary.write` is in `requiresHuman` for the payroll resource, so those requests
return `require_human` and never execute. `UNUSED_STANDING_GRANT` (`accountability/findings.py`)
flags baseline grants whose `last_used_at` is unset, and grant usage is only touched on ALLOW.
This changed with the audit fix in `1ef2dab` ("require_human no longer touches the grant"), which
is correct on its own — a request that executed nothing shouldn't refresh access. The finding rule
just needs to know the difference between "never needed it" and "asked and is waiting on a human".

Not fixable inside Ishan's files: it's `findings.py` (Person 3) or the `payroll` role in
`world.yaml` (co-owned with Person 3).

### Verified good
- All 5 backfill stories resolve: `scheduling-agent` likely_misconfigured, `analytics-agent`
  over_privileged, `facilities-agent` + `database-agent` healthy, and both unknown actors
  (`payroll-sync-bot`, `partner-courier`) unverified_identity.
- 7-day totals: 261 requests, 238 allowed, 16 denied, 4 identity failures, 2 incidents.
- `make smoke` passes 5/5 scenarios against current `main`.

## Still to rehearse
- [ ] Steps 0–6 live against the dashboard with Kiernan's demo bar (keys 1/2/3, A, R, D)
- [ ] Recovery drills: reset mid-demo; simulator down; backend restart
- [ ] 3 clean run-throughs + backup screen recording
