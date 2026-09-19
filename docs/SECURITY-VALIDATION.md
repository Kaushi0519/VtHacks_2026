# Accountability quarantine regression

Scope: mock ANS and rule-based analysis; no live integration claims.

Previously, any quarantine created a `REPEATED_OUT_OF_ROLE` finding, even when an
operator quarantined an agent without any forbidden requests. Quarantine is an
enforcement action, not evidence of a particular behavior.

The finding now requires at least two denied requests matching the role's forbidden
scopes, using the existing threshold. Quarantine can still increase its severity
when that evidence exists. Quarantine totals, current status, incidents, and audit
events remain available independently of this behavioral hypothesis.

Regression coverage in `backend/tests/test_demo_flow.py` checks both the individual
report and fleet overview, before and after release:

| Forbidden requests | Expected repeated-out-of-role finding |
|---|---|
| 0 | Absent, even after manual quarantine |
| 1 | Absent; repeated-request threshold not reached |
| 2 | Present; possible-compromise assessment retained |

Before the fix, the zero- and one-request cases failed. The existing compromised-agent
tests also protect the attack scenario. Run from `backend`: `uv run pytest -q`.

This change does not address the other audit items (caller authentication, ANS
verification/cache handling, enrollment labels, evidence links, or Gemini recovery).
