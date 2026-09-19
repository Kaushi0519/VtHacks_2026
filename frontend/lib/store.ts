// Dashboard state: hydrated from /api/snapshot, then kept live by SSE deltas (lib/stream.ts).
import { create } from "zustand";
import type {
  Agent,
  GraphEdge,
  GraphNode,
  Incident,
  PermissionGrant,
  Resource,
  SentinelEvent,
  Snapshot,
  StreamMessage,
  SystemInfo,
} from "@/types/sentinel";

const MAX_EVENTS = 300;

interface SentinelState {
  connected: boolean;
  system: SystemInfo | null;
  agents: Record<string, Agent>;
  resources: Resource[];
  graph: { nodes: GraphNode[]; edges: GraphEdge[] };
  grants: Record<string, PermissionGrant>;
  incidents: Record<string, Incident>;
  events: SentinelEvent[]; // newest first, live traffic only (backfilled history excluded)
  lastEvent: SentinelEvent | null; // drives graph edge animation
  selectedAgentId: string | null;
  selectedIncidentId: string | null;

  setConnected: (v: boolean) => void;
  hydrate: (s: Snapshot) => void;
  apply: (m: StreamMessage) => void;
  selectAgent: (id: string | null) => void;
  selectIncident: (id: string | null) => void;
}

const byId = <T extends { id: string }>(items: T[]) => Object.fromEntries(items.map((x) => [x.id, x]));

export const useSentinel = create<SentinelState>((set) => ({
  connected: false,
  system: null,
  agents: {},
  resources: [],
  graph: { nodes: [], edges: [] },
  grants: {},
  incidents: {},
  events: [],
  lastEvent: null,
  selectedAgentId: null,
  selectedIncidentId: null,

  setConnected: (connected) => set({ connected }),

  hydrate: (s) =>
    set({
      system: s.system,
      agents: byId(s.agents),
      resources: s.resources,
      graph: s.graph,
      grants: byId(s.grants),
      incidents: byId(s.incidents),
      events: s.events.filter((e) => !e.metadata?.backfill),
    }),

  apply: (m) =>
    set((st) => {
      switch (m.type) {
        case "event": {
          if (st.events.some((e) => e.id === m.data.id)) return {};
          return { events: [m.data, ...st.events].slice(0, MAX_EVENTS), lastEvent: m.data };
        }
        case "agent":
          return { agents: { ...st.agents, [m.data.id]: m.data } };
        case "incident":
          return { incidents: { ...st.incidents, [m.data.id]: m.data } };
        case "grant":
          return { grants: { ...st.grants, [m.data.id]: m.data } };
        default:
          return {}; // "resync" is handled by the stream hook (refetch snapshot)
      }
    }),

  selectAgent: (selectedAgentId) => set({ selectedAgentId, selectedIncidentId: null }),
  selectIncident: (selectedIncidentId) => set({ selectedIncidentId }),
}));
