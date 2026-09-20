"use client";
// Owner: Person 2. Live decision stream. Click any row to have the inspector explain it.
import clsx from "clsx";
import { useState } from "react";
import { decisionStyle, time } from "@/lib/format";
import { useSentinel } from "@/lib/store";
import type { SentinelEvent } from "@/types/sentinel";

type Filter = "all" | "blocked" | "incidents";

const FILTERS: { id: Filter; label: string; match: (e: SentinelEvent) => boolean }[] = [
  { id: "all", label: "All", match: () => true },
  { id: "blocked", label: "Blocked", match: (e) => e.decision !== null && e.decision !== "allow" },
  { id: "incidents", label: "Incidents", match: (e) => e.incidentId !== null },
];

// Left accent bar per row; non-request events (quarantine, grant, analysis) get neutral tones.
const BAR: Record<string, string> = {
  allow: "bg-ok/60",
  deny: "bg-crit",
  require_human: "bg-warn",
  quarantine: "bg-fuchsia-400",
  analysis: "bg-accent/60",
};

export function ActivityFeed() {
  const { events, agents, selectedEventId, selectEvent } = useSentinel();
  const [filter, setFilter] = useState<Filter>("all");
  const match = FILTERS.find((f) => f.id === filter)!.match;
  const shown = events.filter(match);
  const blocked = events.filter(FILTERS[1].match).length;

  return (
    <aside className="panel flex min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 px-3 pt-3 pb-2">
        <h2 className="panel-title whitespace-nowrap">Live activity</h2>
        <span className="font-mono text-[10px] whitespace-nowrap text-dim" title={`${events.length} events, ${blocked} blocked`}>
          {events.length} · <span className={blocked ? "text-crit" : ""}>{blocked} blocked</span>
        </span>
        <div className="ml-auto flex gap-0.5 rounded-md border border-line p-0.5">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={clsx(
                "rounded px-1.5 py-0.5 font-mono text-[10px]",
                filter === f.id ? "bg-raised text-slate-100" : "text-dim hover:text-slate-300",
              )}
            >
              {f.label.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      <ul className="min-h-0 flex-1 space-y-px overflow-y-auto px-2 pb-2 font-mono text-xs">
        {shown.map((e) => (
          <FeedRow
            key={e.id}
            e={e}
            who={agents[e.actorAgentId]?.displayName ?? e.actorAgentId}
            known={Boolean(agents[e.actorAgentId])}
            selected={selectedEventId === e.id}
            onClick={() => selectEvent(e)}
          />
        ))}
        {shown.length === 0 && (
          <li className="px-2 py-6 text-center font-sans text-dim">
            {events.length === 0 ? "No traffic yet. Press 1 (or a demo button below) to start." : "Nothing matches this filter."}
          </li>
        )}
      </ul>
    </aside>
  );
}

// Allowed traffic is the quiet baseline; anything Lattice blocked or escalated stays loud.
function FeedRow({ e, who, known, selected, onClick }: { e: SentinelEvent; who: string; known: boolean; selected: boolean; onClick: () => void }) {
  const d = e.decision ? decisionStyle[e.decision] : null;
  const quiet = e.decision === "allow";
  const riskMoved = e.riskBefore !== null && e.riskAfter !== null && e.riskAfter !== e.riskBefore;
  return (
    <li>
      <button
        onClick={onClick}
        title={e.reason ?? ""}
        className={clsx(
          "feed-row relative flex w-full gap-2 overflow-hidden rounded py-1 pr-2 pl-3 text-left transition-colors",
          selected ? "bg-raised ring-1 ring-accent/50" : "hover:bg-raised/60",
          e.decision && !quiet && !selected && "bg-crit/5",
        )}
      >
        <span className={clsx("absolute inset-y-0 left-0 w-0.5", BAR[e.decision ?? e.kind] ?? "bg-line", quiet && "opacity-40")} />
        <span className="shrink-0 text-dim">{time(e.timestamp)}</span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-baseline gap-x-1.5">
            {d ? (
              <span className={clsx(quiet ? "text-ok/70" : ["font-bold", d.className])}>
                {d.icon} {d.label}
              </span>
            ) : (
              <span className="text-accent/80">{e.kind.replace("_", " ").toUpperCase()}</span>
            )}
            <span className={!known ? "text-crit" : quiet ? "text-slate-400" : "text-slate-100"}>{known ? who : `? ${who}`}</span>
            {riskMoved && (
              <span className={clsx("rounded px-1 text-[10px]", e.riskAfter! > e.riskBefore! ? "bg-high/15 text-high" : "bg-ok/15 text-ok")}>
                risk {e.riskBefore}→{e.riskAfter}
              </span>
            )}
            {e.incidentId && e.kind === "request" && !quiet && (
              <span className="rounded border border-crit/40 px-1 text-[10px] tracking-wider text-crit">INCIDENT</span>
            )}
          </span>
          {e.action && (
            <span className={clsx("block truncate", quiet ? "text-dim" : "text-slate-300")}>
              {e.action}
              {e.decision && !quiet && e.reasonCode && <span className="text-dim"> · {e.reasonCode}</span>}
            </span>
          )}
        </span>
      </button>
    </li>
  );
}
