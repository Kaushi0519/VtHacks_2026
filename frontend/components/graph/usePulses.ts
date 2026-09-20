"use client";
// One short-lived "packet" per gateway decision. Subscribes to the store directly so bursts
// (20 requests in ~2s) each get their own packet instead of being batched into one render.
import { useEffect, useState } from "react";
import { useSentinel } from "@/lib/store";
import type { Decision } from "@/types/sentinel";

export const PULSE_MS = 1100; // must outlast the longest packet animation in globals.css
const MAX_PULSES = 24;

export interface Pulse {
  id: string;
  source: string;
  target: string;
  decision: Decision;
}

export function usePulses(): Pulse[] {
  const [pulses, setPulses] = useState<Pulse[]>([]);

  useEffect(
    () =>
      useSentinel.subscribe((s, prev) => {
        const e = s.lastEvent;
        if (!e || e === prev.lastEvent || e.kind !== "request" || !e.decision) return;
        const target = e.targetAgentId ?? e.targetResource;
        if (!target) return; // unknown resource: nothing to draw a line to
        const pulse: Pulse = { id: e.id, source: e.actorAgentId, target, decision: e.decision };
        setPulses((ps) => [...ps.slice(-(MAX_PULSES - 1)), pulse]);
        setTimeout(() => setPulses((ps) => ps.filter((p) => p.id !== pulse.id)), PULSE_MS);
      }),
    [],
  );

  return pulses;
}
