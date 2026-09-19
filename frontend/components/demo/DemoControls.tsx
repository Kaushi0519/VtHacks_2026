"use client";
// Owner: Ishan. Presenter panel: trigger simulator scenarios (simulator control API, :8001).
// TODO(Ishan): show run caption/progress (GET /runs), hide behind a keyboard toggle for the demo.
import { useEffect, useState } from "react";
import { api, sim } from "@/lib/api";
import type { ScenarioInfo } from "@/types/sentinel";

export function DemoControls() {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    sim.scenarios().then(setScenarios).catch(() => setError("simulator offline (make sim)"));
  }, []);

  const run = (id: string) => sim.run(id).catch((e) => setError(String(e)));

  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-slate-800 px-4 py-2 text-xs">
      <span className="font-mono tracking-widest text-slate-500">DEMO</span>
      {scenarios.map((s) => (
        <button key={s.id} title={s.description} onClick={() => run(s.id)} className="rounded border border-slate-700 px-2 py-1 hover:bg-slate-800">
          {s.title}
        </button>
      ))}
      <button onClick={() => sim.stopAll()} className="rounded border border-slate-700 px-2 py-1">Stop</button>
      <button onClick={() => api.reset()} className="rounded border border-red-900 px-2 py-1 text-red-300">Reset</button>
      {error && <span className="text-amber-300">{error}</span>}
    </div>
  );
}
