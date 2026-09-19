"use client";
// Accountability & visibility: what has each agent actually done? Owner: Person 2.
import { useEffect, useRef, useState } from "react";
import { AgentReportPanel } from "@/components/accountability/AgentReportPanel";
import { EventExplorer } from "@/components/accountability/EventExplorer";
import { FleetSummary, FleetTable, sortRows } from "@/components/accountability/FleetTable";
import { TopBar } from "@/components/layout/TopBar";
import { api } from "@/lib/api";
import { useSentinel } from "@/lib/store";
import { useSentinelStream } from "@/lib/stream";
import type { FleetOverview } from "@/types/sentinel";

const DAYS = 7;
const REFRESH_MS = 3000;

export default function AccountabilityPage() {
  useSentinelStream();
  const [chosen, setChosen] = useState<string | null>(null);
  const [overview, setOverview] = useState<FleetOverview | null>(null);
  const version = useRefreshVersion();

  useEffect(() => {
    let live = true;
    api.overview(DAYS).then((o) => live && setOverview(o)).catch(console.error);
    return () => {
      live = false;
    };
  }, [version]);

  const rows = overview ? sortRows(overview) : [];
  // Default to the most concerning agent so the page never opens empty.
  const selected = chosen && rows.some((r) => r.agentId === chosen) ? chosen : rows[0]?.agentId ?? null;
  const selectedName = rows.find((r) => r.agentId === selected)?.displayName ?? null;

  return (
    <div className="flex h-screen flex-col">
      <TopBar />
      {!overview ? (
        <p className="p-6 text-sm text-dim">Loading history… (empty? use &quot;Seed history&quot; on Mission Control)</p>
      ) : (
        <main className="flex min-h-0 flex-1 flex-col gap-3 p-3">
          <FleetSummary totals={overview.totals} days={DAYS} />
          <div className="grid min-h-0 flex-1 grid-cols-[340px_minmax(0,1fr)_minmax(0,0.9fr)] gap-3">
            <FleetTable rows={rows} selected={selected} onSelect={setChosen} />
            <div className="min-h-0 overflow-y-auto">
              {selected && <AgentReportPanel agentId={selected} days={DAYS} version={version} />}
            </div>
            <EventExplorer agentId={selected} agentName={selectedName} version={version} />
          </div>
        </main>
      )}
    </div>
  );
}

// Bumps at most every few seconds while live traffic arrives (throttle, not debounce: steady
// ambient traffic must still refresh), so the page stays current without refetching per event.
function useRefreshVersion(): number {
  const newest = useSentinel((s) => s.events[0]?.id ?? "");
  const latest = useRef(newest);
  const seen = useRef(newest);
  const [version, setVersion] = useState(0);
  useEffect(() => {
    latest.current = newest;
  }, [newest]);
  useEffect(() => {
    const t = setInterval(() => {
      if (latest.current !== seen.current) {
        seen.current = latest.current;
        setVersion((v) => v + 1);
      }
    }, REFRESH_MS);
    return () => clearInterval(t);
  }, []);
  return version;
}
