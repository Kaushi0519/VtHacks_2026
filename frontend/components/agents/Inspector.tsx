"use client";
// Owner: Person 2. Bottom panel. Explains the selected decision / incident / agent.
// IDENTITY (ANS: who is it?) and BEHAVIOR (Lattice: is it behaving?) are always separate columns.
import clsx from "clsx";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { actionError, decisionStyle, time } from "@/lib/format";
import { useSentinel } from "@/lib/store";
import type { Agent, Incident, PermissionGrant, SentinelEvent } from "@/types/sentinel";
import { GrantForm } from "@/components/permissions/GrantForm";
import { GrantList } from "@/components/permissions/GrantList";
import { AnalysisBox, BehaviorCard, IdentityCard, Section } from "./InspectorCards";

export function Inspector() {
  const { selectedEventId, selectedIncidentId, selectedAgentId, incidents, agents, events, selectEvent, selectAgent } = useSentinel();
  const incident = selectedIncidentId ? incidents[selectedIncidentId] ?? null : null;
  const timeline = useIncidentEvents(incident);

  const event = selectedEventId
    ? events.find((e) => e.id === selectedEventId) ?? timeline.find((e) => e.id === selectedEventId) ?? null
    : null;
  // An incident with nothing else picked explains its trigger decision.
  const decision = event ?? (incident ? timeline.find((e) => e.id === incident.triggerEventId) ?? null : null);
  const agentId = decision?.actorAgentId ?? incident?.agentId ?? selectedAgentId;
  const agent = agentId ? agents[agentId] ?? null : null;

  if (!agent && !decision) {
    return (
      <section className="panel mx-3 mb-3 px-4 py-2 text-center text-xs text-dim">
        Click an agent in the mesh, or any decision in the live feed, to see why Lattice decided what it did.
      </section>
    );
  }

  return (
    <section className="panel relative mx-3 mb-3 grid h-48 grid-cols-[1fr_1fr_1fr_1.5fr] divide-x divide-line overflow-hidden">
      <button
        onClick={() => selectAgent(null)}
        className="absolute top-2 right-2 z-10 rounded px-1.5 font-mono text-xs text-dim hover:bg-raised hover:text-slate-200"
        title="Close"
      >
        ✕
      </button>
      <Subject agent={agent} actorId={agentId!} incident={incident} />
      <IdentityCard identity={decision?.identity ?? agent?.identity ?? null} atRequest={Boolean(decision)} />
      <BehaviorCard agent={agent} event={decision} />
      <Section title="Why">
        {decision && <DecisionLine e={decision} />}
        <AnalysisBox incident={incident} event={decision} events={timeline} />
        {incident && timeline.length > 0 && (
          <Timeline events={timeline} selectedId={decision?.id ?? null} onSelect={selectEvent} />
        )}
        {!decision && !incident && agent && (
          <p className="text-sm text-slate-400">
            {agent.quarantine?.reason ?? agent.description}
            <span className="mt-2 block text-xs text-dim">Pick one of its decisions in the live feed for the full reasoning.</span>
          </p>
        )}
      </Section>
    </section>
  );
}

// Full incident history (events may be older than the live feed). Refetches as the incident grows.
function useIncidentEvents(incident: Incident | null): SentinelEvent[] {
  const [loaded, setLoaded] = useState<{ id: string; events: SentinelEvent[] } | null>(null);
  const id = incident?.id;
  const version = incident?.updatedAt;
  useEffect(() => {
    if (!id) return;
    let live = true;
    api
      .incident(id)
      .then((d) => live && setLoaded({ id, events: [...d.events].sort((a, b) => a.seq - b.seq) }))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [id, version]);
  return id && loaded?.id === id ? loaded.events : [];
}

// Scopes this agent was recently refused for lack of a grant, plus scopes it held temporarily before.
// Only suggestions: the backend still decides what is grantable for the role.
function grantSuggestions(agentId: string, events: SentinelEvent[], grants: Record<string, PermissionGrant>): string[] {
  const refused = events
    .filter((e) => e.actorAgentId === agentId && e.action && (e.reasonCode === "NO_GRANT" || e.reasonCode === "GRANT_EXPIRED" || e.reasonCode === "GRANT_REVOKED"))
    .map((e) => e.action!);
  const held = Object.values(grants)
    .filter((g) => g.agentId === agentId && g.kind === "temporary")
    .map((g) => g.scope);
  return [...new Set([...refused, ...held])];
}

function Subject({ agent, actorId, incident }: { agent: Agent | null; actorId: string; incident: Incident | null }) {
  const { events, grants } = useSentinel();
  const quarantined = agent?.status === "quarantined";
  return (
    <Section title="Subject">
      {incident && (
        <div className={clsx("mb-2 rounded border px-2 py-1 text-xs", incident.status === "open" ? "border-crit/50 bg-crit/10 text-crit" : "border-line text-dim")}>
          <span className="font-mono font-bold">{incident.severity.toUpperCase()} INCIDENT</span>
          {incident.status === "resolved" && <span className="font-mono"> · RESOLVED</span>}
          <span className="mt-0.5 block text-slate-300">{incident.title}</span>
        </div>
      )}
      {agent ? (
        <>
          <p className="text-lg leading-tight font-semibold text-slate-100">{agent.displayName}</p>
          <p className="font-mono text-[11px] text-dim">{agent.role} · {agent.id}</p>
          {agent.currentTask && (
            // What the agent is SUPPOSED to be doing. Gemini judges its behavior against this, so
            // showing it is what makes "inconsistent with its task" a checkable claim, not a vibe.
            <p className="mt-1 rounded border border-line bg-raised/60 px-1.5 py-1 text-[11px] text-slate-300">
              <span className="font-mono text-[10px] tracking-wider text-dim">ASSIGNED TASK </span>
              {agent.currentTask}
            </p>
          )}
          <p className={clsx("mt-1.5 font-mono text-xs font-bold tracking-wider", quarantined ? "text-crit" : "text-ok")}>
            {quarantined ? "⛔ QUARANTINED" : "● ACTIVE"}
          </p>
          <OperatorActions agentId={agent.id} quarantined={quarantined} />
          <GrantList agentId={agent.id} />
          {!quarantined && <GrantForm key={agent.id} agentId={agent.id} suggestions={grantSuggestions(agent.id, events, grants)} />}
        </>
      ) : (
        <>
          <p className="font-mono text-base font-semibold text-crit">? {actorId}</p>
          <p className="mt-1 text-xs text-slate-400">Not an enrolled agent of this organization. It has no permissions here at all.</p>
        </>
      )}
    </Section>
  );
}

function OperatorActions({ agentId, quarantined }: { agentId: string; quarantined: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    fn()
      .catch((e) => setError(actionError(e)))
      .finally(() => setBusy(false));
  };
  return (
    <>
      <button
        disabled={busy}
        onClick={() => run(() => (quarantined ? api.release(agentId) : api.quarantine(agentId)))}
        className={clsx(
          "mt-2 rounded border px-2.5 py-1 font-mono text-[11px] font-bold tracking-wider transition-colors disabled:opacity-50",
          quarantined ? "border-ok/50 text-ok hover:bg-ok/10" : "border-crit/50 text-crit hover:bg-crit/10",
        )}
      >
        {quarantined ? "RELEASE AFTER REVIEW" : "QUARANTINE NOW"}
      </button>
      {error && <p className="mt-1 text-[10px] text-crit">{error}</p>}
    </>
  );
}

function DecisionLine({ e }: { e: SentinelEvent }) {
  const d = e.decision ? decisionStyle[e.decision] : null;
  return (
    <div className="mb-2">
      <p className="font-mono text-xs">
        {d ? <span className={clsx("font-bold", d.className)}>{d.icon} {d.label}</span> : <span className="text-accent">{e.kind.toUpperCase()}</span>}
        {e.action && <span className="text-slate-300"> {e.action}</span>}
        {e.reasonCode && <span className="text-dim"> · {e.reasonCode}</span>}
        <span className="text-dim"> · {time(e.timestamp)}</span>
      </p>
      {e.reason && <p className="mt-0.5 text-sm text-slate-200">{e.reason}</p>}
    </div>
  );
}

function Timeline({ events, selectedId, onSelect }: { events: SentinelEvent[]; selectedId: string | null; onSelect: (e: SentinelEvent) => void }) {
  return (
    <div className="mt-2">
      <p className="panel-title mb-1">Incident timeline</p>
      <ol className="space-y-px font-mono text-[11px]">
        {events.map((e) => {
          const d = e.decision ? decisionStyle[e.decision] : null;
          return (
            <li key={e.id}>
              <button
                onClick={() => onSelect(e)}
                className={clsx("flex w-full gap-2 rounded px-1 text-left", e.id === selectedId ? "bg-raised" : "hover:bg-raised/60")}
              >
                <span className="text-dim">{time(e.timestamp)}</span>
                <span className={d?.className ?? "text-accent"}>{d ? d.label : e.kind.toUpperCase()}</span>
                <span className="truncate text-slate-400">{e.action ?? e.reasonCode}</span>
                {e.riskBefore !== null && e.riskAfter !== null && e.riskAfter !== e.riskBefore && (
                  <span className="ml-auto shrink-0 text-high">{e.riskBefore}→{e.riskAfter}</span>
                )}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
