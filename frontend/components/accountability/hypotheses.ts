// Owner: Person 2. How each accountability hypothesis looks and what it means in plain English.
// The hypothesis itself comes from backend rules (services/accountability/findings.py).
import type { Hypothesis } from "@/types/sentinel";

export const HYPOTHESIS: Record<Hypothesis, { label: string; icon: string; badge: string; meaning: string; rank: number }> = {
  possibly_compromised: {
    label: "Possibly compromised",
    icon: "⛔",
    badge: "border-crit/60 bg-crit/15 text-crit",
    meaning: "Its identity checks out, but its behavior doesn't. Treat as an active threat.",
    rank: 0,
  },
  unverified_identity: {
    label: "Unverified identity",
    icon: "?",
    badge: "border-fuchsia-400/60 bg-fuchsia-400/10 text-fuchsia-300",
    meaning: "Called the gateway without a verified, enrolled identity. Blocked before any policy ran.",
    rank: 1,
  },
  likely_misconfigured: {
    label: "Likely misconfigured",
    icon: "⚙",
    badge: "border-warn/60 bg-warn/10 text-warn",
    meaning: "A legitimate agent keeps asking for access it was never given. Probably a workflow bug, not an attack.",
    rank: 2,
  },
  over_privileged: {
    label: "Over-privileged",
    icon: "↓",
    badge: "border-accent/50 bg-accent/10 text-accent",
    meaning: "Holds standing permissions it never uses. A least-privilege cleanup candidate.",
    rank: 3,
  },
  inactive: {
    label: "Inactive",
    icon: "…",
    badge: "border-line bg-raised text-dim",
    meaning: "No activity in this window.",
    rank: 4,
  },
  healthy: {
    label: "Healthy",
    icon: "✓",
    badge: "border-ok/40 bg-ok/10 text-ok",
    meaning: "Behavior consistent with its role.",
    rank: 5,
  },
};

export const SEVERITY_TEXT: Record<string, string> = {
  critical: "text-crit",
  high: "text-high",
  medium: "text-warn",
  low: "text-dim",
};
