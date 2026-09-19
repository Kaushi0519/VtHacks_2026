// Just-in-time grant helpers for the decay UI. The backend sweeper is the authority on expiry;
// these only drive countdowns between its SSE updates.
import type { PermissionGrant, Resource } from "@/types/sentinel";

// How long an ended grant stays on screen so the audience sees it disappear.
export const ENDED_VISIBLE_MS = 6000;

const ms = (iso: string | null) => (iso ? new Date(iso).getTime() : null);

export const isTemporary = (g: PermissionGrant) => g.kind === "temporary";

// Active, or ended within the last few seconds (still animating out).
export function isOnStage(g: PermissionGrant, now: number): boolean {
  if (g.status === "active") return true;
  const ended = ms(g.endedAt);
  return ended !== null && now - ended < ENDED_VISIBLE_MS;
}

// Fraction of the TTL still left, 0..1 (1 when there's no TTL).
export function remainingFraction(g: PermissionGrant, now: number): number {
  const start = ms(g.grantedAt);
  const end = ms(g.expiresAt);
  if (g.status !== "active") return 0;
  if (start === null || end === null || end <= start) return 1;
  return Math.max(0, Math.min(1, (end - now) / (end - start)));
}

export function resourceForScope(scope: string, resources: Resource[]): Resource | undefined {
  return resources.find((r) => scope === r.scopePrefix || scope.startsWith(`${r.scopePrefix}.`));
}

export function endLabel(g: PermissionGrant): string {
  if (g.status === "revoked") return "REVOKED";
  if (g.endReason === "IDLE_TIMEOUT") return "EXPIRED · UNUSED";
  if (g.endReason === "QUARANTINE_CLEANUP") return "REMOVED · QUARANTINE";
  return "EXPIRED";
}

// Countdown bar color: plenty left → cyan, running out → amber, last stretch → red.
export const barColor = (fraction: number) => (fraction > 0.5 ? "bg-accent" : fraction > 0.2 ? "bg-warn" : "bg-crit");

// Countdown text. At 0 the grant is still ACTIVE until the backend sweeper (1s) marks it expired.
export function countdownLabel(g: PermissionGrant, now: number): string {
  const end = ms(g.expiresAt);
  if (end === null) return "no TTL";
  const left = Math.max(0, Math.ceil((end - now) / 1000));
  return left > 0 ? `${left}s` : "EXPIRING…";
}
