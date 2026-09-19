"use client";
// Owner: Person 2. Shows system status + which ANS/analyzer adapters are live (never hide "mock").
import Link from "next/link";
import { useSentinel } from "@/lib/store";

export function TopBar() {
  const { connected, system, agents } = useSentinel();
  const quarantined = Object.values(agents).filter((a) => a.status === "quarantined").length;
  const secure = connected && quarantined === 0;
  return (
    <header className="flex items-center gap-4 border-b border-slate-800 px-4 py-2">
      <Link href="/" className="font-mono text-lg font-bold tracking-widest text-cyan-300">SENTINEL MESH</Link>
      <span className="text-sm text-slate-400">{system?.tenantName}</span>
      <nav className="ml-6 flex gap-4 text-sm text-slate-300">
        <Link href="/">Mission Control</Link>
        <Link href="/accountability">Accountability</Link>
      </nav>
      <div className="ml-auto flex items-center gap-3 font-mono text-xs">
        {system && (
          <>
            <Chip label={`ANS ${system.ansMode === "real" ? "LIVE" : "MOCK"}`} ok={system.ansMode === "real"} />
            <Chip label={system.analyzerMode === "gemini" ? `GEMINI ${system.geminiModel}` : "AI: RULE-BASED"} ok={system.analyzerMode === "gemini"} />
          </>
        )}
        <span className={secure ? "text-emerald-400" : "text-red-400"}>
          SYSTEM: {!connected ? "OFFLINE" : secure ? "SECURE" : `${quarantined} QUARANTINED`} ●
        </span>
      </div>
    </header>
  );
}

function Chip({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span className={`rounded border px-2 py-0.5 ${ok ? "border-cyan-700 text-cyan-300" : "border-amber-700 text-amber-300"}`}>
      {label}
    </span>
  );
}
