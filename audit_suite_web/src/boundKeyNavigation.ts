import type { Row } from "./api";
import type {
  BoundIssue,
  BoundSnapshot,
  BoundSource,
} from "./boundInstructorKey";
export const BOUND_SOURCE_PAGE_SIZE = 10;
export function issueControlLabel(issue: BoundIssue, controls: Row[]): string {
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
  },
) {
  const issue = snapshot.authored.issues.find(
    (row) => row.id === options.issueId,
  );
  const scope = issue
    ? snapshot.sources.filter((row) => issue.source_ids.includes(row.id))
    : snapshot.sources;
  const q = options.query.trim().toLowerCase();
  const filtered = scope.filter((row) =>
    [
      row.id,
      row.company,
      row.branch,
      row.system,
      row.record,
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
