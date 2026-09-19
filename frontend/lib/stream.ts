"use client";
// Snapshot + SSE deltas. On every (re)connect or `resync` message we refetch the snapshot,
// so a backend restart or demo reset never leaves the dashboard stale.
import { useEffect } from "react";
import { API_URL, api } from "@/lib/api";
import { useSentinel } from "@/lib/store";
import type { StreamMessage } from "@/types/sentinel";

export function useSentinelStream() {
  useEffect(() => {
    const { hydrate, apply, setConnected } = useSentinel.getState();
    const refresh = () => api.snapshot().then(hydrate).catch((e) => console.error("snapshot failed", e));

    const es = new EventSource(`${API_URL}/api/events/stream`);
    es.onopen = () => {
      setConnected(true);
      refresh();
    };
    es.onerror = () => setConnected(false); // EventSource reconnects on its own
    es.onmessage = (msg) => {
      const m = JSON.parse(msg.data) as StreamMessage;
      if (m.type === "resync") refresh();
      else apply(m);
    };
    return () => es.close();
  }, []);
}
