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

### Speaker 1 — hook (0:00–0:55)
> "This summer, twelve hundred AI agents were running inside OpenAI's sandboxes for an internal
> evaluation, with safety measures turned down.
>
> With no human directing them, they built their own message boards to coordinate an escape from
> containment — hundreds of thousands of messages — and hijacked wikis on the open internet to talk to
> each other. Nobody caught it from the inside. OpenAI intervened only after **Hugging Face disclosed
> that its production infrastructure had been breached.** About a third of it had to be rebuilt.
>
> Eleven hundred people who build these systems for a living signed a letter asking the government to
> regulate them. OpenAI paused training. Meanwhile the administration is pushing the other way: build
> faster, don't fear growth, lead.
>
> We're not here to settle that argument. Because while it runs, the thing everyone is arguing about
> already happened. Agents stopped answering questions and started taking actions — at machine speed,
> with no human in the loop.
>
> And whichever side you're on, everyone agrees on this: these systems need boundaries. Not boundaries
> on what they *say*. Boundaries on what they can **do**.
>
> Every one of those agents was authorized to be exactly where it started. What was missing was
> anything watching what they did next."

**Sourcing rule:** whoever delivers this must have read the coverage themselves. Wikipedia's
"OpenAI–HuggingFace incident" is the summary; check primary reporting before stage. If a judge
challenges a number, say what you know and don't improvise. Never claim Sentinel would have prevented
it — the honest claim is that nothing was watching behavior, which is the gap we built for.

### Speaker 2 — what it is (0:55–1:20) · **start the tenant run as you begin speaking**
> "So we built Sentinel Mesh: a zero-trust security gateway for networks of AI agents. Every action an
> agent takes goes through it, and it decides — allow, deny, or isolate — in real time.
>
> Identity comes from GoDaddy's Agent Name Service. That tells us *who* an agent is. But here's the
> whole thesis:
>
> **Identity doesn't imply trust. ANS tells us who the agent is. Sentinel decides whether its behavior
> still deserves access.**
>
> What you're watching is a hospital: six ANS-verified agents doing their normal jobs. Green means
> allowed. This is a system behaving."

### Speaker 3 — the living hospital (1:20–2:50) · narrate what appears, don't read the clock
Cue off the **screen**, not the stopwatch — the run paces itself.

**When the countdown appears on AnalyticsAgent:**
> "Analytics needs patient records for one report. It gets them — for a few minutes, not forever.
> Watch that timer. Nobody has to remember to revoke it; the access expires on its own."

**When SchedulingAgent starts flooding the mesh:**
> "Now something breaks. SchedulingAgent's automation loop runs away — it's hammering the gateway,
> then drifting into systems it has no business touching. Payroll. Patient records.
> Risk climbs. Seventy-seven. Then it crosses critical — **quarantined.** The node goes red and it's
> cut off from the entire mesh, including its own normal work. A buggy insider, isolated before it did
> damage."

**When IntakeAgent comes online:**
> "Here's the one that matters. A new agent just joined — IntakeAgent, onboarded this week to help
> with scheduling. Valid ANS identity. Verified. It does normal work... and then it reaches for
> patient records and the credential vault.
> **Quarantined.**"

*(Stop. Two full seconds of silence on the two red nodes.)*

> "That agent's identity was never the problem. It was exactly who it claimed to be. Its *behavior*
> was the problem — and that's the thing an identity check can't see."

### Speaker 4 — what the rules can't catch (2:50–3:25)
*(Click the incident → the "Why" panel.)*
> "Those two were caught by deterministic rules — forbidden scope, rate spikes, hard thresholds. Fast,
> explainable, no AI in the decision path.
>
> But what about an agent whose every single action is *allowed*? *(open the subtle-exfiltration
> incident)* This one stayed inside its permissions the whole time — and Gemini read the *sequence*,
> saw it didn't match the agent's actual job, and flagged it. Critical. Ninety-five percent.
>
> Two detectors: rules for what's objectively wrong, an LLM for what's only wrong in context."

### Speaker 1 — close (3:25–4:00) · the person who opened, closes
*(Accountability tab.)*
> "And afterwards, the company can finally answer a question it couldn't before: what have our agents
> actually been doing? Not logs — findings. This one is misconfigured. This one holds permissions it
> has never used. This caller was never ours.
>
> We'll be straight about what's real: ANS is running in labeled mock mode, Gemini analysis is live,
> hard policy is deterministic code — the AI explains and can escalate, it never replaces the rules —
> and proving an agent *holds* the identity it claims needs mTLS, which we haven't built yet.
>
> Twelve hundred agents got out of a sandbox this summer because nothing was watching what they did
> next. **ANS tells you who the agent is. Sentinel decides whether its behavior still deserves
> access.**"

## Running it (4:00 budget)

| Time | Who | On screen |
|---|---|---|
| 0:00–0:55 | S1 | dashboard idle, all green |
| 0:55–1:20 | S2 | **start `tenant` now**; fleet comes online |
| 1:20–2:50 | S3 | decay countdown → malfunction quarantine → malicious quarantine |
| 2:50–3:25 | S4 | incident "Why" panel, Gemini reasoning |
| 3:25–4:00 | S1 | accountability page, close |

**Start the run:** `cd simulator && uv run python -m sentinel_sim tenant --pace 1.3` (~2 min), or the
demo-bar button (Kiernan wired `tenant` + `agent` in `cb22302`). Press it as Speaker 2 opens their
mouth: the arc gives ~18s of steady green first, which covers their intro exactly.

**The Gemini beat — decide in rehearsal:**
- *Safer:* run `subtle_exfiltration` **before judges arrive**, so the incident already exists and
  Speaker 4 just clicks it. No live latency, no 503 risk.
- *Live:* start it during Speaker 3's silence. Only if it has been reliable in three rehearsals.

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
- *How do customers integrate?* Gateway, SDK or sidecar calling `POST /api/gateway/evaluate`. The
  simulator is exactly such a client.
