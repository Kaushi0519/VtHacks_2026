"use client";
// Owner: Person 2. Bottom panel: selected incident, else selected agent.
// Always shows IDENTITY (ANS) and BEHAVIOR (Sentinel risk) as separate things.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { riskColor, secondsLeft, time } from "@/lib/format";
import { useSentinel } from "@/lib/store";

export function Inspector() {
  const { selectedIncidentId, selectedAgentId, incidents, agents, grants } = useSentinel();
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(t);
  }, []);

  const incident = selectedIncidentId ? incidents[selectedIncidentId] : null;
  const agentId = incident?.agentId ?? selectedAgentId;
  const agent = agentId ? agents[agentId] : null;
  const agentGrants = Object.values(grants).filter((g) => g.agentId === agentId && g.kind === "temporary");

  if (!agent && !incident) {
    return <section className="border-t border-slate-800 p-4 text-sm text-slate-500">Select an agent or an event.</section>;
  }

  return (
    <section className="grid grid-cols-3 gap-6 border-t border-slate-800 p-4 text-sm">
      <div>
        {incident && (
          <p className="mb-2 font-semibold text-red-400">
            {incident.severity.toUpperCase()} · {incident.title}
          </p>
        )}
        {agent && (
          <>
            <p className="text-lg font-semibold">{agent.displayName} <span className="text-xs text-slate-400">{agent.role}</span></p>
            <p className="font-mono text-xs">
              IDENTITY (ANS):{" "}
              <span className={agent.identity?.verified ? "text-emerald-400" : "text-red-400"}>
                {agent.identity ? (agent.identity.verified ? "VERIFIED" : agent.identity.ansStatus) : "not checked yet"}
              </span>
              {agent.identity?.source === "mock" && <span className="text-amber-300"> (mock)</span>}
            </p>
            <p className="font-mono text-xs">
              BEHAVIORAL RISK: <span className={riskColor[agent.riskLevel]}>{agent.riskScore}/100 {agent.riskLevel.toUpperCase()}</span>
            </p>
            <p className="font-mono text-xs">STATUS: {agent.status.toUpperCase()}</p>
            <div className="mt-2 flex gap-2">
              {agent.status === "quarantined" ? (
                <button className="rounded bg-emerald-800 px-2 py-1" onClick={() => api.release(agent.id)}>RELEASE</button>
              ) : (
                <button className="rounded bg-red-800 px-2 py-1" onClick={() => api.quarantine(agent.id)}>QUARANTINE</button>
              )}
            </div>
          </>
        )}
      </div>

      <div>
        <h3 className="mb-1 font-mono text-xs tracking-widest text-slate-500">WHY</h3>
        {incident?.analysis ? (
          <p>
            {incident.analysis.reason}{" "}
            <span className="text-xs text-slate-500">
              ({incident.analysis.source === "gemini" ? `Gemini ${incident.analysis.model}` : "rule-based"},{" "}
              recommends {incident.analysis.recommendedAction})
            </span>
          </p>
        ) : incident ? (
          <p className="text-slate-500">Analysis {incident.analysisStatus}…</p>
        ) : (
          <p className="text-slate-500">{agent?.quarantine?.reason ?? agent?.description}</p>
        )}
      </div>

      <div>
        <h3 className="mb-1 font-mono text-xs tracking-widest text-slate-500">TEMPORARY ACCESS (DECAYS)</h3>
        {agentGrants.length === 0 && <p className="text-slate-500">None. Standing role permissions only.</p>}
        <ul className="space-y-1 font-mono text-xs">
          {agentGrants.map((g) => {
            const left = secondsLeft(g.expiresAt, now);
            return (
              <li key={g.id}>
                {g.scope}{" "}
                {g.status === "active" ? (
                  <span className="text-cyan-300">expires in {left}s</span>
                ) : (
                  <span className="text-slate-500">{g.status.toUpperCase()} {g.endedAt && time(g.endedAt)}</span>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
