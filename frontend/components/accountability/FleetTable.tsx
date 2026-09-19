"use client";
// Owner: Person 2. "Which agents have problems, and what kind?" Worst first.
import clsx from "clsx";
import { levelFor, riskColor } from "@/lib/format";
import { useSentinel } from "@/lib/store";
import type { ActivityTotals, AgentActivityRow, FleetOverview } from "@/types/sentinel";
import { HYPOTHESIS } from "./hypotheses";

export const sortRows = (o: FleetOverview): AgentActivityRow[] =>
  [...o.agents, ...o.unknownActors].sort(
    (a, b) => HYPOTHESIS[a.hypothesis].rank - HYPOTHESIS[b.hypothesis].rank || b.totals.denied - a.totals.denied,
  );

export function FleetSummary({ totals, days }: { totals: ActivityTotals; days: number }) {
  const tiles: { label: string; value: number; tone?: string }[] = [
    { label: "Requests", value: totals.requests },
    { label: "Allowed", value: totals.allowed, tone: "text-ok" },
    { label: "Denied", value: totals.denied + totals.quarantineDecisions, tone: totals.denied ? "text-crit" : undefined },
    { label: "Sent to human", value: totals.requireHuman, tone: totals.requireHuman ? "text-warn" : undefined },
    { label: "Identity failures", value: totals.identityFailures, tone: totals.identityFailures ? "text-fuchsia-300" : undefined },
    { label: "Incidents", value: totals.incidents, tone: totals.incidents ? "text-high" : undefined },
    { label: "Quarantines", value: totals.quarantines, tone: totals.quarantines ? "text-crit" : undefined },
  ];
  return (
    <div className="panel flex flex-wrap items-stretch divide-x divide-line">
      <div className="flex flex-col justify-center px-4 py-3">
        <span className="panel-title">Accountability</span>
        <span className="text-sm text-slate-300">Last {days} days, every decision</span>
      </div>
      {tiles.map((t) => (
        <div key={t.label} className="flex min-w-24 flex-1 flex-col justify-center px-4 py-3">
          <span className={clsx("font-mono text-2xl leading-none font-bold tabular-nums", t.tone ?? "text-slate-100")}>{t.value}</span>
          <span className="mt-1 text-[11px] text-dim">{t.label}</span>
        </div>
      ))}
    </div>
  );
}

export function FleetTable({ rows, selected, onSelect }: { rows: AgentActivityRow[]; selected: string | null; onSelect: (id: string) => void }) {
  const policy = useSentinel((s) => s.system?.riskPolicy);
  return (
    <section className="panel flex min-h-0 flex-col">
      <div className="flex items-baseline justify-between px-3 pt-3 pb-2">
        <h2 className="panel-title">Fleet</h2>
        <span className="text-[11px] text-dim">worst first · peak risk</span>
      </div>
      <ul className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-2 pb-2">
        {rows.map((r) => {
          const h = HYPOTHESIS[r.hypothesis];
          // Peak, not live: the live score cools back toward baseline, so an agent that spiked to 78
          // and behaved since would read as a harmless 7 next to findings describing the spike.
          const peak = r.peakRisk ?? r.riskScore;
          const level = peak !== null && policy ? levelFor(peak, policy) : null;
          return (
            <li key={r.agentId}>
              <button
                onClick={() => onSelect(r.agentId)}
                className={clsx(
                  "w-full rounded-md border px-3 py-2 text-left transition-colors",
                  selected === r.agentId ? "border-accent/50 bg-raised" : "border-transparent hover:border-line hover:bg-raised/60",
                )}
              >
                <div className="flex items-center gap-2">
                  <span className={clsx("min-w-0 flex-1 truncate text-sm font-medium", r.known ? "text-slate-100" : "font-mono text-crit")}>
                    {r.known ? r.displayName : `? ${r.displayName}`}
                  </span>
                  {r.status === "quarantined" && <span className="font-mono text-[10px] font-bold text-crit">QUARANTINED</span>}
                  {level && (
                    <span className={clsx("font-mono text-sm font-bold tabular-nums", riskColor[level])} title={`Peak Behavioral Risk Score in this window (now ${r.riskScore ?? "?"})`}>
                      {peak}
                    </span>
                  )}
                </div>
                <div className="mt-1 flex items-center gap-2">
                  <span className={clsx("rounded border px-1.5 py-px font-mono text-[10px] tracking-wide", h.badge)}>
                    {h.icon} {h.label.toUpperCase()}
                  </span>
                  <span className="ml-auto font-mono text-[10px] text-dim">
                    {r.totals.requests} req ·{" "}
                    <span className={r.totals.denied ? "text-crit" : undefined}>{r.totals.denied + r.totals.quarantineDecisions} denied</span>
                  </span>
                </div>
                {r.findings[0] && <p className="mt-1 truncate text-xs text-slate-400">{r.findings[0].title}</p>}
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
