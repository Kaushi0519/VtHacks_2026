"use client";
// Owner: Person 2. One card per agent: identity (ANS) and behavior (risk meter) shown separately.
import clsx from "clsx";
import { riskColor, riskFill } from "@/lib/format";
import { DecayHud } from "@/components/permissions/DecayHud";
import { countdownLabel, isTemporary } from "@/lib/grants";
import { useSentinel } from "@/lib/store";
import { useNow } from "@/lib/useNow";
import type { Agent, RiskPolicy } from "@/types/sentinel";

export function AgentList() {
  const { agents, selectedAgentId, selectAgent, system } = useSentinel();
  const list = Object.values(agents);
  return (
    <aside className="panel flex min-h-0 flex-col">
      <div className="flex items-baseline justify-between px-3 pt-3 pb-2">
        <h2 className="panel-title">Agents</h2>
        <span className="font-mono text-[10px] text-dim">BEHAVIORAL RISK</span>
      </div>
      <ul className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-2 pb-2">
        {list.map((a) => (
          <li key={a.id}>
            <AgentCard agent={a} policy={system?.riskPolicy} selected={selectedAgentId === a.id} onSelect={() => selectAgent(a.id)} />
          </li>
        ))}
        {list.length === 0 && <li className="px-2 py-4 text-sm text-dim">Waiting for backend…</li>}
      </ul>
      <DecayHud />
    </aside>
  );
}

function AgentCard({ agent: a, policy, selected, onSelect }: { agent: Agent; policy?: RiskPolicy; selected: boolean; onSelect: () => void }) {
  const quarantined = a.status === "quarantined";
  const verified = a.identity?.verified;
  return (
    <button
      onClick={onSelect}
      className={clsx(
        "w-full rounded-md border px-2.5 py-2 text-left transition-colors",
        quarantined
          ? "border-crit/60 animate-alarm glow-crit"
          : selected
            ? "border-accent/50 bg-raised"
            : "border-transparent hover:border-line hover:bg-raised/60",
      )}
    >
      <div className="flex items-center gap-2">
        <span className={clsx("h-2 w-2 shrink-0 rounded-full", quarantined ? "bg-crit" : `${riskFill[a.riskLevel]} animate-pulse-soft`)} />
        <span className="min-w-0 flex-1 truncate text-sm font-medium text-slate-100">{a.displayName}</span>
        <span className={clsx("font-mono text-lg leading-none font-bold tabular-nums", riskColor[a.riskLevel])}>{a.riskScore}</span>
      </div>

      <RiskMeter score={a.riskScore} fill={riskFill[a.riskLevel]} policy={policy} />

      <div className="mt-1.5 flex items-center gap-1.5 font-mono text-[10px] tracking-wider">
        {quarantined ? (
          <span className="font-bold text-crit">⛔ QUARANTINED</span>
        ) : (
          <span className={riskColor[a.riskLevel]}>{a.riskLevel.toUpperCase()}</span>
        )}
        <TempAccessBadge agentId={a.id} />
        <span className="ml-auto" title={a.identity?.detail ?? a.ansName}>
          {!a.identity ? (
            <span className="text-dim">ANS ?</span>
          ) : verified ? (
            <span className="text-ok">ANS ✓{a.identity.source === "mock" && <span className="text-dim"> mock</span>}</span>
          ) : (
            <span className="text-crit">ANS ✕ {a.identity.ansStatus}</span>
          )}
        </span>
      </div>
    </button>
  );
}

// 0–100 bar with tick marks at the policy thresholds, so "how close to quarantine" is visible.
function RiskMeter({ score, fill, policy }: { score: number; fill: string; policy?: RiskPolicy }) {
  const ticks = policy ? [policy.thresholdElevated, policy.thresholdHigh, policy.thresholdCritical] : [];
  return (
    <div className="relative mt-1.5 h-1.5 overflow-hidden rounded-full bg-line">
      <div className={clsx("h-full rounded-full transition-[width] duration-700 ease-out", fill)} style={{ width: `${Math.min(100, score)}%` }} />
      {ticks.map((t) => (
        <span key={t} className="absolute top-0 h-full w-px bg-void/80" style={{ left: `${t}%` }} />
      ))}
    </div>
  );
}

// "⏱ 32s" while the agent holds a just-in-time grant (soonest expiry if several).
function TempAccessBadge({ agentId }: { agentId: string }) {
  const grants = useSentinel((s) => s.grants);
  const now = useNow();
  const live = Object.values(grants).filter((g) => g.agentId === agentId && isTemporary(g) && g.status === "active");
  if (live.length === 0) return null;
  const soonest = live.reduce((a, b) => ((a.expiresAt ?? "~") <= (b.expiresAt ?? "~") ? a : b));
  return (
    <span className="rounded border border-accent/50 px-1 text-accent" title={live.map((g) => g.scope).join(", ")}>
      ⏱ {countdownLabel(soonest, now)}
    </span>
  );
}
