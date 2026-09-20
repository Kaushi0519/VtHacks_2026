# Lattice

**A zero-trust security gateway + control plane for networks of AI agents.**
*Identity is verified. Behavior is continuously evaluated.*

> **Identity does not automatically imply behavioral trust.**
> ANS tells Lattice **who** an agent is. Lattice decides whether that agent's **behavior** still
> deserves access — and quarantines it when it doesn't.

## ▶ Live demo

**https://lattice.luxe** — the whole thing runs in the browser, no setup. Use the **demo bar at the
bottom of the page**:

1. Click **Seed history** (populates the accountability view).
2. Click **5 · Living hospital (full demo)** and watch (~90s):
   - 6 ANS-verified hospital agents (Facilities, Payroll, Scheduling, Analytics, Database, Intake)
     do their normal jobs — the mesh is green, risk stays low.
   - A just-in-time permission **decays** and auto-expires (countdown on the mesh).
   - **SchedulingAgent malfunctions** — a runaway loop floods the gateway and drifts out of its role.
     Its Behavioral Risk Score spikes past critical → **quarantined** (the buggy insider).
   - **IntakeAgent** joins with a valid ANS identity, then reaches for the credential vault and
     patient records it was never meant to touch → **quarantined** (the credentialed thief).
3. Click any red agent → the inspector shows **Identity (ANS) · Behavior (Lattice) · Why**,
   including Gemini's reasoning.
4. Also try **6 · Real LLM agent** (a genuine LLM agent caught live by Gemini's semantic review) and
   the **Accountability** tab for per-agent findings over time.

*(It's one shared instance — great for everyone to watch, but one person should drive the buttons.)*

## What it is

Agents call APIs, data, tools and each other autonomously. Lattice sits in between (as a gateway /
SDK / sidecar would) and decides, **per request**, whether to allow it:

- **Identity (ANS):** who is this agent, and is that identity registered and ACTIVE?
- **Authorization:** deterministic allow/deny from role policy + the agent's own live grants.
- **Behavior → Behavioral Risk Score:** signals (rate spikes, out-of-role reaches, honeypot touches,
  new sensitive access) raise a transparent risk score.
- **Two detectors:** hard policy handles objective violations instantly; **Gemini** is the *semantic*
  detector — it judges whether a *sequence* of individually-permitted actions fits the agent's role
  and current task, and a real CRITICAL finding can itself trigger quarantine.
- **Enforcement:** critical risk quarantines the agent from the whole mesh; an operator can release it.
- **Permission decay:** just-in-time grants that expire on their own (TTL / idle).
- **Accountability:** every decision is an immutable event; per-agent findings ("Agent X keeps doing Y").

## Sponsors / tracks

- **GoDaddy — Agent Name Service (identity).** ANS is Lattice's identity foundation — the whole model
  is built on top of ANS-verified identity. We implemented a **spec-compliant ANS v2 adapter**
  (`backend/app/services/ans/reference.py`) that reads the Transparency Log badge and verifies the
  ES256/SCITT receipt. **This demo runs ANS in mock mode — labeled `ANS MOCK` in the UI on purpose;**
  we did not stand up a live ANS instance. Nothing mock is ever presented as a live call.
- **Google — Gemini API (semantic behavioral analysis).** Runs live (`gemini-flash-lite-latest`); a
  real CRITICAL finding above the confidence threshold can trigger a quarantine — the rule-based
  fallback never does. `AI: gemini-flash-lite-latest` in the top bar shows it's active.

## Run it locally

```bash
brew install uv            # Python tooling (installs Python 3.12 for you)
make setup                 # backend + simulator + frontend deps, copies .env files
make backend               # terminal 1 → http://localhost:8000/docs
make sim                   # terminal 2 → simulator control API :8001
make frontend              # terminal 3 → http://localhost:3000
make test && make smoke    # checks
```
Then open http://localhost:3000 and use the demo bar. Gemini runs live when `GEMINI_API_KEY` is set in
`.env` (`GEMINI_MODE=real`); everything works without a key in mock mode.

## Architecture

```
simulator (:8001) ──HTTP──▶ backend (:8000, FastAPI) ──SSE──▶ frontend (:3000, Next.js)
 hospital agents            identity(ANS) → quarantine → policy(role+grants)                mission control
                            → behavior signals → enforce → immutable event → broadcast      + accountability
                            → async Gemini semantic review (never blocks)
```
Deployed: frontend on **Vercel** (`lattice.luxe`), backend + simulator on **Railway**
(see [docs/DEPLOY.md](docs/DEPLOY.md)).

Docs: [CLAUDE.md](CLAUDE.md) (start here) · [Architecture](docs/ARCHITECTURE.md) ·
[API](docs/API.md) · [Demo script](docs/DEMO.md) · [Deploy](docs/DEPLOY.md)

Built with [React Flow](https://reactflow.dev) (MIT) for the agent mesh. VTHacks 2026.
