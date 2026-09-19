"use client";
// Mission Control. Owner: Person 2 (layout). Keep panels as separate components to avoid conflicts.
import { ActivityFeed } from "@/components/activity/ActivityFeed";
import { AgentList } from "@/components/agents/AgentList";
import { Inspector } from "@/components/agents/Inspector";
import { DemoControls } from "@/components/demo/DemoControls";
import { AgentMesh } from "@/components/graph/AgentMesh";
import { TopBar } from "@/components/layout/TopBar";
import { useSentinelStream } from "@/lib/stream";

export default function MissionControl() {
  useSentinelStream();
  return (
    <div className="grid h-screen grid-rows-[auto_1fr_auto_auto]">
      <TopBar />
      <main className="grid min-h-0 grid-cols-[240px_1fr_380px]">
        <AgentList />
        <AgentMesh />
        <ActivityFeed />
      </main>
      <Inspector />
      <DemoControls />
    </div>
  );
}
