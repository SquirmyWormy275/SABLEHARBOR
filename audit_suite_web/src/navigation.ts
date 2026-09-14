import type { Bootstrap, Engagement } from "./api";
export const workspaceSections = [
  "kickoff",
  "controls",
  "pbc",
  "meetings",
  "people",
  "populations",
  "notes",
  "calendar",
  "findings",
  "review",
] as const;
export type WorkspaceSection = (typeof workspaceSections)[number];
const objectSections = {
  controls: "controls",
  requests: "pbc",
  artifacts: "pbc",
  meetings: "meetings",
  people: "people",
  populations: "populations",
  selections: "populations",
  notes: "notes",
  calendar: "calendar",
  findings: "findings",
  workpapers: "review",
  reviews: "review",
} as const;
export type WorkspaceLocation = {
  engagement: string;
  section: WorkspaceSection;
  object?: { kind: keyof typeof objectSections; id: string };
};
export type LinkResolution =
  | { status: "ready"; location: WorkspaceLocation }
  | { status: "unavailable" | "engagements" };
/** Only call with the engagement returned by an authorized API fetch. Unknown/denied objects share one response. */
export function parseWorkspaceLink(
  search: string,
  e: Engagement | null,
): LinkResolution {
  const p = new URLSearchParams(search),
    unavailable: LinkResolution = { status: "unavailable" };
  for (const key of ["engagement", "view", "kind", "object"])
    if (p.getAll(key).length > 1) return unavailable;
  const id = p.get("engagement");
  if (!id)
    return p.has("kind") || p.has("object")
      ? unavailable
      : { status: "engagements" };
  if (!e || e.id !== id) return unavailable;
  const section = p.get("view") ?? "kickoff";
  if (!workspaceSections.includes(section as WorkspaceSection))
    return unavailable;
  const location: WorkspaceLocation = {
    engagement: id,
    section: section as WorkspaceSection,
  };
  const kind = p.get("kind"),
    object = p.get("object");
  if (kind !== null || object !== null) {
    if (!kind || !object || !Object.hasOwn(objectSections, kind))
      return unavailable;
    const k = kind as keyof typeof objectSections;
    if (
      objectSections[k] !== section ||
      e[k].filter((r) => r.id === object).length !== 1
    )
      return unavailable;
    location.object = { kind: k, id: object };
  }
  return { status: "ready", location };
}
/** Relative URL; never encode list queries, drafts or record contents. */
export function workspaceLink(location: WorkspaceLocation) {
  const p = new URLSearchParams({
    engagement: location.engagement,
    view: location.section,
  });
  if (location.object) {
    p.set("kind", location.object.kind);
    p.set("object", location.object.id);
  }
  return `?${p}`;
}
export function orientation(e: Engagement, v: Bootstrap["viewer"]) {
  return {
    engagementId: e.id,
    title: e.title,
    boundaries: [...e.scope.boundaries],
    periodStart: e.scope.period_start,
    periodEnd: e.scope.period_end,
    reportType: e.scope.report_type,
    simulatedAt: e.simulated_at,
    viewerName: v.display_name,
    roles: [...v.roles],
    permissions: [...(e.permissions ?? [])],
  };
}
export type ListContext = {
  query: string;
  framework: string;
  scrollTop: number;
};
const empty = (): ListContext => ({
  query: "",
  framework: "all",
  scrollTop: 0,
});
/** In-memory only. Activate after every authorized refresh; clear on logout/access failure.
 * Scope/role/permission switches discard context. No records, drafts or instructor inputs stored.
 */
export function createNavigationMemory() {
  let identity = "";
  const views = new Map<WorkspaceSection, ListContext>();
  return {
    activate(e: Engagement, v: Bootstrap["viewer"]) {
      const next = JSON.stringify([
        v.id,
        [...v.roles].sort(),
        e.id,
        [...(e.permissions ?? [])].sort(),
        e.scope,
      ]);
      if (next !== identity) {
        views.clear();
        identity = next;
      }
    },
    save(section: WorkspaceSection, c: ListContext) {
      if (identity)
        views.set(section, {
          query: c.query.slice(0, 1000),
          framework: c.framework.slice(0, 200),
          scrollTop: Number.isFinite(c.scrollTop)
            ? Math.max(0, c.scrollTop)
            : 0,
        });
    },
    restore(section: WorkspaceSection): ListContext {
      return { ...(views.get(section) ?? empty()) };
    },
    clear() {
      identity = "";
      views.clear();
    },
  };
}
