# Sentinel Mesh Architecture

## 1. System overview

```
┌──────────────────────┐        ┌───────────────────────────────────────────────┐        ┌──────────────────────┐
│ simulator  (:8001)   │  HTTP  │ backend (:8000) FastAPI, single process        │  SSE   │ frontend (:3000)     │
│ hospital agents +    │───────▶│  Gateway pipeline ─ ANSService ─▶ GoDaddy ANS │───────▶│ Mission Control      │
│ scenarios + backfill │        │        │          └ Behavior/Risk ─ Policy    │  REST  │ Accountability       │
│ control API for demo │◀──┐    │        ▼                                       │◀───────│ Demo controls        │
└──────────────────────┘   │    │  SQLite (events, agents, grants, incidents)    │        └──────────────────────┘
          ▲                │    │  Sweeper (permission decay, risk cool-down)    │                  │
          └────────────────┼────│  AnalysisRunner ─▶ Gemini (async, advisory)   │                  │
     demo buttons (REST)   │    └───────────────────────────────────────────────┘                  │
                           └───────────────────────────────────────────────────────────────────────┘
```

Three processes, one backend. The simulator is deliberately **outside** Sentinel: it plays the
customer's agents and reaches Sentinel only through the public gateway API, which is the same shape as
a real SDK / sidecar / proxy integration. Customers do not host agents "inside" Sentinel.

## 2. Request lifecycle (`services/gateway/pipeline.py`)

```
AgentRequest {actorAnsName, action, targetAgentId?, traceId?, parentEventId?, delegationChain[]}
  │
  1 identity    ANSService.verify_agent(ansName)          not verified      → DENY IDENTITY_UNVERIFIED
  │             (network, before the state lock)          ANS down/no cache → DENY IDENTITY_UNAVAILABLE (fail closed)
  │             map ANS name → enrolled agent             not ours          → DENY AGENT_NOT_ENROLLED
  2 quarantine  agent.status == quarantined                                → DENY AGENT_QUARANTINED
  3 permission  evaluate_permission(role, own grants, scope, resource, now)
  │               forbidden for role → denied FORBIDDEN_FOR_ROLE
  │               no live grant      → denied NO_GRANT / GRANT_EXPIRED / GRANT_REVOKED
  │               requires human     → REQUIRES_HUMAN
  4 behavior    compute_signals(ctx) → weights; risk_after = cooled(risk_before) + Σ weights (0..100)
  5 enforce     risk_after ≥ critical → QUARANTINE (RISK_THRESHOLD); else the permission outcome
  6 record      one REQUEST event; incident open/append; quarantine event; grant usage; profile learn
  7 publish     SSE after commit; AnalysisRunner.schedule(incident) → Gemini → ANALYSIS event
```

All state mutation (gateway, sweeper, operator actions, analysis write-back) is serialized by one
`asyncio.Lock`. Throughput needs are tiny and this removes every race on risk scores.

## 3. Data model (Pydantic in `backend/app/models/`, the source of truth)

| Model | Purpose |
|---|---|
| `Agent` | enrolled agent: role, ANS name, last `IdentityResult`, status, **Behavioral Risk Score**, quarantine info |
| `IdentityResult` | ANS verdict: verified, ANS lifecycle status, `source: ans|mock`, cached/stale flags |
| `BehaviorProfile` | what the agent normally does (scope/resource/peer counts), learned **only from allowed requests** |
| `RolePolicy` | baseline (standing) / grantable (JIT) / forbidden scope patterns per role |
| `Resource` | scope prefix → resource, sensitivity, requires-human scopes, honeypot flag |
| `RiskPolicy` | thresholds + signal weights (tunable in `world.yaml`) |
| `PermissionGrant` | baseline or temporary grant; `expiresAt`, `idleTimeoutSeconds`, usage, end reason |
| `SentinelEvent` | **the core contract**: immutable record of every decision / lifecycle change |
| `Incident` | groups evidence events for one agent; severity, peak risk, AI analysis |
| `BehaviorAnalysis` | validated Gemini (or rule-based fallback) output |
| `FleetOverview` / `AgentReport` / `Finding` | accountability views derived from events |

`SentinelEvent.kind`: `request | quarantine | release | grant_issued | grant_expired | grant_revoked | analysis`.
Every event carries `traceId`, optional `parentEventId`, `delegationChain`, `reasonCode`, `reason`,
`riskBefore/After`, and `signals[]`, so any action can be reconstructed and explained later.

**World file** (`simulator/fixtures/world.yaml`): tenant, resources, roles, agents, risk policy, and
the mock ANS registry. Backend validates it at startup; `POST /api/admin/reset` reloads it.

## 4. Storage

SQLite through SQLAlchemy 2.0; `DATABASE_URL` switches to Postgres. Each table has a few indexed
columns for querying plus a JSON `body` holding the full Pydantic model, so contracts stay in one
place and adding a field needs no migration (dev: `make reset`). Events are append-only by API.

*Tradeoff:* SQLite means zero setup on four laptops and no Docker, and our write volume is tiny.
Postgres is a config change if we need it.

## 5. Realtime

SSE at `GET /api/events/stream`: server→client only, auto-reconnect built into `EventSource`,
no extra dependency. Messages are `{type: event|agent|incident|grant|resync, data}`; entity messages
are full replacements (upsert by id). Clients hydrate with `GET /api/snapshot` on every (re)connect
and on `resync`. The broadcaster is in-memory, which is why we run **one uvicorn worker**.

*Tradeoff vs WebSockets:* no bidirectional need (commands go over REST); SSE is simpler and robust.

## 6. ANS integration (`services/ans/`, Person 3) — see `docs/ANS.md` for the full runbook

`ANSService.verify_agent(ansName) -> IdentityResult` is the only interface the rest of the code sees.
`ANS_MODE=real|mock` selects the adapter; the UI shows which one is active.

**Real adapter** (`reference.py`) targets the **ANS reference implementation**
(`github.com/agentnameservice/ans`), run locally — not a GoDaddy hosted API (that earlier assumption
was wrong). Three parts: `ans-ra` (:18080, Registration Authority), `ans-tl` (:18081, Transparency
Log, public read), and the `ans-verify` CLI (offline crypto verification).

`verify_agent` does real cryptographic verification, not just a status check:

| Step | Call |
|---|---|
| resolve name → agentId | world-registry map seeded at registration (dynamic resolve endpoint is a P2 swap) |
| lifecycle status | `GET {tl}/v1/agents/{agentId}` → badge `status ∈ PENDING_VALIDATION, PENDING_DNS, ACTIVE, EXPIRED, REVOKED` (public read) |
| **cryptographic proof** | `ans-verify -url {tl} -agent {agentId}` → Merkle inclusion + ES256 receipt check → `tlVerified` |

`verified = status == ACTIVE AND name matches AND receipt VERIFIED`.
Results are cached (`ANS_CACHE_TTL_SECONDS`, default 60s) and pre-warmed at startup. If the TL is
unreachable, the last **real** answer is served for up to `ANS_STALE_OK_SECONDS`, flagged `stale`;
with no cached answer, Sentinel **fails closed** (`UNREACHABLE`). Registration is a one-time setup
step done with the reference impl's own tooling (`docs/ANS.md`), never at request time.

**Mock adapter:** registry from `world.yaml → ansMockRegistry`, which mirrors what we registered in
real ANS. Results carry `source: "mock"`.

## 7. Behavioral risk (`services/behavior/`, Person 3)

Signals are pure functions of (agent, profile, request, permission result, window counts):

| Signal | Default weight | Fires when |
|---|---|---|
| `FORBIDDEN_SCOPE` | +35 | scope matches the role's forbidden patterns |
| `NEW_SENSITIVE_RESOURCE` | +20 | high/critical resource never used before **and** no grant held |
| `RATE_SPIKE` | +15 | requests in 60s > max(8, expectedRpm × 3) |
| `UNEXPECTED_PEER` | +15 | target agent not a known peer and never contacted |
| `REPEATED_DENIALS` | +10 | ≥3 denials in 5 min |
| `EXPIRED_GRANT_USE` | +5 | used a decayed grant |
| `HONEYPOT_ACCESS` | +50 | touched a deception resource (stretch) |
| `AI_ASSESSMENT` | 0..+20 | P1: bounded, validated Gemini contribution |

Each signal fires at most once per 60s per agent. Levels: 0–29 low, 30–59 elevated, 60–79 high,
80–100 critical (auto-quarantine). Risk cools toward the agent's baseline at 1 point/min while it
behaves; it is frozen while the agent is quarantined. Profiles learn only from allowed requests, so
repeating forbidden requests can't poison the baseline. All numbers are hand-tuned heuristics in
`RiskPolicy`. They are not scientifically calibrated, and we say so.

## 8. Permission decay (`services/grants/`)

- **Baseline grants**: standing, from role policy (seeded).
- **Temporary grants**: `POST /api/agents/{id}/grants {scope, ttlSeconds, idleTimeoutSeconds?}`,
  only for the role's `grantable` scopes. They decay by TTL or by idle timeout (use-it-or-lose-it).
- **Enforcement** checks liveness at request time (`grants/rules.py`), so it never depends on the
  sweeper's timing. The sweeper (1s) only makes expiry *visible*: `grant_expired` event + SSE.
- Quarantine revokes the agent's temporary grants (`QUARANTINE_CLEANUP`).
- Accountability flags standing grants unused in the window as decay candidates.

## 9. Quarantine (`services/quarantine/`)

Automatic when risk ≥ critical, or manual (operator kill switch). While quarantined every request
is denied regardless of grants; the graph shows it isolated. Release is operator-only: it resolves
the open incident and sets risk to a probation value (40). Revoking the ANS identity itself is a
separate, permanent ANS lifecycle action (P2, explicit operator confirmation).

## 10. Gemini (`services/gemini/`, Person 3)

**Two parallel detectors feed the Sentinel controller.** Hard policy is fast and objective; Gemini is
the semantic brain. It answers: *is this sequence of actions consistent with the agent's role and its
current task?* — the thing rules cannot express.

Two triggers into the same analyzer (`AnalysisRunner`):
- **incident** (`schedule`): a hard rule already opened an incident → explain + possibly escalate.
- **semantic review** (`schedule_review`): an agent AGGREGATED sensitive data (≥3 allowed high/critical
  accesses) while NO rule fired → run Gemini so a malicious *sequence* of permitted actions is caught.
  Throttled per agent.

Telemetry: role, **current task**, recent action window (with resource sensitivity), deterministic
signals, delegation targets. Gemini returns `GeminiAnalysisOutput` (anomaly type, severity, confidence,
**violations[]**, reason, recommended action) — **it never emits a 0–100 score.** Sentinel maps
severity → a bounded contribution (`weight_ai_semantic_*` in `RiskPolicy`), and a **CRITICAL finding at
≥ `ai_quarantine_min_confidence` (0.85), real `source=="gemini"` only, quarantines the agent directly**
— even when deterministic signals stayed calm. The quarantine event records Gemini's severity,
confidence, and reasoning. Timeout/quota/bad-JSON → rule-based fallback (`source:"fallback"`), which
never moves the score and never quarantines. The demo works fully with `GEMINI_MODE=mock` (advisory
only); AI-triggered quarantine needs `GEMINI_MODE=real`.

## 11. Accountability & visibility (`services/accountability/`)

Built entirely from stored events (plus grants/incidents):
- **Fleet overview**: every enrolled agent and every unknown caller, totals, top denial reason,
  and a deterministic **hypothesis**: `possibly_compromised`, `likely_misconfigured`,
  `unverified_identity`, `over_privileged`, `inactive`, or `healthy`.
- **Agent report**: denials by reason, per-scope usage (in-role or not), risk history, incidents,
  grant hygiene, and evidence-backed findings (e.g. "Keeps requesting payroll.hours.write without a
  grant: 12 denied attempts in 7 days").
- **Audit log explorer**: `GET /api/events` filtered by agent/kind/decision/reason/trace, paged by `seq`.
- **History**: the simulator's `history_backfill` replays 7 days through the real gateway
  (`observedAt`, only when `ALLOW_BACKFILL=true`), so history is genuine pipeline output.

## 12. Simulator (`simulator/`, Ishan)

`world.yaml` defines the agents; `IMPOSTORS` defines fakes. Scenarios are declarative step lists
(`Request`, `Grant`, `Wait`, `Note`, `Reset`, `Resync`) with expected outcomes, so each scenario is
also a test (`--check`). The control API (`:8001`) lets the dashboard trigger scenarios;
`python -m sentinel_sim smoke` runs the whole demo with assertions.

## 13. Key tradeoffs

| Choice | Why | Cost |
|---|---|---|
| One backend process, global state lock | simple, race-free, debuggable | no horizontal scale (irrelevant here) |
| SQLite + JSON bodies | zero setup, no migrations | weaker typing in DB; Postgres is 1 env var away |
| SSE over WebSockets | one-way is all we need; auto-reconnect | no client→server over the stream |
| Deterministic enforcement, Gemini advisory | explainable, fast, reliable | less "magic"; AI can't catch what rules forbid from overriding |
| Heuristic risk weights | transparent, tunable live | not a trained model (and we don't claim it is) |
| Simulator as a separate process over HTTP | honest integration story, independent ownership | one more process to start |
| Backfill through the gateway | history is real pipeline output | needs a demo-only `observedAt` flag |

## 14. Known limitations (be upfront with judges)

- No proof-of-possession: we verify the *claimed* ANS name is registered and ACTIVE, not that the
  caller holds its key. Production: mTLS with the ANS-issued identity certificate. Signed requests are P2.
- Agent actions are simulated; Sentinel decides and records but doesn't proxy real payloads.
- Risk scoring is heuristic; findings are rule-based summaries of observed history.
