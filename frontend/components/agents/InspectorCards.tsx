"use client";
// Owner: Person 2. Inspector columns. Identity and behavior are deliberately separate cards:
// ANS answers "who is it?", Sentinel answers "is it behaving?". Never merge them into one "trust".
import clsx from "clsx";
import { levelFor, riskColor, riskFill, time } from "@/lib/format";
import { useSentinel } from "@/lib/store";
import type { Agent, IdentityResult, Incident, SentinelEvent } from "@/types/sentinel";

export function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="min-h-0 overflow-y-auto p-3">
      <div className="mb-2 flex items-baseline gap-2">
        <h3 className="panel-title">{title}</h3>
        {subtitle && <span className="text-[11px] text-dim italic">{subtitle}</span>}
      </div>
      {children}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-2 font-mono text-[11px]">
      <span className="text-dim">{label}</span>
      <span className="truncate text-right">{children}</span>
    </div>
  );
}

export function IdentityCard({ identity: id, atRequest }: { identity: IdentityResult | null; atRequest: boolean }) {
  return (
    <Section title="Identity · ANS" subtitle="who is it?">
      {!id ? (
        <p className="text-sm text-dim">Not checked yet. Identity is resolved on the agent&apos;s first request.</p>
      ) : (
        <>
          <p className={clsx("font-mono text-xl font-bold", id.verified ? "text-ok" : "text-crit")}>
            {id.verified ? "✓ VERIFIED" : `✕ ${id.ansStatus}`}
          </p>
          <p className="mb-2 truncate font-mono text-[11px] text-slate-400" title={id.ansName}>{id.ansName}</p>
          <div className="space-y-0.5">
            <Row label="Registry">
              {id.source === "mock" ? <span className="text-warn">MOCK ADAPTER</span> : <span className="text-accent">ANS LIVE</span>}
            </Row>
            <Row label="Status">{id.ansStatus}</Row>
            {id.source === "ans" && (
              <Row label="Transparency log">{id.tlVerified ? <span className="text-ok">receipt verified</span> : <span className="text-dim">not verified</span>}</Row>
            )}
            <Row label="Checked">
              {time(id.checkedAt)}
              {id.cached && <span className="text-dim"> (cached)</span>}
              {id.stale && <span className="text-warn"> STALE</span>}
            </Row>
          </div>
          {id.detail && <p className="mt-1.5 text-[11px] text-slate-400">{id.detail}</p>}
          <p className="mt-1.5 text-[10px] text-dim">{atRequest ? "As resolved for this request." : "Latest check."}</p>
        </>
      )}
    </Section>
  );
}

export function BehaviorCard({ agent, event }: { agent: Agent | null; event: SentinelEvent | null }) {
  const policy = useSentinel((s) => s.system?.riskPolicy);
  const moved = event && event.riskBefore !== null && event.riskAfter !== null;
  const score = moved ? event.riskAfter! : agent?.riskScore ?? null;

  if (score === null) {
    return (
      <Section title="Behavior · Sentinel" subtitle="is it behaving?">
        <p className="text-sm text-slate-400">
          Never scored. Sentinel stopped this caller at the identity check, before any behavior was evaluated.
        </p>
      </Section>
    );
  }

  const level = policy ? levelFor(score, policy) : agent?.riskLevel ?? "low";
  return (
    <Section title="Behavior · Sentinel" subtitle="is it behaving?">
      <p className="font-mono">
        {moved && event.riskBefore !== event.riskAfter && (
          <span className="text-xl text-dim">{event.riskBefore} → </span>
        )}
        <span className={clsx("text-xl font-bold", riskColor[level])}>{score}</span>
        <span className={clsx("ml-2 text-xs tracking-wider", riskColor[level])}>{level.toUpperCase()}</span>
      </p>
      <div className="relative mt-1 mb-2 h-1.5 overflow-hidden rounded-full bg-line">
        <div className={clsx("h-full transition-[width] duration-700", riskFill[level])} style={{ width: `${Math.min(100, score)}%` }} />
        {policy && <span className="absolute top-0 h-full w-px bg-slate-300/70" style={{ left: `${policy.thresholdCritical}%` }} title="Quarantine threshold" />}
      </div>

      {event ? (
        event.signals.length > 0 ? (
          <ul className="space-y-1">
            {event.signals.map((s) => (
              <li key={s.code} className="text-[11px]">
                <span className="font-mono font-bold text-high">+{s.weight}</span>{" "}
                <span className="font-mono text-slate-200">{s.code}</span>
                <span className="block text-slate-400">{s.detail}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-dim">No anomaly signals on this request.</p>
        )
      ) : (
        <p className="text-xs text-dim">
          Baseline {agent?.baselineRisk}. Quarantine at {policy?.thresholdCritical ?? "?"}. Score cools back toward baseline while it behaves.
        </p>
      )}
    </Section>
  );
}

export function AnalysisBox({ incident }: { incident: Incident }) {
  const a = incident.analysis;
  if (!a) {
    return (
      <p className="mb-2 rounded border border-line px-2 py-1.5 text-xs text-dim">
        {incident.analysisStatus === "pending" ? "AI analysis running (off the request path)…" : "Not analyzed."}
      </p>
    );
  }
  const gemini = a.source === "gemini";
  return (
    <div className="mb-2 rounded border border-accent/25 bg-accent/5 px-2 py-1.5">
      <div className="mb-1 flex flex-wrap items-center gap-1.5 font-mono text-[10px] tracking-wider">
        <span className={clsx("rounded border px-1.5", gemini ? "border-accent/50 text-accent" : "border-warn/50 text-warn")}>
          {gemini ? `GEMINI · ${a.model ?? ""}` : "AI: RULE-BASED"}
        </span>
        <span className="text-dim">{a.anomalyType.replaceAll("_", " ").toUpperCase()}</span>
        <span className="text-dim">· {Math.round(a.confidence * 100)}% conf.</span>
        <span className="text-dim">· recommends {a.recommendedAction.replace("_", " ")}</span>
      </div>
      <p className="text-sm text-slate-200">{a.reason}</p>
      <p className="mt-1 text-[10px] text-dim">Analysis only. The decision itself was made by deterministic policy.</p>
    </div>
  );
}
