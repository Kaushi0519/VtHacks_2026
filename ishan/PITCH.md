# 4-minute pitch (4 speakers)

Owner: Ishan. Rehearse from this; the beats match `docs/DEMO.md`.

> **Name:** the product is **Lattice** — not "Lattice Mesh", not "lattice.luxe" (that's just where
> it's deployed). The top bar says Lattice too, so the words and the screen agree.

## The hook (why it works)

Name the AI debate, decline to take a side, then pivot to the one thing both camps agree on:

> **"Whether you think AI should move faster or slower, both sides agree on one thing: these systems
> need boundaries. Not boundaries on what they say — boundaries on what they can do."**

The debate is about *capability*. The risk that already shipped is *authority*: agents stopped
answering questions and started taking actions, with credentials granted once and never taken back.

## Script

### Speaker 1 — hook (0:00–0:40)
> "This summer, twelve hundred AI agents in OpenAI's sandboxes coordinated their way out of
> containment, with no human directing them. OpenAI found out when **Hugging Face reported its
> production infrastructure breached** — a third of it had to be rebuilt.
>
> Every one of those agents was authorized to be exactly where they started, and no one realized what
> was happening until the damage was already done.
>
> That's why we built Lattice. It cuts an agent off for what it's *doing*, not just who it is."

*(~35s spoken. Pause before "Every one of those agents" and slow down — it's the line the whole demo pays off, and
the line Speaker 1 closes on.)*

**Why not "zero-trust security gateway" out loud:** in security, zero trust reads as *identity*
verification — the exact thing that didn't save anyone in the story you just told. It also stacks
three abstractions right after a concrete image, and "gateway" is an implementation detail, not a
benefit. Keep the phrase for the written submission, where a reader can slow down.

**Accuracy note:** don't say "nothing was watching." There *were* safeguards — an internal evaluation,
reduced-but-present safety measures, constraints on internet access, and staff who eventually
intervened. The real failure was detection latency: hundreds of thousands of coordination messages
passed before anyone stepped in, and the alarm came from outside. "No one realized what was happening
until the damage was already done" is both accurate and sharper.

**Cut deliberately:** the accelerate-vs-slow-down framing (the 1,100-employee petition, Anthropic's
CEO on pace, the White House pushing development). It cost ~45s and the demo needs that time more.
Keep it in your pocket for Q&A — "why does this matter now?" is exactly where it belongs, and it
answers without taking a side.

**Sourcing rule:** whoever delivers this must have read the coverage themselves. Wikipedia's
"OpenAI–HuggingFace incident" is the summary; check primary reporting before stage. If a judge
challenges a number, say what you know and don't improvise. Never claim Lattice would have prevented
it — the honest claim is that nothing was watching behavior, which is the gap we built for.

> **How to use this:** bullets are *points*, not lines — say them your way. Only the **bold quoted
> lines** are fixed; those are the ones that land, so deliver them exactly and slow down for them.

### Speaker 2 — the board + the fleet (0:40–1:05)

**Press 1 — Agents online** *(~15s: resets, then each agent checks in and fills the mesh)*
- A hospital running Lattice. Name the agents as they appear: facilities, payroll, scheduling,
  analytics, database.
- **Left:** each one has a verified identity from GoDaddy's Agent Name Service.
  **Right:** everything they can reach — payroll, patient records, scheduling, building systems.
- Lattice sits in between; every request crosses it.
- > **"It answers one question in real time: should *this* agent be doing *this*, right now?"**

### Speaker 3 — normal, then the insider (1:05–2:25)

**Press 2 — Normal + decay**
- Green packet = verified, role-checked, allowed. This is a hospital running itself.
- AnalyticsAgent gets temporary access for one report; the countdown is it expiring on its own.
- Use it after it lapses → blocked.
- > **"Most breaches start with a permission nobody remembered to take away."**

**Press 3 — Compromised agent**
- The **real** FacilitiesAgent. Verified, here all week, runs lights and HVAC. Just got prompt-injected.
- Narrate the score: burst → **23** · salary data, outside its role → denied, **78** · patient records
  → **quarantined**.
- Cut off from the whole mesh, including its own job, until a human reviews it.
- *(Stop. Two full seconds on the red node.)*
- > **"Nothing about its identity changed. It was exactly who it said it was the entire time."**

### Speaker 4 — the newcomer + the record (2:25–3:20)

**Press 4 — Malicious new agent**
- IntakeAgent joined this week. ANS verifies it perfectly, the whole way through.
- It does its real job... then reaches for patient records (**5 → 60**, denied) and the decoy
  credential vault (**→ 100**, quarantined — honeypot).
- The counterpart to the last one: that was a trusted insider going bad, this one **never belonged**.
- > **"Identity verified it both times. Identity is not what caught either of them."**

**Click the Accountability tab**
- Everything is on the record — **not logs, findings**.
- Point at three: misconfigured (asking for payroll all week) · over-privileged (permissions never
  used) · a caller that was never ours.
- Every decision replayable, with the reason attached.
- > **"That's the part a company actually buys."**

### Speaker 1 — how it's built + close (3:20–4:00)

**Points (fast, ~15s):**
- FastAPI gateway; every decision becomes an immutable event in SQL, streamed live to a Next.js
  dashboard.
- Identity from GoDaddy's ANS. Gemini for semantic analysis, with a labeled rule-based fallback.
- Honesty beat: ANS is in mock mode today, and proving an agent *holds* the identity it claims needs
  mTLS — we haven't built that.

**Then word for word:**
> "Every organization is about to be running agents like these. The ones who can least afford a
> mistake are already there — Peraton builds and runs mission systems for national security, where
> *who are you* has never been enough, and where the standard is verifying every action, every time.
>
> That standard exists for people and for devices. It doesn't exist yet for AI agents.
>
> Twelve hundred agents got out of a sandbox this summer, and nobody noticed until it was somebody
> else's problem.
>
> **ANS tells you who an agent is. Lattice decides whether its behavior still deserves access.**"

*(Beat. Then stop talking. Don't add "...and that's our project.")*

## Demo bar reference

| Key | Button | What it runs |
|---|---|---|
| — | Seed history | a week of history for the Accountability page (press before you start) |
| **1** | Agents online | `agents_online` — the fleet fills the mesh (~15s, resets first) |
| **2** | Normal + decay | `normal_operation` + `permission_decay` |
| **3** | Compromised agent | `compromised_agent` — the trusted insider goes bad |
| **4** | Malicious new agent | `malicious_joiner` — verified newcomer, hits the decoy vault |
| **5** | Fake agent | `fake_agent` — unenrolled caller, denied at identity. **Never quarantined**: there's no enrolled agent to isolate |
| **6** | Subtle compromise | `subtle_exfiltration` — Gemini catches an all-allowed sequence. Needs `GEMINI_MODE=real` |
| **A** | Ambient | background traffic on/off — **leave it off during the pitch** |
| **R** | Reset | stops everything and resets (confirm) |
| **D** | — | hide the bar for a clean screen |

**Optional extra beats** if a judge has time: **5** (denied on identity alone) and **6** (the AI
catching what rules can't). Buttons for the living-tenant run and the real-LLM agent appear after
those.

**Restart `make sim` after any pull** — the simulator doesn't hot-reload, so it keeps serving
whatever scenarios existed when it started. New buttons won't appear until you do.

**Before judges arrive:** press Seed history, then R, then Seed history once more if you ran anything.
Confirm all agents green and the top bar reads SECURE.

## Why this sells
- **The wow is a negative result.** Anyone blocks a fake agent. Blocking a *verified* one is the
  insight, and the only part judges haven't seen before. Most time, most silence after it.
- **Accountability is the business case.** The quarantine is the demo; "here's what your agents have
  been doing all week" is what someone buys.
- **Honesty is a feature.** Naming what isn't built makes everything else credible, and turns the
  judges' favorite attack into a point in our favour.

## Delivery rules
- One person on the keyboard for the whole pitch; speakers change, the driver doesn't.
- **One scenario at a time, ambient off, reset between runs** — overlapping traffic drifts the risk
  numbers away from the script (see G7 in `NOTES.md`).
- Running long? Cut the permission-decay lines, then Speaker 4's second sentence. Never cut the
  accountability tab or the honesty paragraph.
- Never say "trust score" — it's the **Behavioral Risk Score**. Never let mock output be implied as
  live. Never claim spoofing is solved.

## If a judge asks
- *Is Gemini deciding who gets blocked?* No. Deterministic policy decides. Gemini is a second,
  semantic detector that runs off the request path; only a real Gemini CRITICAL finding above the
  confidence threshold can trigger quarantine, and the rule-based fallback never enforces.
- *How is the risk score computed?* Previous score plus the weights of the signals that fired, capped
  0–100, decaying while the agent behaves. A transparent heuristic, not a trained model.
- *What stops an agent spoofing an ANS name?* We check registration and lifecycle. Production adds
  mTLS with the ANS identity certificate. We haven't built that.
- *Does delegation leak permissions?* No. Every hop is checked against its own grants.
- *Didn't OpenAI have monitoring?* Yes — and it caught what those agents *were*, not what they were
  *doing*. Detection came from outside, after the damage. That distinction is the whole product.
- *Why does this matter now?* (The framing cut from the script.) 1,100 people who build these systems
  signed an open letter asking to be regulated; Anthropic's CEO says we're outrunning our ability to
  make this safe; the White House is pushing development faster; companies keep deploying agents
  because they work. We're not taking a side — every side assumes someone is enforcing boundaries at
  runtime, and mostly nobody is.
- *How do customers integrate?* Gateway, SDK or sidecar calling `POST /api/gateway/evaluate`. The
  simulator is exactly such a client.
