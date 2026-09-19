"use client";
// Owner: Person 2. "What has this agent been doing, and what's wrong with it?"
import clsx from "clsx";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { time } from "@/lib/format";
import { GrantForm } from "@/components/permissions/GrantForm";
import { useSentinel } from "@/lib/store";
import type { AgentReport } from "@/types/sentinel";
import { HYPOTHESIS, SEVERITY_TEXT } from "./hypotheses";
import { RiskSparkline } from "./RiskSparkline";

export function AgentReportPanel({ agentId, days, version }: { agentId: string; days: number; version: number }) {
  const [report, setReport] = useState<AgentReport | null>(null);
  const policy = useSentinel((s) => s.system?.riskPolicy);
  const liveAgent = useSentinel((s) => s.agents[agentId]);
  useEffect(() => {
    let live = true;
    api.agentReport(agentId, days).then((r) => live && setReport(r)).catch(console.error);
    return () => {
      live = false;
    };
  }, [agentId, days, version]);

  if (!report || report.agentId !== agentId) return <section className="panel p-4 text-sm text-dim">Loading report…</section>;
  const h = HYPOTHESIS[report.hypothesis];
  const denials = Object.entries(report.denialsByReason).sort((a, b) => b[1] - a[1]);
  const maxDenial = Math.max(1, ...denials.map(([, n]) => n));
  const unused = report.grants?.unusedStanding ?? [];
  // In-role scopes it keeps getting refused: the likely fix for a misconfigured agent.
  const refusedInRole = report.scopes.filter((s) => s.inRole && s.denied > 0).map((s) => s.scope);

  return (
    <section className="panel space-y-4 p-4">
      <header>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className={clsx("text-xl font-semibold", report.known ? "text-slate-100" : "font-mono text-crit")}>
            {report.known ? report.displayName : `? ${report.displayName}`}
          </h2>
          <span className={clsx("rounded border px-2 py-0.5 font-mono text-xs tracking-wide", h.badge)}>
            {h.icon} {h.label.toUpperCase()}
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-400">{h.meaning}</p>
        {report.summary && (
          <p className="mt-2 rounded border border-accent/25 bg-accent/5 px-3 py-2 text-sm text-slate-200">
            <span className={clsx("mr-2 rounded border px-1.5 font-mono text-[10px]", report.summary.source === "gemini" ? "border-accent/50 text-accent" : "border-warn/50 text-warn")}>
              {report.summary.source === "gemini" ? `GEMINI · ${report.summary.model ?? ""}` : "AI: RULE-BASED"}
            </span>
            {report.summary.text}
          </p>
        )}
      </header>

      <div>
        <h3 className="panel-title mb-1.5">Findings</h3>
        {report.findings.length === 0 ? (
          <p className="text-sm text-ok">✓ No findings. Behavior consistent with its role.</p>
        ) : (
          <ul className="space-y-1.5">
            {report.findings.map((f) => (
              <li key={f.code + f.title} className="rounded border border-line bg-void/40 px-3 py-2">
                <p className="text-sm font-medium text-slate-100">
                  <span className={clsx("mr-2 font-mono text-[10px] font-bold tracking-wider", SEVERITY_TEXT[f.severity])}>{f.severity.toUpperCase()}</span>
                  {f.title}
                </p>
                <p className="mt-0.5 text-xs text-slate-400">{f.detail}</p>
              </li>
            ))}
          </ul>
        )}
        {liveAgent && liveAgent.status === "active" && (
          <GrantForm
            key={agentId}
            agentId={agentId}
            suggestions={refusedInRole}
            label={report.hypothesis === "likely_misconfigured" && refusedInRole[0] ? `FIX: GRANT ${refusedInRole[0]} TEMPORARILY` : "+ GRANT TEMPORARY ACCESS"}
          />
        )}
      </div>

      {report.known && (
        <div>
          <h3 className="panel-title mb-1">Behavioral risk · {days} days</h3>
          <RiskSparkline points={report.riskHistory} start={report.windowStart} end={report.windowEnd} policy={policy} />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <h3 className="panel-title mb-1.5">Why it was denied</h3>
          {denials.length === 0 ? (
            <p className="text-xs text-dim">Never denied in this window.</p>
          ) : (
            <ul className="space-y-1.5">
              {denials.map(([reason, n]) => (
                <li key={reason} title={`${n} denials: ${reason}`}>
                  <div className="flex justify-between font-mono text-[11px]">
                    <span className="text-slate-300">{reason}</span>
                    <span className="text-slate-100 tabular-nums">{n}</span>
                  </div>
                  <div className="mt-0.5 h-1.5 rounded-full bg-line">
                    <div className="h-full rounded-full bg-crit/80" style={{ width: `${(n / maxDenial) * 100}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h3 className="panel-title mb-1.5">What it touched</h3>
          <ul className="space-y-1.5">
            {report.scopes.slice(0, 7).map((s) => (
              <li key={s.scope} title={`${s.allowed} allowed, ${s.denied} denied${s.lastAt ? `, last ${time(s.lastAt)}` : ""}`}>
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span className={clsx("min-w-0 flex-1 truncate", s.inRole ? "text-slate-300" : "text-crit")}>{s.scope}</span>
                  {!s.inRole && <span className="text-[10px] font-bold text-crit">OUT OF ROLE</span>}
                  <span className="text-slate-100 tabular-nums">{s.total}</span>
                </div>
                {/* Allowed then denied, 2px gap between the two fills. */}
                <div className="mt-0.5 flex h-1.5 gap-0.5">
                  {s.allowed > 0 && <div className="h-full rounded-full bg-ok/80" style={{ flexGrow: s.allowed }} />}
                  {s.denied > 0 && <div className="h-full rounded-full bg-crit/80" style={{ flexGrow: s.denied }} />}
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-1.5 flex gap-3 font-mono text-[10px] text-dim">
            <span><span className="mr-1 inline-block h-1.5 w-2.5 rounded-full bg-ok/80" />allowed</span>
            <span><span className="mr-1 inline-block h-1.5 w-2.5 rounded-full bg-crit/80" />denied</span>
          </p>
          {unused.length > 0 && (
            <p className="mt-2 text-xs text-accent">
              ↓ Never used: <span className="font-mono">{unused.join(", ")}</span>
            </p>
          )}
        </div>
      </div>

      {report.incidents.length > 0 && (
        <div>
          <h3 className="panel-title mb-1.5">Incidents</h3>
          <ul className="space-y-1">
            {report.incidents.map((i) => (
              <li key={i.id} className="flex gap-2 text-xs">
                <span className={clsx("font-mono font-bold", SEVERITY_TEXT[i.severity])}>{i.severity.toUpperCase()}</span>
                <span className="min-w-0 flex-1 truncate text-slate-300">{i.title}</span>
                <span className="font-mono text-dim">{i.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
