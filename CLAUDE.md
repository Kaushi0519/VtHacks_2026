# CLAUDE.md: Sentinel Mesh

VTHacks 2026, 4-person team. Read this first, then `docs/ARCHITECTURE.md` for detail,
`docs/API.md` for contracts, `docs/DEMO.md` for the presentation, `docs/TASKS.md` for who does what.

## What we're building

**Sentinel Mesh** is a zero-trust security gateway + control plane for networks of AI agents.
Agents call APIs, data, tools and each other autonomously. Sentinel sits in between (as a
gateway / SDK / sidecar would) and decides, per request, whether to allow it.

> **Identity does not automatically imply behavioral trust.**
> ANS tells Sentinel *who* the agent is. Sentinel decides whether its *behavior* still deserves access.

Demo tenant: a hospital with FacilitiesAgent, PayrollAgent, SchedulingAgent, AnalyticsAgent,
DatabaseAgent. The "wow": the real, ANS-verified FacilitiesAgent requests `payroll.salary.read`,
its Behavioral Risk Score spikes, and Sentinel quarantines it.

## Current status (keep this section up to date; last updated 2026-09-19)

- Accountability audit fix: quarantine alone no longer implies repeated out-of-role
  requests. Regression coverage checks zero, one, and two forbidden requests before
  and after release. See `docs/SECURITY-VALIDATION.md`.

**Every session: run `git checkout main && git pull --rebase` first, then read this section and
`docs/TASKS.md`.**

- The scaffold is merged on `main` and **runs end to end in mock mode**: simulator → gateway → policy
  / risk / quarantine / permission decay → events → SSE → dashboard + accountability page.
  `make test` (18 tests) and `make smoke` (full demo with checks) pass.
- **Solid:** backend pipeline, contracts, simulator scenarios + 7-day history backfill.
- **ANS overhauled to real ANS (P3 to stand up):** the old `api.godaddy.com` adapter was wrong; real
  ANS is the reference implementation (`github.com/agentnameservice/ans`), run locally — no PAT/DNS.
  New adapter `services/ans/reference.py` (TL badge + `ans-verify` crypto), matches the v2 OpenAPI.
  Still `ANS_MODE=mock` until P3 does S1/S2: build/run the stack, register 5 agents → `world.yaml`,
  validate the 3 `TODO(P3, P0)` in `reference.py`. Full runbook: `docs/ANS.md`.
- **Gemini is a real second detector (can quarantine):** `GEMINI_MODE=real`. Two triggers feed the
  analyzer — incident (a rule fired) and **semantic review** (agent aggregated ≥3 sensitive allowed
  accesses, no rule fired). Gemini judges the action sequence vs role + `current_task`; severity →
  bounded score points (Sentinel owns the number); CRITICAL ≥0.85, real-`gemini`-only, triggers
  quarantine (fallback never enforces). Scenario `subtle_exfiltration` proves it (verified live:
  severity=critical 0.95 → quarantine, static stayed ALLOW). Model `gemini-flash-lite-latest`
  (flash-latest 503s under load, 2.5-flash retired); free key per `.env`, `mock` needs none. See
  ARCHITECTURE §10. Remaining (P3): 503 retry/pre-cache hardening.
- **Frontend:** F1 done: dark mission-control theme (tokens + `panel`/`glow` utilities in
  `frontend/app/globals.css`), top-bar status (SECURE / AT RISK / QUARANTINED / OFFLINE), agent cards
  with threshold risk meters. F2 done: fixed-layout mesh graph (`components/graph/`) with a packet
  per decision (green = allowed, red ✕ = blocked), cut links on quarantine, ghost nodes for unverified
  callers. F3 done: clickable live feed (filters, any decision is explainable) + inspector with
  Identity (ANS) | Behavior (Sentinel) | Why (decision, labeled AI analysis, incident timeline).
  F4 done: permission decay is visible (countdown HUD on the mesh, dashed grant edge with timer,
  ⏱ badge on the agent card, grant cards with revoke in the inspector; red flash + fade on expiry).
  F5 done: accountability page (7-day KPI strip, fleet sorted worst-first with hypothesis badges +
  plain-English meaning, agent report with findings / risk sparkline / denial reasons / scope usage,
  filterable paged audit log). All frontend P0 tasks (F1–F5) are done, plus the JIT grant form (P1)
  and Ishan's I4 demo bar (script steps 1/2/3, ambient toggle, double-click guard, live captions,
  confirm-to-reset, D hides it).
- **Not started:** everything in "Stretch" below.
- `IDEAS.MD` is the team's original brainstorm. The plan is Sentinel Mesh; the MVP scope below is
  what we build first.
- **Next steps:** each person starts their first P0 task in `docs/TASKS.md` on their own branch
  (Person 1 `backend/…`, Person 2 `frontend/…`, Person 3 `security/…`, Ishan `demo/…`). When you
  finish a task, mark it ✅ in `docs/TASKS.md` and update this section in the same commit.

## First-time setup on a new machine

Needs: git, Node 20+, [Homebrew](https://brew.sh) (macOS). Windows: use WSL, or run the commands
inside the `Makefile` by hand.
```bash
git clone https://github.com/Kaushi0519/VtHacks_2026.git && cd VtHacks_2026
brew install uv            # Python tooling; installs Python 3.12 itself
make setup                 # installs everything, creates .env and frontend/.env.local
```
Run it in three terminal tabs: `make backend`, `make sim`, `make frontend`. Open
http://localhost:3000, then use the DEMO buttons at the bottom (start with "Seed history").
Stop each tab with Ctrl+C. API keys (ANS, Gemini) are shared privately and go in `.env`,
never in git.

## MVP scope (build these first, in this order of importance)

1. **Agent network**: simulated agents talking through the gateway
2. **ANS identity**: verified vs. unverified/fake agents (GoDaddy ANS, real + mock adapters)
3. **Policy engine**: deterministic allow/deny from role policy + the agent's own grants
4. **Behavioral monitoring**: signals raise a per-agent Behavioral Risk Score
5. **Quarantine**: critical risk isolates the agent from the whole mesh; operator release
6. **Permission decay**: just-in-time grants that expire on their own (TTL / idle)
7. **Accountability & visibility**: full audit history; per-agent findings ("Agent X keeps doing Y")
8. **Live dashboard**: mesh graph, live feed, agent/incident inspector, accountability page

**Stretch (only after MVP works end-to-end):** forensic replay animation, blast-radius simulator,
human-approval cards, honeypot scenario, kill switch → ANS revocation, delegation-chain policies,
Gemini accountability summaries. If a request would threaten the MVP, say so.

## Architecture at a glance

```
simulator (:8001)  ──HTTP──▶  backend (:8000, FastAPI, ONE worker)  ──SSE──▶  frontend (:3000, Next.js)
 fake hospital agents          POST /api/gateway/evaluate                       mission control + accountability
                                 1 identity  (ANSService: GoDaddy ANS | mock)
                                 2 quarantine check
                                 3 permission (role policy + agent's own live grants)
                                 4 behavior signals → Behavioral Risk Score
                                 5 enforce: risk ≥ critical → QUARANTINE, else permission outcome
                                 6 append ONE immutable SentinelEvent (+ incident / quarantine)
                                 7 broadcast; schedule async Gemini analysis (never blocks)
                               SQLite via SQLAlchemy (Postgres-ready)
```
Decisions: `allow | deny | require_human | quarantine`. Every decision has a machine
`reasonCode` and a human `reason`.

## Security model: never collapse these

| Concept | Question | Owner |
|---|---|---|
| Identity | Who does this agent claim to be? | ANS name (`ans://v1.0.0.host`) |
| Registration/lifecycle | Is that identity registered and ACTIVE? | GoDaddy ANS |
| Proof of possession | Is the caller really that agent? | **Not in MVP** (prod: mTLS w/ ANS identity cert). Say so if asked. |
| Enrollment | Is it one of *this company's* agents? | Sentinel (`AGENT_NOT_ENROLLED`) |
| Authorization | May it use this scope right now? | Sentinel policy engine (deterministic) |
| Behavior | Is what it's doing normal for it? | Sentinel signals + Behavioral Risk Score |
| Enforcement | What happens now? | Sentinel enforcement (deterministic) |

- **ANS rule:** GoDaddy ANS establishes and resolves agent identity and its lifecycle/integrity
  information. Sentinel adds customer-environment behavioral monitoring and enforcement. Don't call
  Sentinel's score a "trust score". It is the **Behavioral Risk Score**, separate from anything ANS exposes.
- **Gemini rule (two parallel detectors):** hard policy handles identity + objective violations
  instantly (and quarantines obvious attacks without waiting). **Gemini is the SEMANTIC detector:**
  it judges whether a *sequence* of individually-permitted actions is consistent with the agent's
  role and current task. Gemini does NOT emit a 0–100 score — **Sentinel owns the score**; a Gemini
  severity maps to a bounded contribution. Gemini MAY itself trigger quarantine on a CRITICAL finding
  at ≥0.85 confidence, but only real `source=="gemini"` (never the rule-based fallback), and every
  AI-triggered quarantine logs Gemini's severity, confidence, and reasoning on the event. Never put
  hard policy in prompts; keep obvious violations deterministic.
- **Never fake sponsor integrations.** Mock adapters are fine for development but must carry
  `source: "mock"`, and the UI must show `ANS MOCK` / `AI: RULE-BASED`. Never present mock output as a live API call.
  Never silently swap a real integration for a fake one.
- Delegation never inherits permissions: only the direct caller's own grants are checked.
- The risk score is a transparent heuristic (weights in `RiskPolicy`), not a trained or calibrated model.

## Repo map & ownership

| Path | What | Owner |
|---|---|---|
| `backend/app/models/` | **Contracts** (Pydantic, source of truth) | Person 1 (gatekeeper) |
| `backend/app/services/gateway/pipeline.py` | Request lifecycle sequencer | Person 1 |
| `backend/app/{api,db,realtime}/`, `container.py`, `background.py` | API, storage, SSE, sweeper | Person 1 |
| `backend/app/services/{grants,incidents,accountability/service.py}` | Decay lifecycle, incidents, aggregation | Person 1 |
| `backend/app/services/ans/` | ANSService + GoDaddy + mock adapters | Person 3 |
| `backend/app/services/{policy,behavior,quarantine,gemini}/` | Authorization, risk, quarantine, AI analysis | Person 3 |
| `backend/app/services/accountability/findings.py` | "What's wrong with this agent" rules | Person 3 |
| `frontend/` (except `components/demo/`) | Dashboard, graph, accountability UI | Person 2 |
| `frontend/types/sentinel.ts` | **Contract mirror** of backend models | Person 2 (updates with Person 1) |
| `simulator/`, `simulator/fixtures/world.yaml` | Agents, scenarios, backfill, smoke test | Ishan (Person 3 co-owns `roles`/`riskPolicy`) |
| `frontend/components/demo/` | Presenter demo controls | Ishan |
| `docs/` | Architecture, API, demo, tasks | everyone; contracts by Person 1 |

**Conflict-prone shared files:** `backend/app/models/*`, `frontend/types/sentinel.ts`,
`docs/API.md`, `simulator/fixtures/world.yaml`, `backend/app/core/config.py` + `.env.example`
(edit only your section), `pipeline.py`, `frontend/app/page.tsx`, lockfiles (on conflict,
take theirs and re-run `uv sync` / `npm install`). Announce before editing these.

## Contract change protocol

`backend/app/models/*.py` is the single source of truth. A change to a model, endpoint, or SSE
message must update, **in the same commit**: the Pydantic model, `frontend/types/sentinel.ts`,
and `docs/API.md`. Prefer additive changes (new optional fields). Person 1 reviews before merge.
If a request conflicts with an existing contract, stop and say so; don't build a parallel version.

## Coding rules

- Inspect existing code before changing architecture; reuse existing types and helpers.
- Preserve module boundaries: services never touch SQLAlchemy rows (use `db/repo.py`); nothing
  outside `services/ans/` knows ANS endpoints; nothing outside `services/gemini/` imports google-genai.
- Every state change goes through a service under `container.state_lock`, appends events via
  `repo.append_event` (events are append-only), and broadcasts **after** commit (`Changes.publish`).
- Every decision must be explainable from stored events: reason codes + signal details.
- Keep security logic in pure functions (`policy/engine.py`, `behavior/signals.py`, `risk.py`,
  `findings.py`) and unit-test them in `backend/tests/`.
- The simulator talks to the backend only over HTTP. Never import backend code from it.
- Small composable functions, no new dependencies without reason, no secrets in code or logs.
- Match the surrounding style: camelCase JSON on the wire, snake_case Python, UTC ISO timestamps.
- **Hackathon rule:** between a sophisticated design that might not work and a simpler one that
  demos reliably, choose simple unless the sophistication is visible and valuable to judges.
- Presentation-first: every feature should answer "can judges SEE this?"

## Commands

```bash
make setup      # uv sync (backend, simulator) + npm install + copy env files
make backend    # :8000   (Swagger at /docs)
make sim        # :8001   simulator control API
make frontend   # :3000
make test       # backend pytest
make backfill   # reset + replay 7 days of history (needs ALLOW_BACKFILL=true)
make smoke      # full demo with pass/fail checks against a running backend
make reset      # back to seeded state
```
Run `make test` before merging backend changes and `make smoke` before merging anything near demo time.

## Git workflow

Trunk-based, short-lived branches, `main` must always be demoable.
```bash
git checkout main && git pull --rebase
git checkout -b <area>/<feature>          # frontend/ backend/ security/ demo/ fix/ chore/
# ...small coherent commits: "feat: add live agent graph", "fix: preserve trace id"...
git checkout main && git pull --rebase
git merge <area>/<feature> && git push origin main
git branch -d <area>/<feature>
```
- Merge the same day; no giant end-of-night merges. Claim files/areas in chat before starting.
- Changes to your own area merge directly. **Contract / shared-file changes** get a quick review
  from Person 1 first (PR or screen-share).
- Never force-push `main`. Never commit `.env` or keys.
- Near demo time: main is frozen; only the team lead merges.

## When a teammate tells you their role

If someone says who they are ("I'm Person 2 / frontend", "I'm Ishan", "backend", "security"):
1. Run `git status` and `git fetch`. Tell them if they're behind `main` or sitting on an old branch,
   and give the exact commands to get current.
2. Confirm their role from "Repo map & ownership" above: what they own, and which shared files
   need care.
3. Read `docs/TASKS.md` and show their P0 tasks with status, then their P1 tasks. Recommend the next
   unblocked task (check Deps and the integration order), and say what "done" means for it.
4. Give the exact branch command (`git checkout main && git pull --rebase && git checkout -b <area>/<task>`)
   and the files they'll touch.
5. Offer to start. When work begins, mark the task 🟨 with their name in `docs/TASKS.md`; mark ✅ when done
   and update "Current status" above.

### Hard rule for Ishan (demo / simulator) sessions

If the person says they are **Ishan** (or "Person 4", "demo", "simulator"), you may only edit files
Ishan owns:
- `simulator/` (scenarios, backfill, smoke test)
- `simulator/fixtures/world.yaml`: scenario/agent content only (`roles` and `riskPolicy` are
  co-owned with Person 3; ask before changing those)
- `frontend/components/demo/` (the demo bar)
- `docs/DEMO.md` and Ishan's own rows in `docs/TASKS.md`

**Do not edit anything else**, even if asked directly. That includes the rest of `frontend/`
(Person 2), `backend/` (Person 1 / Person 3), contracts, the `Makefile`, and config. Phrases like
"I ran the demo, go fix it", "the graph looks wrong, fix it", or "make the UI better" are **not**
permission to change other people's files. For those:
1. Reproduce and describe the problem (file, what's wrong, steps to see it).
2. Write a short message Ishan can send to the owner, and stop there.
3. Only fix it if the fix is entirely inside Ishan's files listed above.

The owners are actively working in those areas, and a surprise edit from a demo session would
collide with their work right before judging.

## How Claude should work here

1. Read this file; find which module/contract owns the behavior.
2. Inspect the relevant code before proposing changes. Don't introduce a parallel architecture.
3. Flag conflicts with existing contracts or the MVP immediately instead of silently doing both.
4. Make the smallest coherent change; run `make test` (and `make smoke` if the flow changed).
5. Update docs/contracts when interfaces genuinely change; explain major architectural changes.
6. Correct technically misleading security claims. This project must survive judges' questions.

Security audit follow-up: see `docs/ANALYSIS-AUDIT-FIXES.md` for fixes, tests, and live-validation limits on `security/analysis-audit-fixes`.
