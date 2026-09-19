// Thin REST client. Every backend call goes through here (see docs/API.md).
import type {
  Agent,
  AgentDetail,
  AgentReport,
  EventPage,
  FleetOverview,
  IncidentDetail,
  PermissionGrant,
  RunState,
  ScenarioInfo,
  Snapshot,
} from "@/types/sentinel";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const SIM_URL = process.env.NEXT_PUBLIC_SIM_URL ?? "http://localhost:8001";

// A hung backend (accepting connections but never answering) must fail, not spin forever.
const TIMEOUT_MS = 10_000;

async function call<T>(base: string, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    signal: AbortSignal.timeout(TIMEOUT_MS),
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`${init?.method ?? "GET"} ${path} -> ${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

const post = (body: unknown = {}): RequestInit => ({ method: "POST", body: JSON.stringify(body) });
const qs = (params: Record<string, string | number | undefined>) => {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
};

export const api = {
  snapshot: () => call<Snapshot>(API_URL, "/api/snapshot"),
  agent: (id: string) => call<AgentDetail>(API_URL, `/api/agents/${id}`),
  quarantine: (id: string, reason = "Isolated by operator") =>
    call<Agent>(API_URL, `/api/agents/${id}/quarantine`, post({ reason })),
  release: (id: string, note = "Reviewed and released by operator") =>
    call<Agent>(API_URL, `/api/agents/${id}/release`, post({ note })),
  grant: (id: string, scope: string, ttlSeconds: number, reason: string) =>
    call<PermissionGrant>(API_URL, `/api/agents/${id}/grants`, post({ scope, ttlSeconds, reason })),
  revokeGrant: (grantId: string) => call<PermissionGrant>(API_URL, `/api/grants/${grantId}/revoke`, post()),
  incident: (id: string) => call<IncidentDetail>(API_URL, `/api/incidents/${id}`),
  events: (f: { agentId?: string; kind?: string; decision?: string; reasonCode?: string; beforeSeq?: number; limit?: number }) =>
    call<EventPage>(API_URL, `/api/events${qs(f)}`),
  overview: (days = 7) => call<FleetOverview>(API_URL, `/api/accountability/overview${qs({ days })}`),
  agentReport: (id: string, days = 7) => call<AgentReport>(API_URL, `/api/accountability/agents/${id}${qs({ days })}`),
  reset: () => call<{ status: string }>(API_URL, "/api/admin/reset", post()),
};

export const sim = {
  scenarios: () => call<ScenarioInfo[]>(SIM_URL, "/scenarios"),
  run: (id: string) => call<RunState>(SIM_URL, `/scenarios/${id}/run`, post()),
  runs: () => call<RunState[]>(SIM_URL, "/runs"),
  stopAll: () => call<{ stopped: number }>(SIM_URL, "/runs/stop-all", post()),
};
