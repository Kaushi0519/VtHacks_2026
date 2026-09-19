import type { Decision, RiskLevel, RiskPolicy } from "@/types/sentinel";

export const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour12: false });

export const riskColor: Record<RiskLevel, string> = {
  low: "text-ok",
  elevated: "text-warn",
  high: "text-high",
  critical: "text-crit",
};

// Mirrors backend level_for() (services/behavior/risk.py), for scores other than the agent's current one.
export function levelFor(score: number, p: RiskPolicy): RiskLevel {
  if (score >= p.thresholdCritical) return "critical";
  if (score >= p.thresholdHigh) return "high";
  if (score >= p.thresholdElevated) return "elevated";
  return "low";
}

// Solid fill for risk meters and status dots.
export const riskFill: Record<RiskLevel, string> = {
  low: "bg-ok",
  elevated: "bg-warn",
  high: "bg-high",
  critical: "bg-crit",
};

export const decisionStyle: Record<Decision, { label: string; icon: string; className: string }> = {
  allow: { label: "ALLOW", icon: "✓", className: "text-emerald-400" },
  deny: { label: "DENY", icon: "✕", className: "text-red-400" },
  require_human: { label: "REVIEW", icon: "⚠", className: "text-amber-300" },
  quarantine: { label: "QUARANTINE", icon: "⛔", className: "text-fuchsia-400" },
};

// Short, human message for a failed operator call (e.g. 401 when OPERATOR_TOKEN is set).
export function actionError(e: unknown): string {
  const msg = String(e instanceof Error ? e.message : e);
  if (msg.includes("-> 401")) return "Not authorized (operator token required).";
  if (msg.includes("Failed to fetch")) return "Backend unreachable.";
  return msg.length > 120 ? `${msg.slice(0, 120)}…` : msg;
}
