"use client";
// Owner: Person 2. Big countdown for just-in-time grants, pinned under the agent list.
// Readable from across the room: the grant shrinks to zero and visibly disappears.
import clsx from "clsx";
import { barColor, countdownLabel, endLabel, isOnStage, isTemporary, remainingFraction } from "@/lib/grants";
import { useSentinel } from "@/lib/store";
import { useNow } from "@/lib/useNow";

export function DecayHud() {
  const { grants, agents } = useSentinel();
  const now = useNow();
  const shown = Object.values(grants)
    .filter((g) => isTemporary(g) && isOnStage(g, now))
    .sort((a, b) => a.grantedAt.localeCompare(b.grantedAt));
  if (shown.length === 0) return null;

  return (
    <div className="space-y-2 border-t border-line px-2 pt-2 pb-2">
      {shown.map((g) => {
        const active = g.status === "active";
        const frac = remainingFraction(g, now);
        return (
          <div
            key={g.id}
            className={clsx(
              "rounded-lg border bg-void/60 px-3 py-2",
              active ? "border-accent/50" : "decay-ended border-crit/60",
            )}
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="panel-title !text-[10px]">{active ? "⏱ Temporary access" : "Access removed"}</span>
              {active ? (
                <span className={clsx("font-mono text-2xl leading-none font-bold tabular-nums", frac > 0.2 ? "text-slate-100" : "text-crit")}>
                  {countdownLabel(g, now)}
                </span>
              ) : (
                <span className="font-mono text-sm font-bold text-crit">{endLabel(g)}</span>
              )}
            </div>
            <p className="mt-1 truncate text-sm text-slate-200">
              {agents[g.agentId]?.displayName ?? g.agentId} <span className="text-dim">→</span>{" "}
              <span className={clsx("font-mono", active ? "text-accent" : "text-crit line-through")}>{g.scope}</span>
            </p>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-line">
              <div className={clsx("h-full rounded-full transition-[width] duration-300 ease-linear", barColor(frac))} style={{ width: `${frac * 100}%` }} />
            </div>
            {!active && <p className="mt-1 text-[10px] text-dim">Nobody had to remember to revoke it.</p>}
          </div>
        );
      })}
    </div>
  );
}
