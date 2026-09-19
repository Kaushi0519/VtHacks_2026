# Ishan — role, ownership, and next steps

My working file for Sentinel Mesh. Source of truth stays `CLAUDE.md` + `docs/TASKS.md`;
this is my lane in one page. Last updated 2026-09-19.

## What I own

I'm **Person "I" — demo & simulation owner**. Everything the judges *experience* is mine;
the security internals belong to Person 1 (backend/contracts) and Person 3 (ANS/policy/risk/AI).

| Path | What it is |
|---|---|
| `simulator/sentinel_sim/scenarios/*` | The 6 scenarios that drive the whole demo |
| `simulator/sentinel_sim/{scenario,server,client,world}.py` | Scenario model, runner, control API (:8001) |
| `simulator/fixtures/world.yaml` | Agents, roles, resources, `riskPolicy` (Person 3 co-owns `roles` + `riskPolicy`) |
| `frontend/components/demo/DemoControls.tsx` | The presenter panel I drive the demo from |
| `docs/DEMO.md` | The 3-minute script — I own it, and I own rehearsing it |

Hard rule from `CLAUDE.md`: **the simulator only talks to the backend over HTTP.** Never import
backend code into `simulator/`. It's a customer of the public gateway API, and that's part of the pitch
("how do customers integrate?" → *exactly like this*).

## Where the project is right now

The scaffold is merged and runs end to end on mock ANS: simulator → gateway → policy/risk/quarantine/decay
→ events → SSE → dashboard. `make test` (18) and `make smoke` pass. The frontend is functional but
unstyled (Person 2's job). Real ANS and real Gemini are written but unverified (Person 3's S1–S3).

**Nothing blocks me.** My P0 tasks I1, I2, I4 have no dependencies on anyone else's work.

## My P0 tasks (from `docs/TASKS.md`)

| ID | Task | Deps | Done when |
|---|---|---|---|
| **I1** | Run everything locally; walk each scenario from the CLI, pair with Person 1 | — | I can explain *every* decision in every scenario out loud |
| **I2** | Scenario polish: pacing, captions, expectations | I1 | `make smoke` passes 3× in a row |
| **I3** | History backfill stories | I1 | `/accountability` shows all 5 intended hypotheses |
| **I4** | Demo controls: captions/progress from `GET /runs`, keyboard toggle, reset flow | — | presenter runs the whole demo from this one panel |
| **I5** | Rehearsal owner: run `docs/DEMO.md` end to end, log every glitch as a task | all | 3 clean run-throughs |

P1 (after P0 is green): ambient background traffic during the demo (the `ambient` scenario already
exists — it's `normal_operation.build_ambient`), and loading/error/offline states with Person 2.

## What each task actually means

### I1 — know the machine cold (do this first, ~1 hour)
Three terminals: `make backend`, `make sim`, `make frontend`. Then run each scenario from the CLI
and read the decisions, not just the colors:

```bash
cd simulator
uv run python -m sentinel_sim list
uv run python -m sentinel_sim run normal_operation --check
uv run python -m sentinel_sim run compromised_agent --check   # reset first, see below
```

The bar for "done" is the judge Q&A in `docs/DEMO.md`: for each step I should be able to name the
decision, the `reasonCode`, and *why* the risk moved. The compromised-agent math is already documented
in [compromised_agent.py:3-8](simulator/sentinel_sim/scenarios/compromised_agent.py#L3-L8):

```
burst of 20 lights reads   RATE_SPIKE +15                          ->  23  low
payroll.salary.read        FORBIDDEN_SCOPE +35, NEW_SENSITIVE +20  ->  78  high   DENY
patient.records.read       FORBIDDEN_SCOPE +35                     -> 100  crit   QUARANTINE
building.lights.write      its normal job, still blocked           -> DENY AGENT_QUARANTINED
```

Gotcha that will bite me on stage: **a quarantined agent stays quarantined.** Always `make reset`
before rerunning `compromised_agent`.

### I2 — pacing and captions
Each scenario is a declarative list of steps ([scenario.py:24-75](simulator/sentinel_sim/scenario.py#L24-L75)):
`Note` (caption), `Wait`, `Request` (with `repeat`, `interval`, `pause`, `expect`, `expect_reason`),
`Grant`, `Reset`, `Resync`. `expect`/`expect_reason` is what makes every scenario double as an
integration test — that's why `--check` and `make smoke` work. **Keep expectations on every
meaningful step.** Tuning is mostly `pause`/`interval` (does the room have time to see it?) and
`Note` text (does the caption say the one thing I want them to notice?).

### I3 — the backfill tells five stories
[history_backfill.py:5-10](simulator/sentinel_sim/scenarios/history_backfill.py#L5-L10) lists the
hypotheses the 7 days of history must produce on the accountability page:

- `scheduling-agent` → **likely misconfigured** (keeps asking for `payroll.hours.write`)
- `payroll-sync-bot` → **unverified identity** (never resolvable in ANS)
- `partner-courier` → **unverified identity** (real ANS agent, another org, not enrolled)
- `analytics-agent` → **over-privileged** (standing `building.energy.read` it never uses)
- facilities / payroll / database → **healthy**, so today's anomaly stands out

Nothing is written to the DB directly — every historical event is a genuine pipeline decision replayed
through the gateway with `observedAt` (needs `ALLOW_BACKFILL=true`). That's a *great* judge answer, so
I should keep it that way. This task is "do the numbers actually produce those five badges?" — which I
can't fully confirm until Person 2 ships F5 and Person 1 ships B3.

### I4 — the presenter panel
[DemoControls.tsx](frontend/components/demo/DemoControls.tsx) is 31 lines today: buttons, Stop, Reset.
The TODO in the file is exactly the task — show the live caption and step progress from
`GET /runs` (:8001), and hide the panel behind a keyboard toggle so it isn't on screen during the
pitch. `RunState` already carries everything I need: `caption`, `stepIndex`, `totalSteps`, `status`,
and per-step `results` ([scenario.py:106-118](simulator/sentinel_sim/scenario.py#L106-L118)) — it's
served camelCase specifically for the frontend, so no contract change is needed. Additive only.

⚠️ This file is in Person 2's directory tree (`frontend/`). I own `components/demo/` but I should say
so in chat before touching anything outside it, and **read `frontend/AGENTS.md` first** — this Next.js
version has breaking changes and wants the docs in `node_modules/next/dist/docs/` read before writing code.

### I5 — rehearsal owner
The one that actually wins or loses the hackathon. Run `docs/DEMO.md` top to bottom, 3 clean times,
and file every glitch as a task instead of fixing it live. Record a backup video once it's clean.

## Recommended order

**I1 → I2 → I4 → I3 → I5.** I1 unblocks everything and is pure learning. I2 keeps smoke green (my
regression net for the whole team). I4 is self-contained and makes every later rehearsal faster. I3
needs B3 + F5 to verify. I5 is last by definition, and I should start it *earlier than feels
comfortable* — first full run-through the moment steps 1–3 work, not on demo morning.

There's also **S4** (tune signals/weights so the risk story reads 8 → 23 → 78 → quarantine), which I
share with Person 3. I bring "does this read well from the back of the room?"; they own the weights in
`behavior/*` and `world.yaml riskPolicy`. That conversation should happen after I1.

## Start I1 now

```bash
git checkout main && git pull --rebase
git checkout -b demo/i1-walk-scenarios
```

Then three terminals: `make backend`, `make sim`, `make frontend` → http://localhost:3000 →
"Seed history" button first. When I finish: mark I1 ✅ in `docs/TASKS.md` and update the
"Current status" section of `CLAUDE.md` **in the same commit**.

## Commands I'll live in

```bash
make backend    # :8000  (Swagger at /docs)
make sim        # :8001  control API behind the demo buttons
make frontend   # :3000
make smoke      # reset + backfill + every scenario with pass/fail checks  ← run before every merge near demo time
make backfill   # reset + replay 7 days (needs ALLOW_BACKFILL=true)
make reset      # back to the seeded world
make test       # backend pytest

cd simulator && uv run python -m sentinel_sim list
cd simulator && uv run python -m sentinel_sim run <scenario> --check
```

## Things I must not get wrong

- **Never fake a sponsor integration.** Mock adapters carry `source: "mock"` and the UI says
  `ANS MOCK` / `AI: RULE-BASED`. If ANS or Gemini is down during the demo, I switch to mock, say so
  out loud, and keep going. Getting caught dressing mock output as a live API call ends our run.
- **Never call the risk score a "trust score."** It's the **Behavioral Risk Score**, ours, separate
  from anything ANS exposes. The whole thesis line is: *ANS tells Sentinel who the agent is; Sentinel
  decides whether its behavior still deserves access.*
- **Gemini explains, it never decides.** Deterministic policy decides, off the request path.
- If asked how we stop ANS-name spoofing: our MVP checks registration + lifecycle; production adds
  mTLS with the ANS identity certificate; **we haven't built that**. Say it plainly.
- Announce in chat before editing shared files — `world.yaml`, `frontend/types/sentinel.ts`,
  `docs/API.md`, `pipeline.py`, `backend/app/models/*`, `frontend/app/page.tsx`.
- Merge the same day, short-lived branches, `main` always demoable. Near demo time main is frozen.
