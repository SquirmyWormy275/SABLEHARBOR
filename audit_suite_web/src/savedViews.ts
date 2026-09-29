import type { Engagement, Row } from "./api";
import {
  investigationKinds,
  type ContextLink,
  type InvestigationKind,
} from "./investigationContext";
import type { TableState } from "./tableMemory";
export type SavedViewReferenceDescriptor = {
  kind: InvestigationKind;
  id: string;
  version: number | null;
};
export type SavedViewNavigation = {
  section: string;
  query: string;
  framework: string;
  scroll_top: number;
  reference: ContextLink | null;
  table: (TableState & { id: string }) | null;
};
export type SavedView = {
  id: string;
  engagement_id: string;
  version: number;
  status: string;
  current_engagement_revision: number;
  engagement_revision: number;
  context_status: string;
  revision_status: string;
  personal_content_visible: boolean;
  restorable: boolean;
  target_status?: string;
  saved_at: string;
  user?: SavedViewNavigation & { title: string };
  navigation: SavedViewNavigation | null;
};
export const savedViewTables: Record<string, readonly string[]> = {
  controls: ["procedures", "controls"],
  pbc: ["requests", "artifacts"],
  people: ["people"],
  populations: ["populations", "selections"],
  calendar: ["events", "calendar"],
  findings: ["findings"],
  review: ["workpapers", "reviews", "exports"],
};
export const referenceSections: Record<InvestigationKind, string> = {
  control: "controls",
  task: "controls",
  artifact: "pbc",
  population: "populations",
  selection: "populations",
  workpaper: "review",
};
export const savedViewsPath = (eid: string) =>
  `/api/engagements/${encodeURIComponent(eid)}/saved-views`;
export function savedViewContext(e: Engagement, viewerId: string) {
  return JSON.stringify([
    viewerId,
    e.id,
    e.revision,
    e.scope,
    e.permissions,
    e.company_source_binding,
    e.evidence_acquisition,
  ]);
}
export function currentViewResponse(
  view: SavedView,
  e: Engagement,
  expectedId?: string,
) {
  return (
    !!view &&
    view.engagement_id === e.id &&
    view.current_engagement_revision === e.revision &&
    (!expectedId || view.id === expectedId) &&
    Number.isSafeInteger(view.version) &&
    view.version > 0
  );
}
export function exactReferenceDescriptor(
  ref: ContextLink,
  descriptor: SavedViewReferenceDescriptor,
) {
  return (
    ref.kind === descriptor.kind &&
    ref.id === descriptor.id &&
    ref.version === descriptor.version &&
    /^[a-f0-9]{64}$/.test(ref.sha256)
  );
}
/** Server verifies the digest; local resolution only selects the exact currently authorized row/version. */
export function resolveSavedViewReference(
  e: Engagement,
  ref: ContextLink,
): Row | null {
  const collection = investigationKinds[ref.kind];
  if (!collection || !/^[a-f0-9]{64}$/.test(ref.sha256)) return null;
  const matches = e[collection].filter((row) => row.id === ref.id);
  if (matches.length !== 1) return null;
  const row = matches[0];
  if (ref.kind === "workpaper") {
    const versions = Array.isArray(row.versions) ? (row.versions as Row[]) : [];
    if (
      !Number.isSafeInteger(ref.version) ||
      versions.filter((v) => v.version === ref.version).length !== 1
    )
      return null;
  } else if (
    (typeof row.version === "number" ? row.version : null) !== ref.version
  )
    return null;
  if (ref.kind === "artifact" && row.status !== "AVAILABLE") return null;
  if (
    ref.kind === "task" &&
    ["EXCLUDED", "NOT_APPLICABLE"].includes(String(row.status))
  )
    return null;
  return row;
}
export function restoredNavigation(
  view: SavedView,
  e: Engagement,
  expectedId: string,
  expectedVersion: number,
) {
  if (
    !currentViewResponse(view, e, expectedId) ||
    view.version !== expectedVersion ||
    view.status !== "ACTIVE" ||
    view.context_status !== "CURRENT" ||
    !view.personal_content_visible ||
    !view.restorable ||
    !view.navigation
  )
    throw new Error(
      "Saved view changed or is unavailable. Refresh the list before restoring.",
    );
  const nav = view.navigation;
  if (nav.table && !savedViewTables[nav.section]?.includes(nav.table.id))
    throw new Error("Saved table does not belong to this section.");
  const row = nav.reference
    ? resolveSavedViewReference(e, nav.reference)
    : null;
  if (
    nav.reference &&
    (referenceSections[nav.reference.kind] !== nav.section || !row)
  )
    throw new Error("Exact saved record is unavailable in this workspace.");
  return { navigation: nav, row };
}

export const savedViewSectionLabels: Record<string, string> = {
  kickoff: "Kickoff & scope",
  controls: "Controls & tracker",
  pbc: "PBC & evidence",
  meetings: "Meetings · MRL",
  people: "People",
  populations: "Populations & samples",
  notes: "Notes",
  calendar: "Calendar & timeline",
  findings: "Exceptions & remediation",
  review: "Workpapers & review",
};
export const savedViewTableLabels: Record<string, string> = {
  procedures: "Procedures",
  controls: "Controls",
  requests: "Evidence requests",
  artifacts: "Evidence originals",
  people: "People",
  populations: "Populations",
  selections: "Sample selections",
  calendar: "Calendar",
  events: "Audit events",
  findings: "Findings",
  workpapers: "Workpapers",
  reviews: "Review comments",
  exports: "Exports",
};
