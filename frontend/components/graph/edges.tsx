"use client";
// Two edge types:
//   mesh:   the standing topology (who normally talks to what). Dims/cuts on quarantine.
//   packet: one gateway decision. Allowed packets travel the whole way; blocked ones stop
//           halfway (at Sentinel) and burst into an ✕.
import { BaseEdge, getBezierPath, Position, type Edge, type EdgeProps } from "@xyflow/react";
import { useLayoutEffect, useRef } from "react";
import { countdownLabel } from "@/lib/grants";
import { useSentinel } from "@/lib/store";
import { useNow } from "@/lib/useNow";
import type { Decision } from "@/types/sentinel";
import { INK } from "./layout";

export type MeshEdgeData = { state: "normal" | "focus" | "faded" | "cut" };
export type PacketEdgeData = { decision: Decision };
export type GrantEdgeData = { grantId: string };

const MESH_STYLE: Record<MeshEdgeData["state"], React.CSSProperties> = {
  normal: { stroke: INK.edge, strokeWidth: 1.25 },
  focus: { stroke: INK.accent, strokeWidth: 1.75, opacity: 0.8 },
  faded: { stroke: INK.edge, strokeWidth: 1, opacity: 0.35 },
  cut: { stroke: INK.crit, strokeWidth: 1.25, strokeDasharray: "3 6", opacity: 0.55 },
};

// Left→left (agent→agent in the same column): React Flow's bezier degenerates to a straight
// line, so draw an explicit arc bulging left. Returns [path, midX, midY] like getBezierPath.
function edgePath(p: EdgeProps): [string, number, number] {
  if (p.sourcePosition !== Position.Left || p.targetPosition !== Position.Left) {
    const [path, x, y] = getBezierPath(p);
    return [path, x, y];
  }
  const { sourceX: sx, sourceY: sy, targetX: tx, targetY: ty } = p;
  const bulge = Math.max(50, Math.abs(ty - sy) * 0.45);
  const cx = Math.min(sx, tx) - bulge;
  // Cubic bezier at t = 0.5: 1/8·P0 + 3/8·P1 + 3/8·P2 + 1/8·P3
  return [`M${sx},${sy} C${cx},${sy} ${cx},${ty} ${tx},${ty}`, (sx + tx) / 8 + (cx * 3) / 4, (sy + ty) / 2];
}

export function MeshEdge(p: EdgeProps<Edge<MeshEdgeData>>) {
  const [path] = edgePath(p);
  return <BaseEdge id={p.id} path={path} style={MESH_STYLE[p.data?.state ?? "normal"]} />;
}

const PACKET_COLOR: Record<Decision, string> = {
  allow: INK.ok,
  deny: INK.crit,
  require_human: INK.warn,
  quarantine: INK.quarantine,
};

export function PacketEdge(p: EdgeProps<Edge<PacketEdgeData>>) {
  const [path, midX, midY] = edgePath(p);
  const decision = p.data?.decision ?? "allow";
  const color = PACKET_COLOR[decision];
  const blocked = decision !== "allow";
  const motion = useRef<SVGAnimateMotionElement>(null);

  // SMIL animations added after page load must be started by hand, or they "already finished".
  useLayoutEffect(() => motion.current?.beginElement(), []);

  return (
    <g className="packet pointer-events-none">
      <path d={path} fill="none" stroke={color} strokeWidth={2} className="packet-trail" />
      <circle r={5} fill={color} style={{ filter: `drop-shadow(0 0 6px ${color})` }}>
        <animateMotion
          ref={motion}
          begin="indefinite"
          dur={blocked ? "0.5s" : "0.9s"}
          fill="freeze"
          calcMode="linear"
          keyPoints={blocked ? "0;0.5" : "0;1"}
          keyTimes="0;1"
          path={path}
        />
      </circle>
      {blocked && (
        <g className="packet-block" transform={`translate(${midX} ${midY})`}>
          <circle r={11} fill="#04070d" stroke={color} strokeWidth={2} />
          <path d="M-4 -4 L4 4 M4 -4 L-4 4" stroke={color} strokeWidth={2.2} strokeLinecap="round" />
        </g>
      )}
    </g>
  );
}

// A just-in-time grant: marching cyan dashes with a live countdown; turns red and fades when it decays.
export function GrantEdge(p: EdgeProps<Edge<GrantEdgeData>>) {
  const grant = useSentinel((s) => (p.data ? s.grants[p.data.grantId] : undefined));
  const now = useNow();
  const [path, midX, midY] = edgePath(p);
  if (!grant) return null;
  const active = grant.status === "active";
  const color = active ? INK.accent : INK.crit;
  const label = active ? `⏱ ${countdownLabel(grant, now)}` : "✕ EXPIRED";
  return (
    <g className={active ? undefined : "grant-ended"}>
      <path d={path} fill="none" stroke={color} strokeWidth={2} strokeDasharray="6 4" className={active ? "grant-live" : undefined} />
      {/* Sits above the line so a blocked packet's ✕ (at the midpoint) doesn't cover it. */}
      <g transform={`translate(${midX} ${midY - 18})`}>
        <rect x={-40} y={-10} width={80} height={20} rx={4} fill="#04070d" stroke={color} strokeWidth={1} />
        <text textAnchor="middle" dy={4} fontSize={11} fontFamily="var(--font-geist-mono), monospace" fontWeight={700} fill={color}>
          {label}
        </text>
      </g>
    </g>
  );
}

export const edgeTypes = { mesh: MeshEdge, packet: PacketEdge, grant: GrantEdge };
