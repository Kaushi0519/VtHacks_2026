"use client";
// Owner: Person 2. An agent's just-in-time grants in the inspector: countdown, usage, revoke.
import clsx from "clsx";
import { useState } from "react";
import { api } from "@/lib/api";
import { time } from "@/lib/format";
import { barColor, countdownLabel, endLabel, isOnStage, isTemporary, remainingFraction } from "@/lib/grants";
import { useSentinel } from "@/lib/store";
import { useNow } from "@/lib/useNow";
import type { PermissionGrant } from "@/types/sentinel";

export function GrantList({ agentId }: { agentId: string }) {
  const grants = useSentinel((s) => s.grants);
  const now = useNow();
  const shown = Object.values(grants).filter((g) => g.agentId === agentId && isTemporary(g) && isOnStage(g, now));
  if (shown.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="panel-title mb-1">Temporary access</p>
      <ul className="space-y-1.5">
        {shown.map((g) => (
          <GrantRow key={g.id} g={g} now={now} />
        ))}
      </ul>
    </div>
  );
}

function GrantRow({ g, now }: { g: PermissionGrant; now: number }) {
  const [busy, setBusy] = useState(false);
  const active = g.status === "active";
  const frac = remainingFraction(g, now);
  return (
    <li className={clsx("rounded border px-2 py-1.5", active ? "border-accent/30" : "decay-ended border-crit/40")}>
      <div className="flex items-center gap-2 font-mono text-[11px]">
        <span className={clsx("min-w-0 flex-1 truncate", active ? "text-accent" : "text-crit line-through")}>{g.scope}</span>
        {active ? (
          <span className="font-bold tabular-nums text-slate-100">{countdownLabel(g, now)}</span>
        ) : (
          <span className="font-bold text-crit">{endLabel(g)}</span>
        )}
      </div>
      <div className="mt-1 h-1 overflow-hidden rounded-full bg-line">
        <div className={clsx("h-full transition-[width] duration-300 ease-linear", barColor(frac))} style={{ width: `${frac * 100}%` }} />
      </div>
      <div className="mt-1 flex items-center gap-2 text-[10px] text-dim">
        <span className="min-w-0 flex-1 truncate" title={g.reason ?? ""}>
          {g.reason ?? "No reason given"} · used {g.useCount}×
          {g.idleTimeoutSeconds !== null && ` · ends if unused ${g.idleTimeoutSeconds}s`}
          {!active && g.endedAt && ` · ${time(g.endedAt)}`}
        </span>
        {active && (
          <button
            disabled={busy}
            onClick={() => {
              setBusy(true);
              api.revokeGrant(g.id).finally(() => setBusy(false));
            }}
            className="shrink-0 rounded border border-crit/40 px-1.5 font-mono text-crit hover:bg-crit/10 disabled:opacity-50"
          >
            REVOKE
          </button>
        )}
      </div>
    </li>
  );
}
