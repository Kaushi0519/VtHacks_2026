"use client";
// Owner: Person 2. The live agent mesh: unverified callers | agents | resources.
// Every gateway decision fires a packet (green = allowed, red ✕ = blocked at Sentinel).
// Quarantined agents turn red and their links are cut. Unknown actors appear as ghost nodes.
// Live just-in-time grants draw as dashed edges with a countdown (plus the DecayHud overlay).
import { Background, ReactFlow, ReactFlowProvider, useReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useRef } from "react";
import { DecayHud } from "@/components/permissions/DecayHud";
import { isOnStage, isTemporary, resourceForScope } from "@/lib/grants";
import { useSentinel } from "@/lib/store";
import { useNow } from "@/lib/useNow";
import { edgeTypes, type GrantEdgeData, type MeshEdgeData, type PacketEdgeData } from "./edges";
import { agentPosition, COLUMN_X, ghostPosition, HEADER_Y, INK, resourcePosition } from "./layout";
import { nodeTypes } from "./nodes";
import { usePulses, type Pulse } from "./usePulses";

const FIT = { padding: 0.08 };

export function AgentMesh() {
  return (
    <ReactFlowProvider>
      <Mesh />
    </ReactFlowProvider>
  );
}

function Mesh() {
  const { graph, agents, resources, events, grants, selectedAgentId, selectAgent } = useSentinel();
  const pulses = usePulses();
  const now = useNow();
  // Edges only change when a grant appears or finishes fading out, not on every clock tick.
  const stagedGrants = Object.values(grants)
    .filter((g) => isTemporary(g) && isOnStage(g, now) && agents[g.agentId])
    .map((g) => g.id)
    .join(",");
  const wrapper = useRef<HTMLDivElement>(null);
  const { fitView } = useReactFlow();

  // Keep the whole mesh in frame when the panel resizes (window resize, inspector opening).
  useEffect(() => {
    const el = wrapper.current;
    if (!el) return;
    const ro = new ResizeObserver(() => fitView(FIT));
    ro.observe(el);
    return () => ro.disconnect();
  }, [fitView]);

  // Anyone who called the gateway but isn't an enrolled agent (e.g. the fake payroll-sync-bot).
  const ghosts = useMemo(() => {
    const seen = new Map<string, string>();
    for (const e of events) {
      if (e.kind === "request" && !agents[e.actorAgentId] && !seen.has(e.actorAgentId)) {
        seen.set(e.actorAgentId, e.identity?.ansStatus ?? "UNKNOWN");
      }
    }
    return [...seen].map(([actorId, ansStatus]) => ({ actorId, ansStatus }));
  }, [events, agents]);

  const nodes: Node[] = useMemo(() => {
    const agentIds = graph.nodes.filter((n) => n.kind === "agent").map((n) => n.id);
    const resourceIds = graph.nodes.filter((n) => n.kind === "resource").map((n) => n.id);
    const activeSources = new Set(pulses.map((p) => p.source));
    const hitTargets = new Set(pulses.map((p) => p.target));
    const resourceById = Object.fromEntries(resources.map((r) => [r.id, r]));
    const fixed = { draggable: false, selectable: false, connectable: false };

    const zone = (id: string, label: string, x: number, tone?: "crit"): Node => ({
      id,
      type: "zone",
      position: { x, y: HEADER_Y },
      data: { label, tone },
      ...fixed,
    });

    return [
      zone("zone-ghost", "Unverified callers", COLUMN_X.ghost, "crit"),
      zone("zone-agent", "Enrolled agents", COLUMN_X.agent),
      zone("zone-resource", "Resources", COLUMN_X.resource),
      ...graph.nodes
        .filter((n) => n.kind === "agent" && agents[n.id])
        .map((n) => ({
          id: n.id,
          type: "agent",
          position: agentPosition(n.id, agentIds),
          data: { agent: agents[n.id], active: activeSources.has(n.id), selected: selectedAgentId === n.id },
          ...fixed,
        })),
      ...graph.nodes
        .filter((n) => n.kind === "resource")
        .map((n) => ({
          id: n.id,
          type: "resource",
          position: resourcePosition(n.id, resourceIds),
          data: { label: n.label, resource: resourceById[n.id], hit: hitTargets.has(n.id) },
          ...fixed,
        })),
      ...ghosts.map((g, i) => ({ id: g.actorId, type: "ghost", position: ghostPosition(i), data: g, ...fixed })),
    ];
  }, [graph, agents, resources, ghosts, pulses, selectedAgentId]);

  // Refit when nodes appear (first snapshot, a new ghost). fitView-on-mount ran on an empty graph.
  const nodeCount = nodes.length;
  useEffect(() => {
    const raf = requestAnimationFrame(() => fitView(FIT));
    return () => cancelAnimationFrame(raf);
  }, [nodeCount, fitView]);

  const edges: Edge[] = useMemo(() => {
    const isAgent = (id: string) => Boolean(agents[id]);
    const quarantined = (id: string) => agents[id]?.status === "quarantined";

    const mesh: Edge<MeshEdgeData>[] = graph.edges.map((e) => {
      const touches = (id: string | null) => id !== null && (e.source === id || e.target === id);
      const state: MeshEdgeData["state"] =
        quarantined(e.source) || quarantined(e.target)
          ? "cut"
          : selectedAgentId
            ? touches(selectedAgentId) ? "focus" : "faded"
            : "normal";
      return { id: e.id, type: "mesh", data: { state }, ...route(e.source, e.target, isAgent) };
    });

    const packets: Edge<PacketEdgeData>[] = pulses
      .filter((p) => nodeExists(p, agents, resources, ghosts))
      .map((p) => ({ id: `packet-${p.id}`, type: "packet", data: { decision: p.decision }, zIndex: 10, ...route(p.source, p.target, isAgent) }));

    const grantEdges: Edge<GrantEdgeData>[] = (stagedGrants ? stagedGrants.split(",") : []).flatMap((id) => {
      const g = grants[id];
      const r = g && resourceForScope(g.scope, resources);
      return r ? [{ id: `grant-${id}`, type: "grant", data: { grantId: id }, zIndex: 5, ...route(g.agentId, r.id, isAgent) }] : [];
    });

    return [...mesh, ...grantEdges, ...packets];
  }, [graph, agents, resources, ghosts, pulses, grants, stagedGrants, selectedAgentId]);

  return (
    <div ref={wrapper} className="relative h-full min-h-0">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={FIT}
        colorMode="dark"
        nodesDraggable={false}
        nodesConnectable={false}
        zoomOnScroll={false}
        onNodeClick={(_, n) => n.type === "agent" && selectAgent(n.id)}
        onPaneClick={() => selectAgent(null)}
      >
        <Background color={INK.line} gap={22} size={1} />
      </ReactFlow>
      <Legend />
      <DecayHud />
    </div>
  );
}

// Agent→agent calls arc out on the left of the agent column; everything else flows left to right.
function route(source: string, target: string, isAgent: (id: string) => boolean) {
  const agentToAgent = isAgent(source) && isAgent(target);
  return { source, target, sourceHandle: agentToAgent ? "peer-out" : "out", targetHandle: "in" };
}

// Sources: agents or ghosts (ghosts only have an outgoing handle). Targets: agents or resources.
function nodeExists(p: Pulse, agents: Record<string, unknown>, resources: { id: string }[], ghosts: { actorId: string }[]) {
  const source = Boolean(agents[p.source]) || ghosts.some((g) => g.actorId === p.source);
  const target = Boolean(agents[p.target]) || resources.some((r) => r.id === p.target);
  return source && target;
}

function Legend() {
  return (
    <div className="pointer-events-none absolute bottom-3 left-3 flex gap-4 rounded-md border border-line bg-void/80 px-3 py-1.5 font-mono text-[10px] tracking-wider text-dim">
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-ok" /> ALLOWED
      </span>
      <span className="flex items-center gap-1.5">
        <span className="text-crit">✕</span> BLOCKED BY SENTINEL
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-4 border-t border-dashed border-crit" /> ISOLATED
      </span>
      <span className="flex items-center gap-1.5">
        <span className="w-4 border-t-2 border-dashed border-accent" /> TEMPORARY ACCESS
      </span>
    </div>
  );
}
