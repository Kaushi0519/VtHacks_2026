"use client";
// Owner: Person 2. Behavioral risk over the report window. Fixed 0–100 scale, quarantine line,
// crosshair + tooltip on hover. Single series: no legend, the panel title names it.
import { useState } from "react";
import { levelFor, riskColor } from "@/lib/format";
import type { RiskPolicy } from "@/types/sentinel";
import { INK } from "@/components/graph/layout";

const W = 600;
const H = 96;
const PAD_T = 6;
const PAD_B = 6;

export function RiskSparkline({ points, start, end, policy }: { points: { timestamp: string; risk: number }[]; start: string; end: string; policy?: RiskPolicy }) {
  const [hover, setHover] = useState<number | null>(null);
  const t0 = new Date(start).getTime();
  const t1 = new Date(end).getTime();
  const x = (ts: string) => ((new Date(ts).getTime() - t0) / Math.max(1, t1 - t0)) * W;
  const y = (risk: number) => PAD_T + (1 - risk / 100) * (H - PAD_T - PAD_B);

  if (points.length === 0) return <p className="py-6 text-center text-xs text-dim">No scored activity in this window.</p>;

  const line = points.map((p, i) => `${i ? "L" : "M"}${x(p.timestamp).toFixed(1)},${y(p.risk).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.at(-1)!.timestamp).toFixed(1)},${H - PAD_B} L${x(points[0].timestamp).toFixed(1)},${H - PAD_B} Z`;
  const peak = points.reduce((a, b) => (b.risk > a.risk ? b : a));
  const hp = hover !== null ? points[hover] : null;

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    let best = 0;
    points.forEach((p, i) => {
      if (Math.abs(x(p.timestamp) - px) < Math.abs(x(points[best].timestamp) - px)) best = i;
    });
    setHover(best);
  };

  return (
    <div className="relative" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-24 w-full" role="img" aria-label={`Behavioral risk, peak ${peak.risk}`}>
        <line x1={0} x2={W} y1={H - PAD_B} y2={H - PAD_B} stroke={INK.line} vectorEffect="non-scaling-stroke" />
        {policy && (
          <line x1={0} x2={W} y1={y(policy.thresholdCritical)} y2={y(policy.thresholdCritical)} stroke={INK.crit} strokeOpacity={0.6} strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
        )}
        <path d={area} fill={INK.accent} fillOpacity={0.08} />
        <path d={line} fill="none" stroke={INK.accent} strokeWidth={2} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        {hp && (
          <line x1={x(hp.timestamp)} x2={x(hp.timestamp)} y1={PAD_T} y2={H - PAD_B} stroke={INK.dim} vectorEffect="non-scaling-stroke" />
        )}
      </svg>
      {/* Peak marker as HTML so it stays round despite the stretched SVG. */}
      <span
        className="pointer-events-none absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-void bg-accent"
        style={{ left: `${(x(peak.timestamp) / W) * 100}%`, top: `${(y(peak.risk) / H) * 96}px` }}
      />
      {policy && (
        <span className="pointer-events-none absolute right-0 font-mono text-[9px] text-crit/80" style={{ top: `${(y(policy.thresholdCritical) / H) * 100}%`, transform: "translateY(-110%)" }}>
          quarantine {policy.thresholdCritical}
        </span>
      )}
      {hp && (
        <div
          className="pointer-events-none absolute top-0 z-10 rounded border border-line bg-void px-2 py-1 font-mono text-[11px] whitespace-nowrap"
          style={{ left: `${(x(hp.timestamp) / W) * 100}%`, transform: x(hp.timestamp) > W * 0.7 ? "translateX(-105%)" : "translateX(8px)" }}
        >
          <span className={policy ? riskColor[levelFor(hp.risk, policy)] : "text-slate-100"}>risk {hp.risk}</span>
          <span className="block text-dim">{new Date(hp.timestamp).toLocaleString([], { hour12: false, month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</span>
        </div>
      )}
      <div className="mt-0.5 flex justify-between font-mono text-[9px] text-dim">
        <span>{new Date(start).toLocaleDateString([], { month: "short", day: "numeric" })}</span>
        <span>peak {peak.risk}</span>
        <span>now</span>
      </div>
    </div>
  );
}
