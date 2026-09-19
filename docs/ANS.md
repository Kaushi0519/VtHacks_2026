# ANS integration (real) — Owner: Person 3

**What changed:** the earlier design assumed a GoDaddy hosted REST API at `api.godaddy.com`. That was
wrong. Real ANS ("Best Use of ANS" track, judged by Scott Courtney, the ANS architect) is the **open
reference implementation**, run locally. Our adapter now targets it and does *real cryptographic
verification*, not just a status check.

- Spec + Trust Index: https://github.com/agentnameservice/ans-registry
- Reference implementation: https://github.com/agentnameservice/ans
- Go SDK (client reference): https://github.com/agentnameservice/ans-sdk-go
- Live external agents to verify against: https://webmesh.ai/

## The three moving parts

| Service | Port | Role |
|---|---|---|
| `ans-ra` | 18080 | Registration Authority — registration, identity certs, lifecycle |
| `ans-tl` | 18081 | Transparency Log — agent **badge** + **SCITT COSE_Sign1 receipts** (public read) |
| `ans-verify` | CLI | offline cryptographic verification of a receipt (Merkle inclusion + ES256) |

Agent name format (unchanged, our regex already matches): `ans://v1.0.0.my-agent.example.com`
Lifecycle: `PENDING_VALIDATION → PENDING_DNS → ACTIVE` (also EXPIRED / REVOKED / FAILED).

## Run it locally (no GoDaddy key, no public DNS, no lead time)

Prereqs: Go 1.26+, openssl, curl, jq.
```bash
git clone https://github.com/agentnameservice/ans && cd ans
make build                     # builds ans-ra, ans-tl, ans-verify, ans-dns
scripts/demo/start.sh          # starts ans-ra :18080 and ans-tl :18081
scripts/demo/run-lifecycle.sh  # full register -> verify -> revoke, prints each agentId
# Swagger UIs: http://localhost:18080/docs  and  http://localhost:18081/docs
```
Dev credentials from the repo: RA `ans-dev-key-change-me`, TL `tl-internal-key`. The verify path
(TL badge + `ans-verify`) is **public read** and needs no key.

## Registering our 5 hospital agents (setup step, one-time)

Registration is done with the reference impl's own tooling (it generates CSRs; the RA issues identity +
server certs after ACME + DNS checks), not by our backend at runtime. High level per agent:
```
POST {ra}/v2/ans/agents            {agentDisplayName, version, agentHost, endpoints[], identityCsrPEM, serverCsrPEM}
POST {ra}/v2/ans/agents/{id}/verify-acme   # PENDING_VALIDATION -> PENDING_DNS
POST {ra}/v2/ans/agents/{id}/verify-dns    # PENDING_DNS -> ACTIVE   (use bin/ans-dns for local DNS)
```
Each registration returns an `agentId`. **Put that agentId into the matching `ansMockRegistry` entry in
`simulator/fixtures/world.yaml`** (field `ansAgentId`) so our resolver can map name → id. Register one or
two **impostors** too — or leave them unregistered so they resolve to NOT_FOUND (the fake-agent demo).

## How our backend verifies (`backend/app/services/ans/reference.py`)

`verify_agent(ans_name)` (never raises; fails closed):
1. **resolve** name → `agentId` from the world registry (seeded above)
2. `GET {tl}/v1/agents/{agentId}` → badge → read lifecycle `status` (public read)
3. `ans-verify -url {tl} -agent {agentId}` → Merkle + ES256 receipt check
4. `verified = status == ACTIVE AND name matches AND receipt VERIFIED`; result carries `tlVerified`

Mock mode (`ANS_MODE=mock`, default) is unchanged and still drives the whole demo with `source:"mock"`;
the UI must show `ANS: MOCK`. Never present mock output as a live call.

## Config (`.env`)

```
ANS_MODE=real
ANS_RA_URL=http://localhost:18080
ANS_TL_URL=http://localhost:18081
ANS_RA_API_KEY=ans-dev-key-change-me   # registration/admin only; verify needs no key
ANS_VERIFY_BIN=ans-verify              # must be on PATH, or an absolute path to the binary
```

## What the authoritative ANS v2 spec confirmed (and two refinements)

Fetched the real v2 OpenAPI (`ans/spec/api-spec-v2.yaml`). It **validates our design** and pins two things:

1. **REST resolution was removed in v2.** `POST /v1/agents/resolution` (what the old `godaddy.py` used)
   is gone — resolution is now via the agent's **`_ans` DNS TXT record**. Our seeded world-registry map
   is the MVP stand-in; the reference impl ships **`ans-dns`** for real `_ans` lookups if we want true
   DNS-based discovery later.
2. **The RA management API is owner-scoped.** `GET /ans/agents/{id}` (base `.../v2`, `Authorization:
   Bearer`) **404s for agents you don't own** — so it *cannot* verify impostors or external agents. We
   correctly verify against the **public Transparency Log** instead (`GET {tl}/v1/agents/{id}` badge +
   the public `GET /v1/agents/events` lifecycle feed, no auth). This is the right call, not a shortcut.

Lifecycle status enum (authoritative): `PENDING_VALIDATION, PENDING_DNS, ACTIVE, FAILED, EXPIRED,
DEPRECATED, REVOKED`. Two hosted API surfaces also exist (a GoDaddy-hosted API — PAT from
AgentNameRegistry.org / ansinfo.ai — and the local reference impl); **SDKs are Rust/Go/Java only, no
Python**, so we hand-roll REST either way. We target the **local reference impl** (key-free, no DNS
lead time); the hosted API is a drop-in alternate once we have a PAT + the prod base URL.

## ⚠️ Validate against the running stack before trusting it in the demo

This adapter is written to the documented API but has **not** been run against a live ANS stack yet.
Confirm on the running `/docs` (Swagger) and fix `reference.py` if needed:
- the TL badge JSON key that holds lifecycle status (assumed `status`)
- the `ans-verify` success output (assumed a line containing `VERIFIED`, exit 0)
- optionally resolve via the `_ans` DNS TXT record (`ans-dns`) instead of the seeded map

## Why this wins the track (and a limitation to state honestly)

- We use ANS's *actual* mechanisms: transparency-log badge + **cryptographically verified SCITT receipt**,
  not just "is it registered." Identity is domain-anchored and provable.
- Trust Index (integrity, identity, solvency, **behavior**, safety): our Behavioral Risk Score *is* the
  behavior dimension — Sentinel consumes ANS identity and contributes behavior signal.
- **Limitation (say it):** we verify the agent's registered state + receipt; we do not yet do full mTLS
  proof-of-possession per request (ANS issues identity certs for exactly this — a strong next step).
