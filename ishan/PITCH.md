# 4-minute pitch (4 speakers)

Owner: Ishan. Rehearse from this; the beats match `docs/DEMO.md`.

> **Name check before judging:** the UI top bar says **SENTINEL MESH**. If we pitch "Lattice", the
> screen contradicts the words within ten seconds. Either change the wordmark first or say what's on
> screen. This script says Sentinel.

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
challenges a number, say what you know and don't improvise. Never claim Sentinel would have prevented
it — the honest claim is that nothing was watching behavior, which is the gap we built for.

### Speaker 2 — the board (0:40–1:05)
*(Nothing pressed yet.)*
> "You're looking at a hospital. On the left, its six AI agents — each with a verified identity from
> GoDaddy's Agent Name Service. On the right, everything they can reach: payroll, patient records,
> scheduling, the building systems.
>
> Lattice sits in between. Every request crosses it, and it answers one question in real time: should
> *this* agent be doing *this*, right now?"

### Speaker 3 — the demo (1:05–2:25) · driver presses, speaker narrates

**Press 1 — "Normal + decay"**
> "A normal Tuesday. Every green packet is a request that was verified, checked against the agent's
> role, and allowed.
>
> Now watch AnalyticsAgent. It needs patient records for one report, so it's granted access — for
> minutes, not forever. That countdown is the access expiring on its own. Most breaches start with a
> permission nobody remembered to take away."

**Press 2 — "Fake agent"**
> "Now something unknown claims to be a payroll sync service. ANS can't resolve it — denied on
> identity alone. We never even evaluated what it wanted. And it stays on the board as an unverified
> caller, because *who tried* is worth knowing."

**Press 3 — "Compromised agent"**
> "Here's the hard case: the **real** FacilitiesAgent. Verified, here all week, runs the lights and the
> HVAC. It's just been prompt-injected.
>
> Watch the score. A burst — 23. Salary data, outside its role — denied, 78. Patient records —
> **quarantined.** Cut off from the whole mesh, including its own job."

*(Stop. Two seconds of silence on the red node.)*

> "Nothing about its identity changed. It was exactly who it said it was the entire time."

### Speaker 4 — the AI detector + the record (2:25–3:20)

**Press 4 — "Subtle compromise (Gemini catches it)"**
> "Rules catch the obvious. But what about an agent whose every action is *allowed*?
>
> This one stays inside its permissions the whole way. Gemini reads the *sequence* against what the
> agent was actually assigned to do, and flags it — critical, ninety-five percent. Two detectors: rules
> for what's objectively wrong, an LLM for what's only wrong in context. The fallback can never
> quarantine anything; only real Gemini can."

**Click the Accountability tab**
> "And all of it is on the record. Not logs — findings. This agent is misconfigured, it's been asking
> for payroll access all week. This one is over-privileged, it holds permissions it has never used.
> This caller was never ours. Every decision, replayable, with the reason attached. That's the part a
> company actually buys."

### Speaker 1 — how it's built + close (3:20–4:00)
> "Under the hood: a FastAPI gateway where every decision becomes an immutable event, streamed live to
> a Next.js dashboard. Identity from GoDaddy's ANS. Gemini for the semantic analysis, with a labeled
> rule-based fallback — we always tell you which one you're looking at.
>
> And straight with you: ANS is in mock mode today, and proving an agent *holds* the identity it claims
> needs mTLS, which we haven't built.
>
> Twelve hundred agents got out of a sandbox this summer, and nobody noticed until it was somebody
> else's problem. **ANS tells you who an agent is. Lattice decides whether its behavior still deserves
> access.**"

## Demo bar reference

| Key | Button | What it runs |
|---|---|---|
| — | Seed history | a week of history, for the Accountability page (press before you start) |
| **1** | Normal + decay | `normal_operation` + `permission_decay` |
| **2** | Fake agent | `fake_agent` |
| **3** | Compromised agent | `compromised_agent` |
| **4** | Subtle compromise (Gemini catches it) | `subtle_exfiltration` — needs `GEMINI_MODE=real` |
| **5** | Living tenant | the whole story as one continuous ~90s run |
| **6** | Real LLM agent (Gemini catches it) | a genuine model-driven agent, hijacked mid-run |
| **A** | Ambient | background traffic on/off — **leave it off during the pitch** |
| **R** | Reset | stops everything and resets (confirm) |
| **D** | — | hide the bar for a clean screen |

**Buttons 5 and 6 only appear after `make sim` is restarted** — the simulator doesn't hot-reload, so
it keeps serving whatever scenarios existed when it started.

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
