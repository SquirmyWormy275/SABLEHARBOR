import type { Engagement, Row } from "./api";
import type { WorkspaceSection } from "./navigation";
export const searchKinds = {
  control: {
    collection: "controls",
    label: "Controls",
    section: "controls",
    fields: ["title", "description", "control_id"],
  },
  request: {
    collection: "requests",
    label: "Evidence requests",
    section: "pbc",
    fields: ["title", "purpose", "status", "control_id"],
  },
  artifact: {
    collection: "artifacts",
    label: "Evidence files",
    section: "pbc",
    fields: ["title", "name", "filename", "request_id", "control_id"],
  },
  workpaper: {
    collection: "workpapers",
    label: "Workpapers",
    section: "review",
    fields: ["title", "objective", "control_id", "status"],
  },
  finding: {
    collection: "findings",
    label: "Findings",
    section: "findings",
    fields: ["title", "condition", "description", "control_id", "status"],
  },
  person: {
    collection: "people",
    label: "People",
    section: "people",
    fields: ["name", "display_name", "role_title", "role_id"],
  },
  population: {
    collection: "populations",
    label: "Populations",
    section: "populations",
    fields: ["title", "control_id", "status", "boundary_id"],
  },
  task: {
    collection: "tasks",
    label: "Procedures and tasks",
    section: "controls",
    fields: ["title", "objective", "procedure", "control_id", "status"],
  },
  note: {
    collection: "notes",
    label: "Notes",
    section: "notes",
    fields: ["title", "text", "control_id"],
  },
} as const;
export type SearchKind = keyof typeof searchKinds;
export type SearchHit = {
  kind: SearchKind;
  id: string;
  title: string;
  snippet: string;
  section: WorkspaceSection;
};
export type SearchGroup = {
  kind: SearchKind;
  label: string;
  total: number;
  hits: SearchHit[];
};
const scalar = (v: unknown) =>
  typeof v === "string" || typeof v === "number" ? String(v) : "";
const excerpt = (text: string, q: string) => {
  const collapsed = text.replace(/\s+/g, " ").trim(),
    found = collapsed.toLocaleLowerCase().indexOf(q);
  const start = Math.max(0, found - 55);
  return (
    (start ? "…" : "") +
    collapsed.slice(start, start + 210) +
    (collapsed.length > start + 210 ? "…" : "")
  );
};
/** Searches explicit public fields in an already authorized engagement only.
 * Never traverse objects, recipes, versions, events, rubric, private key or arbitrary metadata.
 */
export function searchWorkspace(
  e: Engagement,
  query: string,
  kind: SearchKind | "all" = "all",
): SearchGroup[] {
  const q = query.trim().slice(0, 200).toLocaleLowerCase();
  if (!q) return [];
  const groups: SearchGroup[] = [];
  for (const [name, spec] of Object.entries(searchKinds)) {
    const k = name as SearchKind;
    if (kind !== "all" && kind !== k) continue;
    const rows = e[spec.collection];
    const counts = new Map<string, number>();
    for (const row of rows) counts.set(row.id, (counts.get(row.id) ?? 0) + 1);
    const hits: SearchHit[] = [];
    let total = 0;
    for (const row of rows) {
      if (counts.get(row.id) !== 1) continue;
      const values = [
        row.id,
        ...spec.fields.map((field) => scalar(row[field])),
      ];
      const matching = values.find((value) =>
        value.toLocaleLowerCase().includes(q),
      );
      if (!matching) continue;
      ++total;
      if (hits.length >= 25) continue;
      const title =
        scalar(row.title) ||
        scalar(row.name) ||
        scalar(row.display_name) ||
        scalar(row.filename) ||
        row.id;
      hits.push({
        kind: k,
        id: row.id,
        title: title.slice(0, 180),
        snippet: excerpt(matching, q),
        section: spec.section,
      });
    }
    if (total) groups.push({ kind: k, label: spec.label, total, hits });
  }
  return groups;
}
/** Resolve again at click time so stale results cannot preview removed or ambiguous rows. */
export function resolveSearchHit(e: Engagement, hit: SearchHit): Row | null {
  const spec = searchKinds[hit.kind];
  if (!spec) return null;
  const matches = e[spec.collection].filter((row) => row.id === hit.id);
  return matches.length === 1 ? matches[0] : null;
}
export function searchContext(e: Engagement, viewerId: string) {
  return JSON.stringify([
    viewerId,
    e.id,
    e.scope,
    [...(e.permissions ?? [])].sort(),
    e.company_source_binding,
    e.evidence_acquisition,
  ]);
}
