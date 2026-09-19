# Analysis and identity audit fixes

## Changes

- Semantic and incident analysis capture a generation token. Reset invalidates all
  prior results; operator release invalidates prior results for that agent. The
  token is checked while holding the state lock before persistence or enforcement.
- Unknown callers can receive incident analysis without an enrolled Agent row.
- Semantic quarantine uses AI_SEMANTIC_QUARANTINE and records risk before/after;
  release events are included in incident detail as well as the global audit log.
- ANS requires an explicit matching badge name and object-shaped badge JSON.
  Stale cached results are diagnostic only (verified=false, UNREACHABLE).
  Fresh cache entries still have the configured TTL: revocation is not instantaneous.
- Verifier success requires exit zero and the exact upstream documented line:
  `? VERIFIED (kid <8 hex digits> matched key directly)`.
  Unknown formats fail closed. Timeout/cancellation kills and reaps the subprocess.
  Source: https://github.com/agentnameservice/ans/blob/main/README.md
- World configuration rejects unknown fields, invalid risk bounds/order, duplicate
  identities/resources/prefixes, unknown roles/peers, and baseline/forbidden conflicts
  detectable by matching either scope pattern against the other. This is not a
  general proof of disjointness for arbitrary glob-pattern intersections.
- The Gemini prompt explicitly treats telemetry as untrusted evidence.

## Validation

Regression tests use fake Gemini/ANS responses and temporary databases, never keys
or live registration changes. Coverage includes reset/release during delayed analysis,
new reviews after invalidation, unknown caller completion, semantic audit attribution,
release evidence, invalid ANS badges, stale cache, exact CLI output, subprocess timeout,
and malformed world configuration.

Results: 58 backend tests passed (two existing dependency deprecation warnings);
full mock simulator smoke test passed; frontend `npx tsc --noEmit` passed.

## Remaining work / integration limits

- Revalidate real ANS against the presenter's badge format and verifier binary. This
  is not evidence of successful live ANS/Gemini operation.
- Caller proof-of-possession (request signing/mTLS) remains an MVP limitation;
  registry verification does not authenticate the sender of a request.
- The existing accountability PR on security/gemini-live remains separate and should
  be reviewed/merged. Enrollment classification and finding evidence links remain open.
- Startup recovery of pending analysis and broader incident concurrency handling
  remain follow-ups; these changes address reset/release invalidation.
- Model and wire enum changes require Person 1 review before merging.
