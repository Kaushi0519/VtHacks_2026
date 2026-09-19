"use client";
// Owner: Person 2. Audit log over GET /api/events: every stored decision, filterable and paged.
import clsx from "clsx";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { decisionStyle } from "@/lib/format";
import type { Decision, SentinelEvent } from "@/types/sentinel";

const PAGE = 50;
const DECISIONS: (Decision | "all")[] = ["all", "allow", "deny", "require_human", "quarantine"];

export function EventExplorer({ agentId, agentName, version }: { agentId: string | null; agentName: string | null; version: number }) {
  const [decision, setDecision] = useState<Decision | "all">("all");
  const [onlyAgent, setOnlyAgent] = useState(true);
  const [page, setPage] = useState<{ key: string; items: SentinelEvent[]; next: number | null } | null>(null);
  const [open, setOpen] = useState<string | null>(null);

  const scopeAgent = onlyAgent ? agentId ?? undefined : undefined;
  const filters = { agentId: scopeAgent, decision: decision === "all" ? undefined : decision, limit: PAGE };
  const key = JSON.stringify(filters);

  useEffect(() => {
    let live = true;
    api
      .events(JSON.parse(key))
      .then((p) => live && setPage({ key, items: p.items, next: p.nextBeforeSeq }))
      .catch(console.error);
    return () => {
      live = false;
    };
  }, [key, version]);

  const loadMore = () => {
    if (!page?.next) return;
    api.events({ ...filters, beforeSeq: page.next }).then((p) => setPage({ key, items: [...page.items, ...p.items], next: p.nextBeforeSeq }));
  };

  const items = page?.key === key ? page.items : [];
  return (
    <section className="panel flex min-h-0 flex-col">
      <div className="flex flex-wrap items-center gap-2 px-3 pt-3 pb-2">
        <h2 className="panel-title mr-1">Audit log</h2>
        <div className="flex gap-0.5 rounded-md border border-line p-0.5">
          {DECISIONS.map((d) => (
            <button
              key={d}
              onClick={() => setDecision(d)}
              className={clsx("rounded px-1.5 py-0.5 font-mono text-[10px]", decision === d ? "bg-raised text-slate-100" : "text-dim hover:text-slate-300")}
            >
              {d === "all" ? "ALL" : decisionStyle[d].label}
            </button>
          ))}
        </div>
        {agentId && (
          <label className="flex cursor-pointer items-center gap-1.5 text-[11px] text-dim">
            <input type="checkbox" checked={onlyAgent} onChange={(e) => setOnlyAgent(e.target.checked)} className="accent-cyan-400" />
            only {agentName ?? agentId}
          </label>
        )}
        <span className="ml-auto font-mono text-[10px] text-dim">append-only · {items.length}{page?.next ? "+" : ""} shown</span>
      </div>

      <ul className="min-h-0 flex-1 overflow-y-auto px-2 pb-2 font-mono text-[11px]">
        {items.map((e) => {
          const d = e.decision ? decisionStyle[e.decision] : null;
          const expanded = open === e.id;
          return (
            <li key={e.id}>
              <button onClick={() => setOpen(expanded ? null : e.id)} className={clsx("flex w-full gap-2 rounded px-1.5 py-0.5 text-left", expanded ? "bg-raised" : "hover:bg-raised/60")}>
                <span className="shrink-0 text-dim">{new Date(e.timestamp).toLocaleString([], { hour12: false, month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
                <span className={clsx("w-24 shrink-0 whitespace-nowrap", d?.className ?? "text-accent")}>{d ? `${d.icon} ${d.label}` : e.kind.toUpperCase()}</span>
                <span className="w-32 shrink-0 truncate text-slate-300">{e.actorAgentId}</span>
                <span className="min-w-0 flex-1 truncate text-slate-400">{e.action ?? ""}</span>
                {e.decision !== "allow" && <span className="shrink-0 text-dim">{e.reasonCode}</span>}
              </button>
              {expanded && (
                <div className="mx-1.5 mb-1 rounded-b border-x border-b border-line px-2 py-1.5 font-sans text-xs text-slate-300">
                  {e.reason}
                  {e.signals.length > 0 && (
                    <span className="mt-1 block font-mono text-[10px] text-high">
                      {e.signals.map((s) => `+${s.weight} ${s.code}`).join("  ")}
                    </span>
                  )}
                  <span className="mt-1 block font-mono text-[10px] text-dim">
                    {e.id} · trace {e.traceId}
                    {e.identity && ` · ANS ${e.identity.ansStatus}${e.identity.source === "mock" ? " (mock)" : ""}`}
                    {e.metadata?.backfill ? " · history" : ""}
                  </span>
                </div>
              )}
            </li>
          );
        })}
        {page?.key === key && items.length === 0 && <li className="py-6 text-center font-sans text-dim">No events match.</li>}
        {page?.next && (
          <li className="pt-1 text-center">
            <button onClick={loadMore} className="rounded border border-line px-3 py-1 font-sans text-xs text-slate-300 hover:bg-raised">
              Load older
            </button>
          </li>
        )}
      </ul>
    </section>
  );
}
