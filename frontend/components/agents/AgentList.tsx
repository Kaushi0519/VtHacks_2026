"use client";
// Owner: Person 2.
import { riskColor } from "@/lib/format";
import { useSentinel } from "@/lib/store";

export function AgentList() {
  const { agents, selectedAgentId, selectAgent } = useSentinel();
  return (
    <aside className="overflow-y-auto border-r border-slate-800 p-3">
      <h2 className="mb-2 font-mono text-xs tracking-widest text-slate-500">AGENTS</h2>
      <ul className="space-y-1">
        {Object.values(agents).map((a) => (
          <li key={a.id}>
            <button
              onClick={() => selectAgent(a.id)}
              className={`flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm hover:bg-slate-800 ${
                selectedAgentId === a.id ? "bg-slate-800" : ""
              }`}
            >
              <span>
                <span className={a.status === "quarantined" ? "text-red-500" : "text-emerald-400"}>● </span>
                {a.displayName}
              </span>
              <span className={`font-mono ${riskColor[a.riskLevel]}`}>{a.riskScore}</span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
