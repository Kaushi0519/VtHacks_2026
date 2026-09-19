"use client";
// Owner: Person 2. Inspector columns. Identity and behavior are deliberately separate cards:
// ANS answers "who is it?", Sentinel answers "is it behaving?". Never merge them into one "trust".
import clsx from "clsx";
import { levelFor, riskColor, riskFill, time } from "@/lib/format";
import { useSentinel } from "@/lib/store";
import type { Agent, BehaviorAnalysis, IdentityResult, Incident, SentinelEvent, Severity } from "@/types/sentinel";

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

const severityText: Record<Severity, string> = {
  low: "text-dim",
  medium: "text-warn",
  high: "text-high",
  critical: "text-crit",
};

// Did Gemini itself cause this quarantine, or did a deterministic rule? Both end as an isolated
// agent with a Gemini analysis attached, so the structured fields alone would mislabel a
// rule-triggered quarantine that happens to carry a Gemini analysis recommending one. We require
// the structured fields AND, when we have the quarantine event, its stored reason — the backend
// writes "Gemini semantic analysis flagged…" only on the AI path. Under-claiming is the safe
// direction: a miss downgrades the box to "advisory", never to a false security claim.
function quarantineEventFor(incident: Incident, events: SentinelEvent[]): SentinelEvent | null {
  return events.find((e) => e.kind === "quarantine" && e.incidentId === incident.id)
    ?? events.find((e) => e.kind === "quarantine")
    ?? null;
}

function aiTriggeredQuarantine(incident: Incident, events: SentinelEvent[]): boolean {
  const a = incident.analysis;
  if (!incident.quarantined || a?.source !== "gemini") return false;
  if (a.recommendedAction !== "quarantine" || a.severity !== "critical") return false;
  const q = quarantineEventFor(incident, events);
  return q ? Boolean(q.reason?.includes("Gemini")) : true;
}

// What the deterministic half of Sentinel saw in the requests leading up to this finding. Scoped to
// the events we actually hold and labeled with that count, so "clean" is a checkable claim about a
// stated window rather than a blanket assertion.
function staticChecks(agentId: string, events: SentinelEvent[], until: string) {
  const reqs = events
    .filter((e) => e.kind === "request" && e.actorAgentId === agentId && e.timestamp <= until)
    .slice(0, 25);
  return {
    n: reqs.length,
    identity: reqs.every((e) => e.identity?.verified !== false),
    permissions: reqs.every((e) => e.decision === "allow"),
    noRule: reqs.every((e) => e.signals.length === 0),
  };
}

function Check({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return (
    <span className={ok ? "text-ok" : "text-crit"}>
      {ok ? "✓" : "✕"} {children}
    </span>
  );
}

// A semantic review that fires with no rule behind it opens no incident, so its analysis lives only
// on the ANALYSIS event's metadata. That is exactly the case DEMO.md step 5d shows, so the box has
// to read from either source.
export function AnalysisBox({
  incident,
  event,
  events = [],
}: {
  incident?: Incident | null;
  event?: SentinelEvent | null;
  events?: SentinelEvent[];
}) {
  const feed = useSentinel((s) => s.events);
  const fromEvent = event?.kind === "analysis" ? (event.metadata.analysis as BehaviorAnalysis | undefined) ?? null : null;
  const a = incident?.analysis ?? fromEvent;
  if (!a) {
    if (!incident) return null;
    return (
      <p className="mb-2 rounded border border-line px-2 py-1.5 text-xs text-dim">
        {incident.analysisStatus === "pending" ? "AI analysis running (off the request path)…" : "Not analyzed."}
      </p>
    );
  }
  const gemini = a.source === "gemini";
  const aiQuarantine = incident ? aiTriggeredQuarantine(incident, events) : false;
  const quarantineReason = incident && aiQuarantine ? quarantineEventFor(incident, events)?.reason : null;
  const agentId = incident?.agentId ?? event?.actorAgentId ?? null;
  // Two views of the deterministic half: the checks it ran on the recent requests (what makes
  // "every one of these was allowed" checkable), and the incident's own signal codes.
  const checks = agentId ? staticChecks(agentId, feed, a.analyzedAt) : null;
  const signalCodes = incident?.signalCodes ?? [];

  return (
    <div className={clsx("mb-2 rounded border px-2 py-1.5", aiQuarantine ? "border-crit/50 bg-crit/10" : "border-accent/25 bg-accent/5")}>
      <div className="mb-1 flex flex-wrap items-center gap-1.5 font-mono text-[10px] tracking-wider">
        <span className={clsx("rounded border px-1.5", gemini ? "border-accent/50 text-accent" : "border-warn/50 text-warn")}>
          {gemini ? `GEMINI · ${a.model ?? ""}` : "AI: RULE-BASED"}
        </span>
        <span className={clsx("font-bold", severityText[a.severity])}>{a.severity.toUpperCase()}</span>
        <span className="text-dim">{a.anomalyType.replaceAll("_", " ").toUpperCase()}</span>
        <span className="text-dim">· {Math.round(a.confidence * 100)}% conf.</span>
        <span className="text-dim">· recommends {a.recommendedAction.replace("_", " ")}</span>
      </div>

      {/* The two detectors, side by side. This is the claim step 5d is built on. */}
      <div className="mb-1 font-mono text-[10px] tracking-wider">
        <span className="text-dim">STATIC POLICY</span>
        {checks && checks.n > 0 ? (
          <>
            <span className="text-dim"> · last {checks.n} req </span>
            <span className="inline-flex flex-wrap gap-x-2">
              <Check ok={checks.identity}>identity</Check>
              <Check ok={checks.permissions && signalCodes.length === 0}>permissions</Check>
              <Check ok={checks.noRule && signalCodes.length === 0}>
                {signalCodes.length === 0 ? "no rule violated" : signalCodes.join(", ")}
              </Check>
            </span>
          </>
        ) : (
          <span className={signalCodes.length === 0 ? "text-ok" : "text-high"}>
            : {signalCodes.length === 0 ? "no violation" : signalCodes.join(", ")}
          </span>
        )}
      </div>

      {a.violations.length > 0 && (
        <p className="mb-1 flex flex-wrap gap-1">
          {a.violations.map((v) => (
            <span key={v} className="rounded bg-raised px-1.5 font-mono text-[10px] text-slate-300">{v}</span>
          ))}
        </p>
      )}

      <p className="text-sm text-slate-200">{a.reason}</p>

      {aiQuarantine ? (
        <p className="mt-1 text-[10px] text-crit">
          AI-TRIGGERED QUARANTINE · Gemini&apos;s finding caused this isolation. Sentinel enforces it only for real
          Gemini analysis rated CRITICAL at high confidence; the rule-based fallback never enforces.
          {quarantineReason && <span className="mt-0.5 block text-slate-300">{quarantineReason}</span>}
        </p>
      ) : gemini ? (
        <p className="mt-1 text-[10px] text-dim">
          Advisory here. Gemini&apos;s severity adds bounded points to the Behavioral Risk Score — Sentinel owns the
          number — and this decision was made by deterministic policy.
        </p>
      ) : (
        <p className="mt-1 text-[10px] text-warn">
          Rule-based fallback, not a live model call. It never moves the score and never enforces.
        </p>
      )}
    </div>
  );
}
