"use client";
// Accountability & visibility: what has each agent actually done? Owner: Person 2.
import { FleetTable } from "@/components/accountability/FleetTable";
import { AgentReportPanel } from "@/components/accountability/AgentReportPanel";
import { EventExplorer } from "@/components/accountability/EventExplorer";
import { TopBar } from "@/components/layout/TopBar";
import { useSentinelStream } from "@/lib/stream";
import { useState } from "react";

export default function AccountabilityPage() {
  useSentinelStream();
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="grid flex-1 grid-cols-[1fr_1fr] gap-6 p-6">
        <FleetTable selected={selected} onSelect={setSelected} />
        <div className="space-y-6">
          {selected ? <AgentReportPanel agentId={selected} /> : <p className="text-slate-500">Select an agent to see its history.</p>}
          <EventExplorer agentId={selected} />
        </div>
      </main>
    </div>
  );
}
