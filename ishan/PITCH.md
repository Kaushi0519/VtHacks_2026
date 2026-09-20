# 3-minute pitch (4 speakers)

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

### Speaker 1 — hook (0:00–0:50)
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

### Speaker 2 — what it is (0:50–1:10)
> "So we built Sentinel Mesh: a zero-trust security gateway for networks of AI agents. Every action an
> agent takes goes through it, and it decides — allow, deny, or isolate — in real time.
>
> Identity comes from GoDaddy's Agent Name Service: that tells us *who* an agent is. But here's our
> whole thesis:
>
> **Identity doesn't imply trust. ANS tells us who the agent is. Sentinel decides whether its behavior
> still deserves access.**"

### Speaker 3 — live demo (1:10–2:30) · Ishan drives the keyboard
> "This is a hospital running five AI agents. *(press 1)* Normal traffic — every request verified and
> checked.
>
> *(press 2)* Now an unknown agent claims to be a payroll service. ANS can't resolve it. Denied on
> identity alone — we never even evaluate what it wanted.
>
> *(press 3)* But here's the hard case. This is the **real** FacilitiesAgent. Its identity is perfectly
> valid. It just got prompt-injected.
>
> Watch the score. A burst of requests — 23. It reaches for salary data, outside its role — denied,
> 78. It reaches for patient records — **quarantined**. Cut off from the entire mesh, including its own
> normal job.
>
> **That agent wasn't fake. ANS verified exactly who it was. Its behavior changed, and identity alone
> couldn't see that.**"

*(Stop talking for two seconds. Let them look at the red node.)*

### Speaker 4 — payoff + close (2:30–3:00)
> "Two more things. Temporary access expires on its own — nobody has to remember to revoke it.
>
> *(Accountability tab)* And every decision is on the record. Not just logs — findings. This agent is
> misconfigured, it's been asking for payroll access for a week. This one is over-privileged, it holds
> permissions it has never used. This caller was never one of ours.
>
> We're honest about where we are: ANS and our AI analysis run in labeled mock mode unless the badge
> says live, hard policy is deterministic code — the AI explains, it never decides — and proving an
> agent *holds* the identity it claims needs mTLS, which we haven't built.
>
> **ANS tells you who the agent is. Sentinel decides whether its behavior still deserves access.**"

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
- Running long? Cut the permission-decay line, never the accountability tab.
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
