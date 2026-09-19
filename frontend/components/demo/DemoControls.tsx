"use client";
// Owner: Ishan. Presenter panel: runs simulator scenarios (simulator control API, :8001).
// Steps mirror docs/DEMO.md. Keyboard: D hide/show · 1/2/3 steps · A ambient on/off · R reset.
// A scenario that is already running can't be started again (a double-click would stack runs,
// e.g. four overlapping decay grants whose expired reuse quarantines AnalyticsAgent).
import clsx from "clsx";
import { useEffect, useState } from "react";
import { api, sim } from "@/lib/api";
import { actionError } from "@/lib/format";
import type { RunState, ScenarioInfo } from "@/types/sentinel";

const POLL_MS = 1000;

// DEMO.md script steps. Step 1 starts decay early so its countdown runs during steps 2–3.
const STEPS = [
  { key: "1", label: "Normal + decay", runs: ["normal_operation", "permission_decay"] },
  { key: "2", label: "Fake agent", runs: ["fake_agent"] },
  { key: "3", label: "Compromised agent", runs: ["compromised_agent"] },
];
const AMBIENT = "ambient";
const BACKFILL = "history_backfill";

const isRunning = (r: RunState) => r.status === "running";

export function DemoControls() {
  const [scenarios, setScenarios] = useState<ScenarioInfo[] | null>(null);
  const [runs, setRuns] = useState<RunState[]>([]);
  const [simDown, setSimDown] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hidden, setHidden] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  // Clicked but not yet visible in the 1s poll: counts as running, so a fast double-click can't slip through.
  const [starting, setStarting] = useState<Set<string>>(new Set());

  // Scenario list + run status, polled so captions and button states stay live.
  useEffect(() => {
    let live = true;
    const tick = () => {
      Promise.all([scenarios ? Promise.resolve(scenarios) : sim.scenarios(), sim.runs()])
        .then(([sc, rs]) => {
          if (!live) return;
          setScenarios(sc);
          setRuns(rs);
          setSimDown(false);
        })
        .catch(() => live && setSimDown(true));
    };
    tick();
    const t = setInterval(tick, POLL_MS);
    return () => {
      live = false;
      clearInterval(t);
    };
  }, [scenarios]);

  const toggleHidden = () => setHidden((h) => !h);

  const available = new Set(scenarios?.map((s) => s.id));
  const runningIds = new Set([...runs.filter(isRunning).map((r) => r.scenarioId), ...starting]);
  const ambientRun = runs.find((r) => r.scenarioId === AMBIENT && isRunning(r));

  const fail = (e: unknown) => setError(actionError(e));
  const start = (ids: string[]) => {
    setError(null);
    // Skip anything already running or starting: this is the double-click guard.
    const fresh = ids.filter((id) => !runningIds.has(id));
    if (fresh.length === 0) return;
    setStarting((prev) => new Set([...prev, ...fresh]));
    fresh.forEach((id) =>
      sim
        .run(id)
        .then((run) => setRuns((rs) => [run, ...rs.filter((r) => r.id !== run.id)]))
        .catch(fail)
        .finally(() => setStarting((prev) => new Set([...prev].filter((x) => x !== id)))),
    );
  };
  const toggleAmbient = () => {
    setError(null);
    if (ambientRun) sim.stop(ambientRun.id).catch(fail);
    else start([AMBIENT]); // guarded like the other steps
  };
  const reset = () => {
    if (!confirmReset) {
      setConfirmReset(true);
      setTimeout(() => setConfirmReset(false), 3000);
      return;
    }
    setConfirmReset(false);
    setError(null);
    sim
      .stopAll()
      .catch(() => undefined) // simulator down shouldn't block a backend reset
      .then(() => api.reset())
      .catch(fail);
  };

  // Presenter keyboard shortcuts (ignored while typing in a form field). Re-bound every render
  // on purpose so the handlers always see the latest run state.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof Element && e.target.closest("input, textarea, select, [contenteditable]");
      if (e.metaKey || e.ctrlKey || e.altKey || e.repeat || typing) return;
      const k = e.key.toLowerCase();
      if (k === "d") toggleHidden();
      else if (k === "a" && available.has(AMBIENT)) toggleAmbient();
      else if (k === "r") reset();
      else {
        const step = STEPS.find((s) => s.key === k);
        if (step) start(step.runs.filter((id) => available.has(id)));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (hidden) return null;

  // Caption: the most recent non-looping run that's still going (ambient has nothing to narrate).
  const narrated = runs.find((r) => isRunning(r) && r.scenarioId !== AMBIENT);
  const steps = STEPS.map((s) => ({ ...s, runs: s.runs.filter((id) => available.has(id)) })).filter((s) => s.runs.length > 0);

  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-line bg-panel/80 px-4 py-2 text-xs">
      <span className="panel-title mr-1" title="Press D to hide or show">
        Demo
      </span>

      {simDown ? (
        <span className="text-warn">Simulator offline. Start it with `make sim`.</span>
      ) : (
        <>
          {available.has(BACKFILL) && (
            <DemoButton onClick={() => start([BACKFILL])} running={runningIds.has(BACKFILL)} title="Setup: a week of history for the Accountability page">
              Seed history
            </DemoButton>
          )}
          <span className="mx-1 h-4 w-px bg-line" />
          {steps.map((s) => (
            <DemoButton key={s.key} hotkey={s.key} onClick={() => start(s.runs)} running={s.runs.some((id) => runningIds.has(id))}>
              {s.label}
            </DemoButton>
          ))}
          {available.has(AMBIENT) && (
            <DemoButton hotkey="A" onClick={toggleAmbient} running={Boolean(ambientRun)} toggle title="Background traffic from every agent; click again to stop">
              Ambient {ambientRun ? "on" : "off"}
            </DemoButton>
          )}
          <button onClick={() => sim.stopAll().catch(fail)} className="rounded border border-line px-2 py-1 text-slate-300 hover:bg-raised">
            Stop all
          </button>
        </>
      )}
      <button
        onClick={reset}
        className={clsx(
          "rounded border px-2 py-1 transition-colors",
          confirmReset ? "border-crit bg-crit/20 font-bold text-crit" : "border-crit/40 text-crit/90 hover:bg-crit/10",
        )}
        title="Stops all scenarios and resets the backend (press R)"
      >
        {confirmReset ? "Click again to reset" : "Reset"}
      </button>

      {narrated && <Caption run={narrated} />}
      {error && <span className="text-crit">{error}</span>}
      <span className="ml-auto font-mono text-[10px] text-dim">D hides this bar</span>
    </div>
  );
}

function DemoButton({
  children,
  onClick,
  running,
  hotkey,
  toggle,
  title,
}: {
  children: React.ReactNode;
  onClick: () => void;
  running: boolean;
  hotkey?: string;
  toggle?: boolean;
  title?: string;
}) {
  // Toggles stay clickable while running (to switch off); one-shot steps are locked until done.
  const locked = running && !toggle;
  return (
    <button
      onClick={onClick}
      disabled={locked}
      title={title ?? (locked ? "Already running" : undefined)}
      className={clsx(
        "flex items-center gap-1.5 rounded border px-2 py-1 transition-colors",
        running ? "border-accent/60 bg-accent/10 text-accent" : "border-line text-slate-200 hover:bg-raised",
        locked && "cursor-not-allowed",
      )}
    >
      {hotkey && <kbd className="rounded bg-void px-1 font-mono text-[10px] text-dim">{hotkey}</kbd>}
      {running && <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-accent" />}
      {children}
    </button>
  );
}

function Caption({ run }: { run: RunState }) {
  const pct = run.totalSteps ? Math.min(100, ((run.stepIndex + 1) / run.totalSteps) * 100) : 0;
  return (
    <span className="ml-2 flex min-w-0 items-center gap-2 rounded border border-accent/30 bg-accent/5 px-2 py-1">
      <span className="font-mono text-[10px] text-accent">{run.title.toUpperCase()}</span>
      <span className="h-1 w-16 overflow-hidden rounded-full bg-line">
        <span className="block h-full bg-accent transition-[width] duration-500" style={{ width: `${pct}%` }} />
      </span>
      {run.caption && <span className="truncate text-slate-200">{run.caption}</span>}
    </span>
  );
}
