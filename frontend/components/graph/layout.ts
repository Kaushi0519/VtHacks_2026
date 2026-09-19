// Fixed, hand-tuned mesh layout: unverified callers | agents | resources, left to right.
// Vertical steps are deliberately tight: the mesh is fitted to its panel, and height is the binding
// dimension (width has slack), so every row of slack costs node size on screen — most visibly with
// the inspector open. Agent nodes are ~72px tall and resource nodes ~36px, so these keep real gaps.
// Agents are ordered so every peer pair sits next to each other; resources so access edges barely cross.
// Unknown ids (new agents/resources in world.yaml) are appended below instead of breaking the layout.

export const COLUMN_X = { ghost: 0, agent: 260, resource: 600 } as const;
export const HEADER_Y = -48;

const AGENT_ORDER = ["facilities-agent", "scheduling-agent", "payroll-agent", "analytics-agent", "database-agent"];
const RESOURCE_ORDER = [
  "building-mgmt",
  "scheduling-system",
  "hr-directory",
  "payroll-system",
  "analytics-warehouse",
  "ehr",
  "credential-vault",
];

const AGENT_STEP = 100;
const RESOURCE_STEP = 68;
const GHOST_STEP = 96;

function slot(order: string[], id: string, seen: string[]): number {
  const i = order.indexOf(id);
  return i >= 0 ? i : order.length + seen.filter((s) => !order.includes(s)).indexOf(id);
}

export const agentPosition = (id: string, all: string[]) => ({ x: COLUMN_X.agent, y: slot(AGENT_ORDER, id, all) * AGENT_STEP });
export const resourcePosition = (id: string, all: string[]) => ({ x: COLUMN_X.resource, y: slot(RESOURCE_ORDER, id, all) * RESOURCE_STEP });
export const ghostPosition = (index: number) => ({ x: COLUMN_X.ghost, y: 40 + index * GHOST_STEP });

// Hex mirrors of the theme tokens in app/globals.css (SVG strokes can't use Tailwind classes).
export const INK = {
  line: "#1c2a3d",
  edge: "#2a3b52",
  dim: "#7b8aa2",
  accent: "#22d3ee",
  ok: "#34d399",
  warn: "#fbbf24",
  crit: "#f43f5e",
  quarantine: "#e879f9",
} as const;
