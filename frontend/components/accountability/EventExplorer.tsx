"use client";
// Owner: Person 2. Audit log explorer over GET /api/events. TODO(P2): filters UI, paging, trace view.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { decisionStyle } from "@/lib/format";
import type { SentinelEvent } from "@/types/sentinel";

export function EventExplorer({ agentId }: { agentId: string | null }) {
  const [events, setEvents] = useState<SentinelEvent[]>([]);
  useEffect(() => {
    api.events({ agentId: agentId ?? undefined, limit: 100 }).then((p) => setEvents(p.items)).catch(console.error);
  }, [agentId]);

  return (
    <section>
      <h2 className="mb-2 font-mono text-xs tracking-widest text-slate-500">AUDIT LOG {agentId && `· ${agentId}`}</h2>
      <ul className="max-h-[50vh] space-y-0.5 overflow-y-auto font-mono text-xs">
        {events.map((e) => {
          const d = e.decision ? decisionStyle[e.decision] : null;
          return (
            <li key={e.id} title={e.reason ?? ""}>
              <span className="text-slate-500">{new Date(e.timestamp).toLocaleString([], { hour12: false })} </span>
              {d ? <span className={d.className}>{d.label} </span> : <span className="text-cyan-300">{e.kind} </span>}
              {e.actorAgentId} {e.action} <span className="text-slate-500">{e.reasonCode}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
