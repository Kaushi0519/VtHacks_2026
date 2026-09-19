# API contract

Source of truth: `backend/app/models/*.py`. Mirror: `frontend/types/sentinel.ts`. Change all three
together (see CLAUDE.md). Live, clickable schema: `http://localhost:8000/docs`.

Conventions: JSON is **camelCase**; timestamps are UTC ISO-8601; ids are prefixed (`evt_`, `trc_`,
`inc_`, `grt_`); agent ids are slugs (`facilities-agent`). Errors: FastAPI `{"detail": "..."}` with
400/403/404/422.

## Gateway (what agents / SDKs / sidecars call)

### `POST /api/gateway/evaluate`
```json
{ "actorAnsName": "ans://v1.0.0.facilities.demo-hospital.example",
  "actorAgentId": "facilities-agent",        // optional hint, must match the ANS identity
  "action": "payroll.salary.read",            // scope: <resource>.<thing>.<verb>
  "targetAgentId": null,                      // set for agent-to-agent calls
  "traceId": null, "parentEventId": null,     // propagate to link delegated calls
  "delegationChain": [],                      // upstream agents, originator first
  "observedAt": null,                         // history backfill only (ALLOW_BACKFILL=true)
  "source": "scenario:compromised_agent" }    // label only, never used for policy
```
→ `GatewayDecision`
```json
{ "eventId": "evt_…", "traceId": "trc_…", "decision": "deny", "reasonCode": "FORBIDDEN_FOR_ROLE",
  "reason": "payroll.salary.read is forbidden for the facilities role",
  "identity": { "ansName": "…", "verified": true, "ansStatus": "ACTIVE", "source": "mock", … },
  "riskBefore": 23, "riskAfter": 78, "riskLevel": "high",
  "signals": [{ "code": "FORBIDDEN_SCOPE", "weight": 35, "detail": "…" }],
  "incidentId": "inc_…", "agentStatus": "active", "result": null }
```
`decision`: `allow | deny | require_human | quarantine`.
`reasonCode`: `ALLOWED, IDENTITY_UNVERIFIED, IDENTITY_UNAVAILABLE, AGENT_NOT_ENROLLED, AGENT_QUARANTINED,
UNKNOWN_RESOURCE, FORBIDDEN_FOR_ROLE, NO_GRANT, GRANT_EXPIRED, GRANT_REVOKED, REQUIRES_HUMAN, RISK_THRESHOLD, AI_SEMANTIC_QUARANTINE`

`AI_SEMANTIC_QUARANTINE` identifies asynchronous Gemini-triggered quarantine, which can
occur below the numeric risk threshold. Its quarantine and analysis events preserve the
score before and after the contribution. Results started before reset or operator release
are discarded. Unknown callers still receive incident explanations without agent enforcement.
Incident detail includes its release event.
(lifecycle events also use `OPERATOR_ACTION, TTL_ELAPSED, IDLE_TIMEOUT, QUARANTINE_CLEANUP, ANALYSIS_COMPLETE`).

## Dashboard / control plane

| Method & path | Returns | Notes |
|---|---|---|
| `GET /api/health` | `{status, ansMode, analyzerMode}` | |
| `GET /api/system` | `SystemInfo` | tenant, adapter modes, risk policy |
| `GET /api/snapshot` | `Snapshot` | hydrate the dashboard: agents, resources, graph, grants, incidents, 100 latest events, lastSeq |
| `GET /api/graph` | `{nodes, edges}` | baseline topology from world.yaml |
| `GET /api/agents` | `Agent[]` | |
| `GET /api/agents/{id}` | `AgentDetail` | agent, profile, grants, recent events, open incident |
| `POST /api/agents/{id}/quarantine` | `Agent` | body `{reason}`: operator kill switch |
| `POST /api/agents/{id}/release` | `Agent` | body `{note}`: resolves incident, risk → probation |
| `GET /api/agents/{id}/grants` | `PermissionGrant[]` | |
| `POST /api/agents/{id}/grants` | `PermissionGrant` (201) | body `{scope, ttlSeconds, idleTimeoutSeconds?, reason, grantedBy?}`; 403 if not grantable |
| `GET /api/grants?status=&agentId=` | `PermissionGrant[]` | |
| `POST /api/grants/{id}/revoke` | `PermissionGrant` | body `{reason}` |
| `GET /api/events?agentId=&kind=&decision=&reasonCode=&traceId=&incidentId=&since=&until=&beforeSeq=&limit=` | `EventPage {items, nextBeforeSeq}` | newest first |
| `GET /api/events/stream` | SSE | see below |
| `GET /api/incidents?status=&agentId=` | `Incident[]` | |
| `GET /api/incidents/{id}` | `IncidentDetail {incident, events}` | evidence, oldest first |
| `GET /api/accountability/overview?days=7` | `FleetOverview` | agents + unknown actors ranked by hypothesis |
| `GET /api/accountability/agents/{id}?days=7` | `AgentReport` | works for unknown actor ids too |

Accountability rows carry two risk numbers, on purpose: `riskScore` is the **live, cooled** score
(what the dashboard card shows — it drifts back to baseline between requests), while `peakRisk` is
the **worst score reached in the window** (max `riskAfter` over the window's request events; `null`
if the actor made no requests). The retrospective views should render `peakRisk` so a transient
spike (e.g. a denied attempt) stays visible; `riskScore` is only the current instant.
| `POST /api/admin/reset` | `{status}` | wipe + reload world.yaml + reseed; broadcasts `resync` |
| `POST /api/admin/resync` | `{status}` | tell dashboards to refetch (after backfill) |

## Realtime: `GET /api/events/stream` (Server-Sent Events)

Each message is `data: {"type": T, "data": {...}}`, with a `: ping` comment every 15s.

| type | data | client action |
|---|---|---|
| `event` | `SentinelEvent` | prepend to feed (dedupe by id), animate edge |
| `agent` | `Agent` | replace by id |
| `incident` | `Incident` | replace by id |
| `grant` | `PermissionGrant` | replace by id |
| `resync` | `{}` | refetch `/api/snapshot` |

On every (re)connect: fetch `/api/snapshot`. Within one operation, messages arrive in the order
event → agent → grant → incident. Backfilled history is not streamed (events have `metadata.backfill`).

## SentinelEvent (abridged; full shape in `models/event.py`)
```ts
{ id, seq, traceId, parentEventId, timestamp,
  kind: "request"|"quarantine"|"release"|"grant_issued"|"grant_expired"|"grant_revoked"|"analysis",
  actorAgentId, actorAnsName, targetAgentId, targetResource, action, delegationChain,
  identity: IdentityResult|null, decision, reasonCode, reason,
  riskBefore, riskAfter, signals: RiskSignal[], incidentId, grantId,
  initiatedBy: "gateway"|"sentinel"|"operator"|"analyzer", metadata }
```
`metadata` is an open bag of stable, documented keys (not free-form):
- `metadata.backfill: true` — seeded history, not streamed live.
- `metadata.analysis: BehaviorAnalysis` — present on **every** `analysis` event (and only those),
  including semantic reviews that open no incident (`incidentId: null`). This is the canonical place
  to read the finding off a raw event; the UI depends on it. `metadata.analysisStatus: "done"`
  accompanies it on the incident record.

## Behavioral analysis (Gemini structured output → `BehaviorAnalysis`)
```json
{ "anomalyType": "role_resource_mismatch", "severity": "high", "confidence": 0.94,
  "violations": ["task_deviation", "suspicious_data_aggregation"],
  "reason": "Facilities agent requested payroll salary data outside its observed role.",
  "recommendedAction": "quarantine", "source": "gemini", "model": "gemini-flash-lite-latest",
  "analyzedAt": "…", "error": null }
```
`source: "fallback"` means rule-based (Gemini off or failed). The UI must label it. `violations` are
short semantic tags Gemini named; render them as-is (empty on the rule-based fallback).

An **AI-triggered quarantine** (Gemini decided, not a hard rule) is identifiable without guessing:
the quarantine event's `reason` starts with `"Gemini semantic analysis flagged …"` and its
accompanying `analysis` has `source: "gemini"`, `severity: "critical"`, `recommendedAction:
"quarantine"`. Anything short of that (e.g. a rule-triggered quarantine that merely carries an
advisory Gemini finding) must not be presented as AI-decided.

## Simulator control API (`:8001`, separate process)

| Method & path | Notes |
|---|---|
| `GET /scenarios` | `[{id, title, description, loop, steps}]` |
| `POST /scenarios/{id}/run?check=false&ttl_seconds=` | starts in background → `RunState` |
| `GET /runs`, `GET /runs/{id}` | `RunState {status, stepIndex, totalSteps, caption, results[]}` |
| `POST /runs/{id}/stop`, `POST /runs/stop-all` | |

World-file validation rejects unknown settings, invalid risk ranges/threshold order, duplicate IDs/prefixes, and invalid role/peer references. These checks do not change the wire fields. ANS stale cached results carry `verified=false`, `stale=true`, and `ansStatus=UNREACHABLE`; they cannot authorize access.
