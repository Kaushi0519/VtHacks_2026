"use client";
// Owner: Person 2.
import { decisionStyle, time } from "@/lib/format";
import { useSentinel } from "@/lib/store";

export function ActivityFeed() {
  const { events, agents, selectAgent, selectIncident } = useSentinel();
  return (
    <aside className="overflow-y-auto border-l border-slate-800 p-3">
      <h2 className="mb-2 font-mono text-xs tracking-widest text-slate-500">LIVE ACTIVITY</h2>
      <ul className="space-y-1 font-mono text-xs">
        {events.map((e) => {
          const d = e.decision ? decisionStyle[e.decision] : null;
          const who = agents[e.actorAgentId]?.displayName ?? e.actorAgentId;
          return (
            <li
              key={e.id}
              className="cursor-pointer rounded px-1 py-0.5 hover:bg-slate-800"
              onClick={() => (e.incidentId ? selectIncident(e.incidentId) : agents[e.actorAgentId] && selectAgent(e.actorAgentId))}
              title={e.reason ?? ""}
            >
              <span className="text-slate-500">{time(e.timestamp)} </span>
              {d ? <span className={d.className}>{d.icon} {d.label} </span> : <span className="text-cyan-300">{e.kind.toUpperCase()} </span>}
              <span className="text-slate-200">{who}</span>
              {e.action && <span className="text-slate-400"> {e.action}</span>}
              {e.riskBefore !== null && e.riskAfter !== null && e.riskAfter !== e.riskBefore && (
                <span className="text-orange-300"> risk {e.riskBefore}→{e.riskAfter}</span>
              )}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
