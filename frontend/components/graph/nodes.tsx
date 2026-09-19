"use client";
// Custom React Flow nodes for the mesh. Handles are invisible: edges attach at the sides.
//   agent:    in (left, target) · peer-out (left, source, for agent→agent arcs) · out (right, source)
//   resource: in (left, target)
//   ghost:    out (right, source)
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import clsx from "clsx";
import { riskColor, riskFill } from "@/lib/format";
import type { Agent, Resource } from "@/types/sentinel";

const hidden = "!h-1 !w-1 !min-w-0 !border-0 !bg-transparent";

export type AgentNodeData = { agent: Agent; active: boolean; selected: boolean };
export type ResourceNodeData = { label: string; resource?: Resource; hit: boolean };
export type GhostNodeData = { actorId: string; ansStatus: string };
export type ZoneNodeData = { label: string; tone?: "crit" };

export function AgentNode({ data: { agent: a, active, selected } }: NodeProps<Node<AgentNodeData>>) {
  const quarantined = a.status === "quarantined";
  return (
    <div
      className={clsx(
        "w-[200px] rounded-lg border bg-panel px-3 py-2 transition-shadow duration-300",
        quarantined ? "border-crit glow-crit animate-alarm" : selected ? "border-accent" : "border-accent/40",
        active && !quarantined && "shadow-[0_0_0_1px_#22d3ee,0_0_22px_rgb(34_211_238/0.45)]",
      )}
    >
      <Handle type="target" position={Position.Left} id="in" className={hidden} />
      <Handle type="source" position={Position.Left} id="peer-out" className={hidden} />
      <Handle type="source" position={Position.Right} id="out" className={hidden} />
      <div className="flex items-center gap-2">
        <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-slate-100">{a.displayName}</span>
        <span className={clsx("font-mono text-base leading-none font-bold tabular-nums", riskColor[a.riskLevel])}>{a.riskScore}</span>
      </div>
      <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-line">
        <div className={clsx("h-full transition-[width] duration-700", riskFill[a.riskLevel])} style={{ width: `${Math.min(100, a.riskScore)}%` }} />
      </div>
      <div className="mt-1 font-mono text-[9px] tracking-widest">
        {quarantined ? (
          <span className="font-bold text-crit">⛔ ISOLATED FROM MESH</span>
        ) : (
          <span className="text-dim">{a.role.toUpperCase()}</span>
        )}
      </div>
    </div>
  );
}

const SENSITIVITY_DOT: Record<string, string> = { low: "bg-ok", medium: "bg-warn", high: "bg-high", critical: "bg-crit" };

export function ResourceNode({ data: { label, resource: r, hit } }: NodeProps<Node<ResourceNodeData>>) {
  return (
    <div
      className={clsx(
        "flex w-[210px] items-center gap-2 rounded-md border border-dashed bg-void/80 px-3 py-2 transition-colors duration-300",
        hit ? "border-slate-400" : "border-line",
      )}
    >
      <Handle type="target" position={Position.Left} id="in" className={hidden} />
      <span className={clsx("h-1.5 w-1.5 shrink-0 rounded-full", SENSITIVITY_DOT[r?.sensitivity ?? "low"])} title={`${r?.sensitivity ?? "?"} sensitivity`} />
      <span className="min-w-0 flex-1 truncate text-xs text-slate-300">{label}</span>
      {r?.honeypot && <span className="font-mono text-[9px] text-dim">DECOY</span>}
    </div>
  );
}

export function GhostNode({ data: { actorId, ansStatus } }: NodeProps<Node<GhostNodeData>>) {
  return (
    <div className="w-[180px] rounded-lg border border-dashed border-crit/70 bg-crit/5 px-3 py-2 opacity-90">
      <Handle type="source" position={Position.Right} id="out" className={hidden} />
      <div className="truncate font-mono text-xs text-crit">? {actorId}</div>
      <div className="mt-0.5 font-mono text-[9px] tracking-widest text-crit/80">UNVERIFIED · ANS {ansStatus}</div>
    </div>
  );
}

export function ZoneNode({ data: { label, tone } }: NodeProps<Node<ZoneNodeData>>) {
  return <div className={clsx("panel-title whitespace-nowrap", tone === "crit" && "!text-crit/70")}>{label}</div>;
}

export const nodeTypes = { agent: AgentNode, resource: ResourceNode, ghost: GhostNode, zone: ZoneNode };
