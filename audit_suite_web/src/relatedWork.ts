import type { Engagement, Row } from "./api";
import { record } from "./workpaperSupport";

const kinds = {
  controls: "control",
  tasks: "task",
  requests: "request",
  artifacts: "artifact",
  populations: "population",
  notes: "note",
  findings: "finding",
  workpapers: "workpaper",
} as const;
export type RelatedWorkReference = {
  collection: keyof typeof kinds;
  id: string;
  version?: number;
};
export type RelatedWorkLink = {
  reference: RelatedWorkReference;
  title: string;
  reason: string;
};
export type RelatedWorkGroup = {
  id: string;
  title: string;
  links: RelatedWorkLink[];
};
const unique = (rows: Row[], id: string) => {
  const matches = rows.filter((row) => row.id === id);
  return matches.length === 1 ? matches[0] : undefined;
};
function inScope(e: Engagement, row: Row) {
  return (
    (!row.boundary_id ||
      e.scope.boundaries.includes(String(row.boundary_id))) &&
    row.applicability !== "PRIOR_SCOPE_REQUIRES_REASSESSMENT" &&
    row.applicability !== "EXCLUDED" &&
    row.status !== "EXCLUDED"
  );
}
function title(row: Row) {
  const value = row.title ?? row.name ?? row.filename ?? row.id;
  return typeof value === "string" ? value.slice(0, 180) : row.id;
}
/** Resolve only current authorized rows; duplicate identities/versions are unavailable. */
export function resolveRelatedWork(e: Engagement, ref: RelatedWorkReference) {
  if (!Object.hasOwn(kinds, ref.collection)) return null;
  const row = unique(e[ref.collection], ref.id);
  if (!row || !inScope(e, row)) return null;
  if (ref.collection === "artifacts" && row.status !== "AVAILABLE") return null;
  if (ref.collection === "workpapers") {
    if (
      !Number.isInteger(ref.version) ||
      typeof ref.version !== "number" ||
      ref.version < 1 ||
      !Array.isArray(row.versions) ||
      row.versions.filter((v) => record(v).version === ref.version).length !== 1
    )
      return null;
  } else if (ref.version !== undefined && ref.version !== row.version)
    return null;
  return { kind: kinds[ref.collection], row };
}

/** Explicit links in the authorized engagement projection only. No name matching,
 * private Key, event/history traversal, source collection, conclusions or task credit.
 * Shared control context is deliberately distinct from exact procedure-version links.
 */
export function relatedWork(
  e: Engagement,
  kind: "control" | "task",
  id: string,
) {
  const anchor = unique(kind === "task" ? e.tasks : e.controls, id);
  if (!anchor || !inScope(e, anchor)) return null;
  const controlId = kind === "control" ? id : anchor.control_id;
  const control =
    typeof controlId === "string" ? unique(e.controls, controlId) : undefined;
  const scopedControl = control && inScope(e, control) ? control : undefined;
  const groups: RelatedWorkGroup[] = [];
  const add = (
    groupId: string,
    groupTitle: string,
    links: RelatedWorkLink[],
  ) => {
    groups.push({ id: groupId, title: groupTitle, links });
  };
  const link = (
    collection: RelatedWorkReference["collection"],
    row: Row,
    reason: string,
  ): RelatedWorkLink => ({
    reference: {
      collection,
      id: row.id,
      ...(typeof row.version === "number" ? { version: row.version } : {}),
    },
    title: title(row),
    reason,
  });
  const rowsForControl = (collection: RelatedWorkReference["collection"]) =>
    scopedControl
      ? e[collection].filter(
          (row) =>
            row.control_id === scopedControl.id &&
            inScope(e, row) &&
            !!unique(e[collection], row.id),
        )
      : [];
  if (kind === "task") {
    add(
      "control",
      "Recorded control",
      scopedControl
        ? [
            link(
              "controls",
              scopedControl,
              `Procedure ${id} explicitly records this control.`,
            ),
          ]
        : [],
    );
  } else {
    add(
      "procedures",
      "Scoped procedures",
      rowsForControl("tasks").map((row) =>
        link("tasks", row, `Procedure records control ${id}.`),
      ),
    );
  }
  const requests = rowsForControl("requests");
  const requestIds = new Set(requests.map((row) => row.id));
  if (scopedControl) {
    add(
      "requests",
      "Evidence requests",
      requests.map((row) =>
        link(
          "requests",
          row,
          `Request records control ${scopedControl.id}; procedure support has not been inferred.`,
        ),
      ),
    );
    add(
      "artifacts",
      "Retained evidence files",
      e.artifacts
        .filter(
          (row) =>
            row.status === "AVAILABLE" &&
            inScope(e, row) &&
            !!unique(e.artifacts, row.id) &&
            (row.control_id === scopedControl.id ||
              requestIds.has(String(row.request_id))),
        )
        .map((row) =>
          link(
            "artifacts",
            row,
            row.control_id === scopedControl.id
              ? `File records control ${scopedControl.id}; relevance does not establish testing.`
              : `Received for request ${String(row.request_id)}, which records control ${scopedControl.id}.`,
          ),
        ),
    );
    add(
      "populations",
      "Declared populations",
      rowsForControl("populations").map((row) =>
        link(
          "populations",
          row,
          `Population records control ${scopedControl.id}; completeness and acceptance remain separate.`,
        ),
      ),
    );
  }
  const taskIds = new Set(
    kind === "task" ? [id] : rowsForControl("tasks").map((row) => row.id),
  );
  const paperLinks: RelatedWorkLink[] = [];
  for (const paper of e.workpapers) {
    if (
      !unique(e.workpapers, paper.id) ||
      !inScope(e, paper) ||
      !Array.isArray(paper.versions)
    )
      continue;
    for (const raw of paper.versions) {
      const v = record(raw);
      if (
        typeof v.version !== "number" ||
        !Number.isInteger(v.version) ||
        v.version < 1 ||
        paper.versions.filter((x) => record(x).version === v.version).length !==
          1
      )
        continue;
      const explicitTasks = Array.isArray(v.task_ids)
        ? v.task_ids.filter(
            (value): value is string =>
              typeof value === "string" && taskIds.has(value),
          )
        : [];
      if (!explicitTasks.length) continue;
      paperLinks.push({
        reference: {
          collection: "workpapers",
          id: paper.id,
          version: v.version,
        },
        title: title(paper),
        reason: `This exact version explicitly records ${[...new Set(explicitTasks)].join(", ")}. A recorded link does not establish adequate testing.`,
      });
    }
  }
  add("workpapers", "Exact procedure-linked workpaper versions", paperLinks);
  if (scopedControl) {
    add(
      "notes",
      "Linked notes",
      rowsForControl("notes").map((row) =>
        link(
          "notes",
          row,
          `Note records control ${scopedControl.id}; statements remain attributed.`,
        ),
      ),
    );
    add(
      "findings",
      "Recorded findings",
      rowsForControl("findings").map((row) =>
        link(
          "findings",
          row,
          `Finding records control ${scopedControl.id}; its recorded status does not close this procedure.`,
        ),
      ),
    );
  }
  return { anchor, kind, groups, controlId: scopedControl?.id ?? null };
}
