"use client";
// Owner: Person 2. v0: static layout + status colors + the last event's edge highlighted.
// TODO(P2): animated packets per event, ghost nodes for unknown actors, cut edges on quarantine,
// dashed edges for active temporary grants, fixed hand-tuned positions.
import { Background, ReactFlow, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";
import { useSentinel } from "@/lib/store";

const EDGE_COLOR = { allow: "#34d399", deny: "#f87171", require_human: "#fcd34d", quarantine: "#e879f9" } as const;

export function AgentMesh() {
  const { graph, agents, lastEvent, selectAgent } = useSentinel();

  const nodes: Node[] = useMemo(() => {
    const agentNodes = graph.nodes.filter((n) => n.kind === "agent");
    const resourceNodes = graph.nodes.filter((n) => n.kind === "resource");
    const place = (i: number, total: number, radius: number) => ({
      x: 400 + radius * Math.cos((2 * Math.PI * i) / total),
      y: 300 + radius * Math.sin((2 * Math.PI * i) / total),
    });
    return [
      ...agentNodes.map((n, i) => {
        const a = agents[n.id];
        const quarantined = a?.status === "quarantined";
        return {
          id: n.id,
          position: place(i, agentNodes.length, 150),
          data: { label: `${n.label}\nrisk ${a?.riskScore ?? "-"}` },
          style: {
            background: quarantined ? "#450a0a" : "#0f172a",
            color: "#e2e8f0",
            border: `2px solid ${quarantined ? "#ef4444" : "#22d3ee"}`,
            whiteSpace: "pre-line" as const,
            fontSize: 12,
          },
        };
      }),
      ...resourceNodes.map((n, i) => ({
        id: n.id,
        position: place(i, resourceNodes.length, 290),
        data: { label: n.label },
        style: { background: "#020617", color: "#94a3b8", border: "1px dashed #475569", fontSize: 11 },
      })),
    ];
  }, [graph, agents]);

  const edges: Edge[] = useMemo(() => {
    const hot = lastEvent?.decision ? lastEvent : null;
    const hotTarget = hot?.targetAgentId ?? hot?.targetResource;
    return graph.edges.map((e) => {
      const quarantined = agents[e.source]?.status === "quarantined" || agents[e.target]?.status === "quarantined";
      const isHot = hot && e.source === hot.actorAgentId && e.target === hotTarget;
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        animated: Boolean(isHot),
        style: {
          stroke: isHot ? EDGE_COLOR[hot!.decision!] : quarantined ? "#7f1d1d" : "#334155",
          strokeWidth: isHot ? 3 : 1,
          strokeDasharray: quarantined ? "4 4" : undefined,
        },
      };
    });
  }, [graph, agents, lastEvent]);

  return (
    <div className="h-full min-h-0">
      <ReactFlow nodes={nodes} edges={edges} fitView colorMode="dark" onNodeClick={(_, n) => agents[n.id] && selectAgent(n.id)}>
        <Background />
      </ReactFlow>
    </div>
  );
}
