"use client";
// Owner: Person 2. Shows system status + which ANS/analyzer adapters are live (never hide "mock").
import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSentinel } from "@/lib/store";

export function TopBar() {
  const { connected, system, agents } = useSentinel();
  const pathname = usePathname();
  const all = Object.values(agents);
  const quarantined = all.filter((a) => a.status === "quarantined").length;
  const atRisk = all.filter((a) => a.status === "active" && (a.riskLevel === "high" || a.riskLevel === "critical")).length;

  return (
    <header className="flex items-center gap-6 border-b border-line bg-panel/80 px-5 py-2.5 backdrop-blur">
      <Link href="/" className="flex items-center gap-2.5">
        <LatticeMark />
        <span className="font-mono text-base font-bold tracking-[0.35em] text-accent">LATTICE</span>
      </Link>
      {system && <span className="text-sm text-dim">{system.tenantName}</span>}

      <nav className="flex gap-1 text-sm">
        {[
          ["/", "Mission Control"],
          ["/accountability", "Accountability"],
        ].map(([href, label]) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "rounded-md px-3 py-1 transition-colors",
              pathname === href ? "bg-raised text-slate-100" : "text-dim hover:text-slate-200",
            )}
          >
            {label}
          </Link>
        ))}
      </nav>

      <div className="ml-auto flex items-center gap-2 font-mono text-[11px]">
        {system && (
          <>
            <ModeBadge
              live={system.ansMode === "real"}
              label={system.ansMode === "real" ? "ANS LIVE" : "ANS MOCK"}
              title={system.ansMode === "real" ? `Identity resolved via ANS (${system.ansBaseUrl})` : "Identity from the local mock adapter, not the ANS API"}
            />
            <ModeBadge
              live={system.analyzerMode === "gemini"}
              label={system.analyzerMode === "gemini" ? `AI: ${system.geminiModel ?? "GEMINI"}` : "AI: RULE-BASED"}
              title={system.analyzerMode === "gemini" ? "Incident analysis by Gemini (after the decision, never authorizes)" : "Incident analysis by deterministic rules (Gemini not configured)"}
            />
          </>
        )}
        <SystemStatus connected={connected} quarantined={quarantined} atRisk={atRisk} />
      </div>
    </header>
  );
}

function SystemStatus({ connected, quarantined, atRisk }: { connected: boolean; quarantined: number; atRisk: number }) {
  const state = !connected ? "offline" : quarantined > 0 ? "breach" : atRisk > 0 ? "watch" : "secure";
  const view = {
    offline: { text: "OFFLINE", dot: "bg-dim", box: "border-line text-dim" },
    secure: { text: "SECURE", dot: "bg-ok animate-pulse-soft", box: "border-ok/40 text-ok glow-ok" },
    watch: { text: `${atRisk} AT RISK`, dot: "bg-high animate-pulse-soft", box: "border-high/50 text-high" },
    breach: { text: `${quarantined} QUARANTINED`, dot: "bg-crit", box: "border-crit/60 text-crit glow-crit animate-alarm" },
  }[state];
  return (
    <span className={clsx("ml-2 flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm font-bold tracking-widest", view.box)}>
      <span className={clsx("h-2.5 w-2.5 rounded-full", view.dot)} />
      {view.text}
    </span>
  );
}

function ModeBadge({ live, label, title }: { live: boolean; label: string; title: string }) {
  return (
    <span
      title={title}
      className={clsx(
        "flex items-center gap-1.5 rounded border px-2 py-1",
        live ? "border-accent/50 text-accent" : "border-warn/50 bg-warn/10 text-warn",
      )}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", live ? "bg-accent animate-pulse-soft" : "bg-warn")} />
      {label}
    </span>
  );
}

function LatticeMark() {
  // Six vertices around a hexagon, each joined to its neighbours and spoked to a brighter core --
  // the product in one glyph: a mesh of agents with a control plane in the middle.
  const r = 9;
  const pts = Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 3) * i - Math.PI / 2;
    return [12 + r * Math.cos(a), 12 + r * Math.sin(a)] as const;
  });
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6 text-accent" fill="none" aria-hidden>
      <g stroke="currentColor" strokeWidth={1.1} strokeLinecap="round" opacity={0.75}>
        {pts.map(([x, y], i) => {
          const [nx, ny] = pts[(i + 1) % 6];
          return <line key={`r${i}`} x1={x} y1={y} x2={nx} y2={ny} />;
        })}
        {pts.map(([x, y], i) => (
          <line key={`s${i}`} x1={x} y1={y} x2={12} y2={12} opacity={0.55} />
        ))}
      </g>
      {pts.map(([x, y], i) => (
        <circle key={`v${i}`} cx={x} cy={y} r={1.9} fill="currentColor" />
      ))}
      <circle cx={12} cy={12} r={2.4} fill="currentColor" />
    </svg>
  );
}
