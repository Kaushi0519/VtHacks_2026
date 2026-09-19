"use client";
// Owner: Person 2. TODO(P2): risk sparkline from riskHistory, denial-reason bar chart.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { AgentReport } from "@/types/sentinel";
import { HYPOTHESIS_STYLE } from "./FleetTable";

export function AgentReportPanel({ agentId }: { agentId: string }) {
  const [report, setReport] = useState<AgentReport | null>(null);
  useEffect(() => {
    api.agentReport(agentId).then(setReport).catch(console.error);
  }, [agentId]);
  if (!report) return null;

  return (
    <section className="rounded border border-slate-800 p-4 text-sm">
      <p className="text-lg font-semibold">
        {report.displayName}{" "}
        <span className={`rounded px-2 py-0.5 text-xs ${HYPOTHESIS_STYLE[report.hypothesis]}`}>{report.hypothesis.replace(/_/g, " ")}</span>
      </p>
      <ul className="mt-3 space-y-2">
        {report.findings.map((f) => (
          <li key={f.code + f.title}>
            <span className="font-semibold">{f.title}</span>
            <span className="text-slate-400"> · {f.detail}</span>
          </li>
        ))}
        {report.findings.length === 0 && <li className="text-emerald-400">No findings. Behavior consistent with its role.</li>}
      </ul>
      <h3 className="mt-4 font-mono text-xs tracking-widest text-slate-500">DENIALS BY REASON</h3>
      <p className="font-mono text-xs">
        {Object.entries(report.denialsByReason).map(([k, v]) => `${k} ×${v}`).join("   ") || "none"}
      </p>
      <h3 className="mt-4 font-mono text-xs tracking-widest text-slate-500">SCOPES</h3>
      <ul className="font-mono text-xs">
        {report.scopes.slice(0, 8).map((s) => (
          <li key={s.scope} className={s.inRole ? "" : "text-red-400"}>
            {s.scope} · {s.allowed} allowed · {s.denied} denied {!s.inRole && "· OUT OF ROLE"}
          </li>
        ))}
      </ul>
    </section>
  );
}
