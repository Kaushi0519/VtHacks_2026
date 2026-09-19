"use client";
// Owner: Person 2. "Which agents have problems, and what kind?"
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useSentinel } from "@/lib/store";
import type { AgentActivityRow, FleetOverview, Hypothesis } from "@/types/sentinel";

export const HYPOTHESIS_STYLE: Record<Hypothesis, string> = {
  possibly_compromised: "bg-red-900 text-red-200",
  unverified_identity: "bg-fuchsia-900 text-fuchsia-200",
  likely_misconfigured: "bg-amber-900 text-amber-200",
  over_privileged: "bg-sky-900 text-sky-200",
  inactive: "bg-slate-800 text-slate-300",
  healthy: "bg-emerald-900 text-emerald-200",
};

export function FleetTable({ selected, onSelect }: { selected: string | null; onSelect: (id: string) => void }) {
  const [data, setData] = useState<FleetOverview | null>(null);
  const eventCount = useSentinel((s) => s.events.length); // refresh as live traffic arrives

  useEffect(() => {
    api.overview(7).then(setData).catch(console.error);
  }, [eventCount]);

  if (!data) return <p className="text-slate-500">Loading history…</p>;
  const rows: AgentActivityRow[] = [...data.agents, ...data.unknownActors];
  return (
    <section>
      <h2 className="mb-2 font-mono text-xs tracking-widest text-slate-500">
        LAST 7 DAYS · {data.totals.requests} REQUESTS · {data.totals.denied} DENIED · {data.totals.incidents} INCIDENTS
      </h2>
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-slate-500">
          <tr><th>Agent</th><th>Assessment</th><th>Req</th><th>Denied</th><th>Incidents</th><th>Top issue</th></tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.agentId}
              onClick={() => onSelect(r.agentId)}
              className={`cursor-pointer border-t border-slate-800 hover:bg-slate-900 ${selected === r.agentId ? "bg-slate-900" : ""}`}
            >
              <td className="py-2">{r.displayName}{!r.known && <span className="ml-1 text-xs text-fuchsia-300">(unknown)</span>}</td>
              <td><span className={`rounded px-2 py-0.5 text-xs ${HYPOTHESIS_STYLE[r.hypothesis]}`}>{r.hypothesis.replace(/_/g, " ")}</span></td>
              <td className="font-mono">{r.totals.requests}</td>
              <td className="font-mono">{r.totals.denied + r.totals.quarantineDecisions}</td>
              <td className="font-mono">{r.totals.incidents}</td>
              <td className="text-xs text-slate-400">{r.findings[0]?.title ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
