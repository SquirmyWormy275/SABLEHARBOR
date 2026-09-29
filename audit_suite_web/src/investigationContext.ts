import type { Engagement, Row } from "./api";
export const investigationKinds = {
  control: "controls",
  task: "tasks",
  artifact: "artifacts",
  population: "populations",
  selection: "selections",
  workpaper: "workpapers",
} as const;
export type InvestigationKind = keyof typeof investigationKinds;
export type ContextLink = {
  kind: InvestigationKind;
  id: string;
  version: number | null;
  sha256: string;
};
export type SavedInvestigation = {
  id: string;
  version: number;
  status: string;
  user: {
    title: string;
    question: string;
    next_step: string;
    links: ContextLink[];
  };
  scope_status: string;
  context_status?: "CURRENT" | "CONTEXT_CHANGED" | "BASIS_UNRECORDED";
  engagement_revision: number;
  link_status: { reference: ContextLink; status: string }[];
};
export const contextsPath = (id: string) =>
  `/api/engagements/${encodeURIComponent(id)}/contexts`;
export function resolveContextLink(
  e: Engagement,
  link: ContextLink,
  status: string,
): Row | null {
  if (!["EXACT_PIN_AVAILABLE", "HISTORICAL_VERSION_AVAILABLE"].includes(status))
    return null;
  const rows = e[investigationKinds[link.kind]];
  const matches = rows.filter((r) => r.id === link.id);
  return matches.length === 1 ? matches[0] : null;
}
export function selectedVersion(
  kind: InvestigationKind,
  row: Row,
): number | null {
  if (kind === "workpaper") {
    const versions = Array.isArray(row.versions) ? (row.versions as Row[]) : [];
    const value = versions.at(-1)?.version;
    return typeof value === "number" ? value : null;
  }
  return typeof row.version === "number" ? row.version : null;
}

export function contextAllowsOpen(
  context: Pick<SavedInvestigation, "scope_status" | "context_status">,
): boolean {
  return (
    context.scope_status === "CURRENT" && context.context_status === "CURRENT"
  );
}
