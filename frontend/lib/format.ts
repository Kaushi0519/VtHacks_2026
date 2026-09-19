import type { Decision, RiskLevel } from "@/types/sentinel";

export const time = (iso: string) => new Date(iso).toLocaleTimeString([], { hour12: false });

export const riskColor: Record<RiskLevel, string> = {
  low: "text-emerald-400",
  elevated: "text-amber-300",
  high: "text-orange-400",
  critical: "text-red-500",
};

export const decisionStyle: Record<Decision, { label: string; icon: string; className: string }> = {
  allow: { label: "ALLOW", icon: "✓", className: "text-emerald-400" },
  deny: { label: "DENY", icon: "✕", className: "text-red-400" },
  require_human: { label: "REVIEW", icon: "⚠", className: "text-amber-300" },
  quarantine: { label: "QUARANTINE", icon: "⛔", className: "text-fuchsia-400" },
};

export function secondsLeft(expiresAt: string | null, now: number): number | null {
  return expiresAt ? Math.max(0, Math.round((new Date(expiresAt).getTime() - now) / 1000)) : null;
}
