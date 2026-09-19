// World configuration numeric ranges and consistency are validated by the backend.
// MIRROR of backend/app/models/*.py (the source of truth) and docs/API.md.
// Change all three in the same commit. Person 1 reviews contract changes.

export type Decision = "allow" | "deny" | "require_human" | "quarantine";
export type RiskLevel = "low" | "elevated" | "high" | "critical";
export type Severity = "low" | "medium" | "high" | "critical";
export type Sensitivity = Severity;

export interface IdentityResult {
  ansName: string;
  verified: boolean;
  ansStatus: string; // ACTIVE | REVOKED | EXPIRED | NOT_FOUND | UNREACHABLE | INVALID_NAME | ...
  source: "ans" | "mock"; // "mock" must be labeled in the UI
  ansAgentId: string | null;
  tlVerified: boolean; // Transparency-Log SCITT receipt cryptographically verified (real mode)
  checkedAt: string;
  cached: boolean;
  stale: boolean;
  detail: string | null;
}

export interface QuarantineInfo {
  since: string;
  reason: string;
  triggeredBy: "auto" | "operator";
  incidentId: string | null;
  eventId: string | null;
}

export interface Agent {
  id: string;
  displayName: string;
  role: string;
  description: string;
  currentTask: string; // what the agent is currently supposed to be doing; Gemini judges consistency
  ansName: string;
  identity: IdentityResult | null;
  status: "active" | "quarantined";
  riskScore: number; // Sentinel Behavioral Risk Score, NOT an ANS trust score
  riskLevel: RiskLevel;
  baselineRisk: number;
  riskUpdatedAt: string;
  quarantine: QuarantineInfo | null;
  peers: string[];
  expectedRpm: number;
  lastSeenAt: string | null;
}

export interface BehaviorProfile {
  agentId: string;
  scopeCounts: Record<string, number>;
  resourceCounts: Record<string, number>;
  peerCounts: Record<string, number>;
  signalLastFired: Record<string, string>;
  updatedAt: string | null;
}

export interface Resource {
  id: string;
  displayName: string;
  scopePrefix: string;
  sensitivity: Sensitivity;
  requiresHuman: string[];
  honeypot: boolean;
}

export interface RiskPolicy {
  thresholdElevated: number;
  thresholdHigh: number;
  thresholdCritical: number;
  [weight: string]: number;
}

export interface PermissionGrant {
  id: string;
  agentId: string;
  scope: string;
  kind: "baseline" | "temporary";
  status: "active" | "expired" | "revoked";
  grantedAt: string;
  expiresAt: string | null;
  idleTimeoutSeconds: number | null;
  lastUsedAt: string | null;
  useCount: number;
  grantedBy: string;
  reason: string | null;
  endedAt: string | null;
  endReason: string | null;
}

export type EventKind =
  | "request"
  | "quarantine"
  | "release"
  | "grant_issued"
  | "grant_expired"
  | "grant_revoked"
  | "analysis";

export type ReasonCode =
  | "ALLOWED"
  | "IDENTITY_UNVERIFIED"
  | "IDENTITY_UNAVAILABLE"
  | "AGENT_NOT_ENROLLED"
  | "AGENT_QUARANTINED"
  | "UNKNOWN_RESOURCE"
  | "FORBIDDEN_FOR_ROLE"
  | "NO_GRANT"
  | "GRANT_EXPIRED"
  | "GRANT_REVOKED"
  | "REQUIRES_HUMAN"
  | "RISK_THRESHOLD"
  | "AI_SEMANTIC_QUARANTINE"
  | "OPERATOR_ACTION"
  | "TTL_ELAPSED"
  | "IDLE_TIMEOUT"
  | "QUARANTINE_CLEANUP"
  | "ANALYSIS_COMPLETE";

export type SignalCode =
  | "FORBIDDEN_SCOPE"
  | "NEW_SENSITIVE_RESOURCE"
  | "RATE_SPIKE"
  | "UNEXPECTED_PEER"
  | "REPEATED_DENIALS"
  | "EXPIRED_GRANT_USE"
  | "HONEYPOT_ACCESS"
  | "AI_ASSESSMENT";

export interface RiskSignal {
  code: SignalCode;
  weight: number;
  detail: string;
}

export interface SentinelEvent {
  id: string;
  seq: number;
  traceId: string;
  parentEventId: string | null;
  timestamp: string;
  kind: EventKind;
  actorAgentId: string;
  actorAnsName: string | null;
  targetAgentId: string | null;
  targetResource: string | null;
  action: string | null;
  delegationChain: string[];
  identity: IdentityResult | null;
  decision: Decision | null;
  reasonCode: ReasonCode | null;
  reason: string | null;
  riskBefore: number | null;
  riskAfter: number | null;
  signals: RiskSignal[];
  incidentId: string | null;
  grantId: string | null;
  initiatedBy: string;
  metadata: Record<string, unknown> & { backfill?: boolean; source?: string };
}

export type AnomalyType =
  | "role_resource_mismatch"
  | "privilege_escalation"
  | "rate_anomaly"
  | "unusual_peer"
  | "expired_access_reuse"
  | "identity_failure"
  | "benign"
  | "other";

export interface BehaviorAnalysis {
  anomalyType: AnomalyType;
  severity: Severity;
  confidence: number;
  violations: string[]; // semantic violation tags Gemini named, e.g. "task deviation", "possible exfiltration"
  reason: string;
  recommendedAction: "none" | "monitor" | "require_human" | "quarantine";
  source: "gemini" | "fallback"; // label fallback as "rule-based"
  model: string | null;
  analyzedAt: string;
  error: string | null;
}

export interface Incident {
  id: string;
  agentId: string;
  agentKnown: boolean;
  title: string;
  severity: Severity;
  status: "open" | "resolved";
  openedAt: string;
  updatedAt: string;
  resolvedAt: string | null;
  triggerEventId: string;
  eventIds: string[];
  traceIds: string[];
  reasonCodes: string[];
  signalCodes: string[];
  riskPeak: number | null;
  quarantined: boolean;
  analysis: BehaviorAnalysis | null;
  analysisStatus: "pending" | "done" | "skipped";
  resolutionNote: string | null;
}

export interface IncidentDetail {
  incident: Incident;
  events: SentinelEvent[];
}

export interface AgentDetail {
  agent: Agent;
  profile: BehaviorProfile;
  grants: PermissionGrant[];
  recentEvents: SentinelEvent[];
  openIncident: Incident | null;
}

export interface EventPage {
  items: SentinelEvent[];
  nextBeforeSeq: number | null;
}

export interface SystemInfo {
  tenantName: string;
  ansMode: "real" | "mock";
  ansBaseUrl: string | null;
  analyzerMode: "gemini" | "fallback";
  geminiModel: string | null;
  riskPolicy: RiskPolicy;
  backfillEnabled: boolean;
  serverTime: string;
}

export interface GraphNode {
  id: string;
  kind: "agent" | "resource";
  label: string;
  group: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  kind: "peer" | "access";
}

export interface Snapshot {
  system: SystemInfo;
  agents: Agent[];
  resources: Resource[];
  graph: { nodes: GraphNode[]; edges: GraphEdge[] };
  grants: PermissionGrant[];
  incidents: Incident[];
  events: SentinelEvent[]; // newest first
  lastSeq: number;
}

export type StreamMessage =
  | { type: "event"; data: SentinelEvent }
  | { type: "agent"; data: Agent }
  | { type: "incident"; data: Incident }
  | { type: "grant"; data: PermissionGrant }
  | { type: "resync"; data: Record<string, never> };

// --- accountability ---
export type Hypothesis =
  | "healthy"
  | "likely_misconfigured"
  | "possibly_compromised"
  | "unverified_identity"
  | "over_privileged"
  | "inactive";

export interface Finding {
  code: string;
  severity: Severity;
  hypothesis: Hypothesis;
  title: string;
  detail: string;
  evidenceEventIds: string[];
}

export interface ActivityTotals {
  requests: number;
  allowed: number;
  denied: number;
  requireHuman: number;
  quarantineDecisions: number;
  identityFailures: number;
  expiredGrantAttempts: number;
  incidents: number;
  quarantines: number;
}

export interface AgentActivityRow {
  agentId: string;
  displayName: string;
  role: string | null;
  known: boolean;
  status: "active" | "quarantined" | null;
  riskScore: number | null;
  totals: ActivityTotals;
  topReason: string | null;
  hypothesis: Hypothesis;
  findings: Finding[];
  lastSeenAt: string | null;
}

export interface FleetOverview {
  windowStart: string;
  windowEnd: string;
  totals: ActivityTotals;
  agents: AgentActivityRow[];
  unknownActors: AgentActivityRow[];
}

export interface AgentReport {
  agentId: string;
  displayName: string;
  known: boolean;
  windowStart: string;
  windowEnd: string;
  totals: ActivityTotals;
  denialsByReason: Record<string, number>;
  scopes: { scope: string; total: number; allowed: number; denied: number; inRole: boolean; lastAt: string | null }[];
  riskHistory: { timestamp: string; risk: number }[];
  incidents: Incident[];
  grants: { active: number; expired: number; revoked: number; unusedStanding: string[] } | null;
  findings: Finding[];
  hypothesis: Hypothesis;
  summary: { text: string; source: "gemini" | "fallback"; model: string | null; generatedAt: string } | null;
}

// --- simulator control API (port 8001) ---
export interface ScenarioInfo {
  id: string;
  title: string;
  description: string;
  loop: boolean;
  steps: number;
}

export interface RunState {
  id: string;
  scenarioId: string;
  title: string;
  status: "running" | "passed" | "failed" | "done" | "stopped" | "error";
  stepIndex: number;
  totalSteps: number;
  caption: string | null;
  error: string | null;
}
