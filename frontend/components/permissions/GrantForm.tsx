"use client";
// Owner: Person 2. Operator issues a just-in-time grant. The backend decides whether the scope is
// grantable for the agent's role (403 otherwise); this form only suggests and submits.
import clsx from "clsx";
import { useState } from "react";
import { api } from "@/lib/api";
import { actionError } from "@/lib/format";

const DURATIONS = [
  { label: "30s", seconds: 30 },
  { label: "1 min", seconds: 60 },
  { label: "5 min", seconds: 300 },
  { label: "15 min", seconds: 900 },
];

export function GrantForm({
  agentId,
  suggestions,
  initialScope,
  label = "+ GRANT TEMPORARY ACCESS",
}: {
  agentId: string;
  suggestions: string[];
  initialScope?: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [scope, setScope] = useState(initialScope ?? suggestions[0] ?? "");
  const [ttl, setTtl] = useState(60);
  const [idle, setIdle] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  const listId = `grant-scopes-${agentId}`;

  if (!open) {
    return (
      <div className="mt-2">
        <button
          onClick={() => {
            setOpen(true);
            setResult(null);
            if (!scope) setScope(initialScope ?? suggestions[0] ?? "");
          }}
          className="rounded border border-accent/50 px-2.5 py-1 font-mono text-[11px] font-bold tracking-wider text-accent transition-colors hover:bg-accent/10"
        >
          {label}
        </button>
        {result?.ok && <p className="mt-1 text-[10px] text-ok">{result.text}</p>}
      </div>
    );
  }

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!scope.trim()) return;
    setBusy(true);
    setResult(null);
    api
      .grant(agentId, scope.trim(), ttl, reason.trim() || "Just-in-time access (operator)", idle ? Math.min(30, ttl) : undefined)
      .then((g) => {
        setResult({ ok: true, text: `✓ Granted ${g.scope}. It decays on its own.` });
        setOpen(false);
      })
      .catch((err) => setResult({ ok: false, text: actionError(err) }))
      .finally(() => setBusy(false));
  };

  return (
    <form onSubmit={submit} className="mt-2 space-y-1.5 rounded border border-accent/30 bg-accent/5 p-2 text-[11px]">
      <p className="panel-title !text-[10px]">Just-in-time grant</p>
      <input
        list={listId}
        value={scope}
        onChange={(e) => setScope(e.target.value)}
        placeholder="scope, e.g. payroll.hours.write"
        className="w-full rounded border border-line bg-void px-2 py-1 font-mono text-slate-100 outline-none focus:border-accent/60"
        autoFocus
      />
      <datalist id={listId}>
        {suggestions.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
      <div className="flex flex-wrap items-center gap-1">
        <span className="text-dim">for</span>
        {DURATIONS.map((d) => (
          <button
            type="button"
            key={d.seconds}
            onClick={() => setTtl(d.seconds)}
            className={clsx("rounded px-1.5 py-0.5 font-mono", ttl === d.seconds ? "bg-raised text-slate-100 ring-1 ring-accent/50" : "text-dim hover:text-slate-300")}
          >
            {d.label}
          </button>
        ))}
      </div>
      <label className="flex cursor-pointer items-center gap-1.5 text-dim">
        <input type="checkbox" checked={idle} onChange={(e) => setIdle(e.target.checked)} className="accent-cyan-400" />
        also ends if unused for {Math.min(30, ttl)}s
      </label>
      <input
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="reason (goes in the audit log)"
        className="w-full rounded border border-line bg-void px-2 py-1 text-slate-100 outline-none focus:border-accent/60"
      />
      {result && !result.ok && <p className="text-crit">{result.text}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={busy || !scope.trim()}
          className="rounded border border-accent/60 bg-accent/10 px-2.5 py-1 font-mono font-bold text-accent hover:bg-accent/20 disabled:opacity-50"
        >
          {busy ? "GRANTING…" : "GRANT"}
        </button>
        <button type="button" onClick={() => setOpen(false)} className="px-2 text-dim hover:text-slate-300">
          cancel
        </button>
      </div>
    </form>
  );
}
