# Demo script (~3 minutes)

## Before judges arrive
1. `make backend`, `make sim`, `make frontend` (three terminals). `.env`: `ALLOW_BACKFILL=true`,
   and `ANS_MODE=real` + `GEMINI_MODE=real` if keys work (the top bar must say **ANS LIVE**).
2. `make backfill` (a week of history), then open `http://localhost:3000`.
3. Confirm: all five agents green, risk under 10, **SYSTEM: SECURE**.
4. Rehearse with `make smoke` at least 3×. Keep a screen recording as backup.
5. Demo bar shortcuts: **1 / 2 / 3** = script steps below, **A** = ambient traffic on/off, **R** = reset
   (press twice), **D** = hide the bar for a clean screen. A step that's already running can't be
   started twice, so a nervous double-click is harmless.

## Script

| # | Say | Click | Judges see |
|---|---|---|---|
| 0 | "Hospitals now run autonomous AI agents that touch payroll, patient records, buildings." | nothing | green mesh, live feed |
| 1 | "Every agent action flows through Sentinel. Identity comes from GoDaddy's Agent Name Service." | **Normal operation** + **Permission decay** (start decay now, it counts down in the background) | green edges, ✓ ALLOW, "ANS VERIFIED"; AnalyticsAgent gets a 45s patient-records grant |
| 2 | "An unknown agent claims to be a payroll sync service." | **Fake agent** | ✕ DENY IDENTITY_UNVERIFIED, ANS status NOT_FOUND, incident linked to earlier probes this week |
| 3 | "Now the hard case: the *real* FacilitiesAgent gets prompt-injected." | **Compromised legitimate agent** | request burst → risk 8→23; payroll.salary.read → DENY, risk 78 HIGH; patient.records.read → **QUARANTINE**, risk 100; node turns red, edges cut; its normal lights request is also denied |
| 3b | **"That agent wasn't fake. ANS verified exactly who it was. Its behavior changed. Identity alone isn't enough."** | click the incident | IDENTITY: VERIFIED vs BEHAVIORAL RISK: 100 CRITICAL; the WHY panel shows Gemini's explanation |
| 4 | "Meanwhile, AnalyticsAgent's temporary access expired. Nobody had to remember to revoke it." | select AnalyticsAgent | grant EXPIRED; its next attempt DENY GRANT_EXPIRED |
| 5 | "And the company can finally see what its agents have been doing." | **Accountability** tab | FacilitiesAgent *possibly compromised*; SchedulingAgent *likely misconfigured* (12 denied payroll.hours.write in 7 days); payroll-sync-bot *unverified identity*; AnalyticsAgent *over-privileged* (never uses building.energy.read) |
| 6 | **"ANS tells Sentinel who the agent is. Sentinel decides whether its behavior still deserves access."** | | |

## If something breaks
- Dashboard stale or odd: **Reset**, then `make backfill`, then rerun from step 1.
- Simulator down: run scenarios from a terminal (`cd simulator && uv run python -m sentinel_sim run compromised_agent`).
- ANS or Gemini down: switch `ANS_MODE`/`GEMINI_MODE` to `mock` and restart the backend. The top bar
  will say MOCK / RULE-BASED. Say so honestly; never present mock output as live.
- A quarantined agent stays quarantined: always reset before rerunning the compromised scenario.

## Judge Q&A prep
- *Is Gemini deciding who gets blocked?* No. Deterministic policy decides; Gemini explains and advises off the request path.
- *How is the risk score computed?* Transparent weighted signals (ARCHITECTURE §7). A heuristic, not a trained model.
- *What stops an agent spoofing an ANS name?* Our MVP checks registration + lifecycle. Production adds mTLS with the ANS identity certificate. We haven't built that yet.
- *Can an attacker train the baseline?* Profiles learn only from allowed requests.
- *Does delegation leak permissions?* No. Each hop is checked against its own grants.
- *How do customers integrate?* Gateway / SDK / sidecar calling `POST /api/gateway/evaluate`; the simulator is exactly such a client.
