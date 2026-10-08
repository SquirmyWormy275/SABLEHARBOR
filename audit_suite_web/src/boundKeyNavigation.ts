import type { Row } from "./api";
import type {
  BoundIssue,
  BoundSnapshot,
  BoundSource,
} from "./boundInstructorKey";
import { authoredRelationships } from "./boundInstructorKey";
export const BOUND_SOURCE_PAGE_SIZE = 10;
export const BOUND_ISSUE_PAGE_SIZE = 20;
export type BoundIssueIndex = {
  query: string;
  control_id: string | null;
  page: number;
};
export const defaultIssueIndex = (): BoundIssueIndex => ({
  query: "",
  control_id: null,
  page: 0,
});
export function boundIssuePage(
  snapshot: BoundSnapshot,
  options: BoundIssueIndex,
) {
  const q = options.query.trim().toLowerCase();
  const filtered = snapshot.authored.issues.filter(
    (row) =>
      (options.control_id === null ||
        row.control_ids.includes(options.control_id)) &&
      [
        row.id,
        ...row.control_ids,
        row.claim,
        row.uncertainty,
        ...selectedIssueExpectations(snapshot, row.id).flatMap((e) => [
          e.id,
          ...(e.task_ids ?? []),
          e.procedure,
          ...e.acceptable_alternatives,
        ]),
        ...snapshot.sources
          .filter((s) => row.source_ids.includes(s.id))
          .flatMap((s) => [
            s.id,
            s.company,
            s.branch,
            s.system,
            s.record,
            String(s.version),
            s.sha256,
          ]),
      ]
        .join(" ")
        .toLowerCase()
        .includes(q),
  );
  const pages = Math.max(1, Math.ceil(filtered.length / BOUND_ISSUE_PAGE_SIZE));
  const page = Math.min(
    Math.max(0, Number.isInteger(options.page) ? options.page : 0),
    pages - 1,
  );
  return {
    filtered,
    rows: filtered.slice(
      page * BOUND_ISSUE_PAGE_SIZE,
      (page + 1) * BOUND_ISSUE_PAGE_SIZE,
    ),
    controls: [
      ...new Set(snapshot.authored.issues.flatMap((row) => row.control_ids)),
    ].sort(),
    page,
    pages,
    total: snapshot.authored.issues.length,
  };
}
export function issueControlLabel(issue: BoundIssue, controls: Row[]): string {
  if (issue.control_ids.length === 0) return "Engagement scope";
  return issue.control_ids
    .map((id) => {
      const control = controls.find((row) => row.id === id);
      const title = control?.title ?? control?.name;
      return typeof title === "string" && title.trim()
        ? `${id} · ${title}`
        : id;
    })
    .join("; ");
}
export function boundSourcePage(
  snapshot: BoundSnapshot,
  options: {
    issueId: string;
    query: string;
    page: number;
    sourceFilters?: BoundSourceFilters;
  },
) {
  const issue = snapshot.authored.issues.find(
    (row) => row.id === options.issueId,
  );
  const scope = issue
    ? snapshot.sources.filter((row) => issue.source_ids.includes(row.id))
    : snapshot.sources;
  const q = options.query.trim().toLowerCase();
  const filtered = scope.filter(
    (row) =>
      (!options.sourceFilters?.system ||
        row.system === options.sourceFilters.system) &&
      (!options.sourceFilters?.visibility ||
        row.actor_visibility_at_binding === options.sourceFilters.visibility) &&
      [
        row.id,
        row.company,
        row.branch,
        row.system,
        row.record,
        String(row.version),
        row.sha256,
        row.source_store_id,
        row.source_system_alias,
        row.registry_sha256,
        row.actor_visibility_at_binding,
      ]
        .join(" ")
        .toLowerCase()
        .includes(q),
  );
  const pages = Math.max(
    1,
    Math.ceil(filtered.length / BOUND_SOURCE_PAGE_SIZE),
  );
  const page = Math.min(
    Math.max(0, Number.isInteger(options.page) ? options.page : 0),
    pages - 1,
  );
  return {
    rows: filtered.slice(
      page * BOUND_SOURCE_PAGE_SIZE,
      (page + 1) * BOUND_SOURCE_PAGE_SIZE,
    ),
    filtered,
    scopeCount: scope.length,
    page,
    pages,
    total: snapshot.sources.length,
  };
}
export type BoundSourceFilters = {
  system: string | null;
  visibility: string | null;
};
export const defaultSourceFilters = (): BoundSourceFilters => ({
  system: null,
  visibility: null,
});
/** Only explicitly authored endpoints, bounded and synchronized to literal selection. */
export function boundRelationshipPage(
  snapshot: BoundSnapshot,
  issue: string,
  source: string,
  page: number,
  expectation = "",
) {
  const edges = authoredRelationships(snapshot);
  const filtered =
    issue || source || expectation
      ? edges.filter(
          (edge) =>
            edge.from === issue ||
            edge.to === issue ||
            edge.from === source ||
            edge.to === source ||
            edge.from === expectation ||
            edge.to === expectation,
        )
      : edges;
  const pages = Math.max(1, Math.ceil(filtered.length / 20));
  const selectedPage = Math.min(
    Math.max(0, Number.isInteger(page) ? page : 0),
    pages - 1,
  );
  return {
    rows: filtered.slice(selectedPage * 20, (selectedPage + 1) * 20),
    total: edges.length,
    filtered: filtered.length,
    page: selectedPage,
    pages,
  };
}
export function selectedIssueExpectations(
  snapshot: BoundSnapshot,
  issueId: string,
) {
  return snapshot.authored.expectations.filter((row) =>
    row.issue_ids.includes(issueId),
  );
}
export function scopedTimelineSources(
  selected: BoundSource | undefined,
  page: BoundSource[],
) {
  return selected ? [selected] : page;
}
