import type { Engagement } from "./api";
import type { BoundSnapshot } from "./boundInstructorKey";
import {
  boundIssuePage,
  boundSourcePage,
  type BoundIssueIndex,
  type BoundSourceFilters,
} from "./boundKeyNavigation";
import {
  filterKeys,
  keyOption,
  keySelector,
  type InstructorIndex,
} from "./instructorKey";
export type BoundKeyFilters = {
  query: string;
  issue_id: string | null;
  scope_to_issue: boolean;
  source: null | { id: string; version: number; sha256: string };
  page: number;
  issue_index?: BoundIssueIndex;
  source_filters?: BoundSourceFilters;
};
export type ArchiveKeyFilters = {
  query: string;
  selector: string;
  option: string;
  review: string;
  scenario: null | { id: string; key_sha256: string };
  page: number;
  review_facets?: { causal_validation: string | null; grading: string | null };
};
export type KeyViewFilters = BoundKeyFilters | ArchiveKeyFilters;
export type KeyViewKind = "BOUND" | "ARCHIVE";
export const isBoundFilters = (v: KeyViewFilters): v is BoundKeyFilters =>
  "scope_to_issue" in v;
export function keyViewContext(
  e: Engagement,
  actor: string,
  kind: KeyViewKind,
  pin: string,
) {
  return JSON.stringify([
    actor,
    e.id,
    e.revision,
    e.permissions,
    e.scope,
    e.company_source_binding,
    e.evidence_acquisition,
    kind,
    pin,
  ]);
}
function exactFields(value: unknown, fields: string[]) {
  return (
    !!value &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.keys(value).length === fields.length &&
    fields.every((k) => Object.prototype.hasOwnProperty.call(value, k))
  );
}
export function validateBoundFilters(v: BoundKeyFilters, s: BoundSnapshot) {
  if (
    !exactFields(v, [
      "query",
      "issue_id",
      "scope_to_issue",
      "source",
      "page",
      ...(Object.prototype.hasOwnProperty.call(v ?? {}, "issue_index")
        ? ["issue_index"]
        : []),
      ...(Object.prototype.hasOwnProperty.call(v ?? {}, "source_filters")
        ? ["source_filters"]
        : []),
    ]) ||
    (v.source !== null && !exactFields(v.source, ["id", "version", "sha256"]))
  )
    throw Error("Exact bound filter fields required.");
  if (
    typeof v.query !== "string" ||
    v.query.length > 1000 ||
    typeof v.scope_to_issue !== "boolean" ||
    !Number.isSafeInteger(v.page) ||
    v.page < 0 ||
    (v.issue_id !== null &&
      s.authored.issues.filter((i) => i.id === v.issue_id).length !== 1) ||
    (v.scope_to_issue && !v.issue_id)
  )
    throw Error("Saved bound Key filters no longer match this exact snapshot.");
  if (
    v.source &&
    s.sources.filter(
      (r) =>
        r.id === v.source!.id &&
        r.version === v.source!.version &&
        r.sha256 === v.source!.sha256,
    ).length !== 1
  )
    throw Error(
      "Saved original pin is unavailable; no version was substituted.",
    );
  if (
    v.source_filters &&
    (!exactFields(v.source_filters, ["system", "visibility"]) ||
      Object.entries(v.source_filters).some(
        ([key, value]) =>
          value !== null &&
          (typeof value !== "string" ||
            !s.sources.some(
              (r) =>
                (key === "system"
                  ? r.system
                  : r.actor_visibility_at_binding) === value,
            )),
      ))
  )
    throw Error("Saved source facets are unavailable in this exact snapshot.");
  if (Object.hasOwn(v, "source_filters") && !v.source_filters)
    throw Error("Exact source facet fields required.");
  const result = boundSourcePage(s, {
    query: v.query,
    issueId: v.scope_to_issue ? (v.issue_id ?? "") : "",
    page: v.page,
    sourceFilters: v.source_filters,
  });
  if (result.page !== v.page)
    throw Error("Saved source page is outside this exact filter result.");
  if (Object.prototype.hasOwnProperty.call(v, "issue_index")) {
    const index = v.issue_index;
    if (
      !exactFields(index, ["query", "control_id", "page"]) ||
      typeof index?.query !== "string" ||
      index.query.length > 1000 ||
      !Number.isSafeInteger(index.page) ||
      index.page < 0 ||
      (index.control_id !== null &&
        (typeof index.control_id !== "string" ||
          !s.authored.issues.some((issue) =>
            issue.control_ids.includes(index.control_id!),
          )))
    )
      throw Error("Exact saved issue-index filters required.");
    if (boundIssuePage(s, index).page !== index.page)
      throw Error("Saved issue page is outside this exact filter result.");
  }
  return structuredClone(v);
}
export function validateArchiveFilters(
  v: ArchiveKeyFilters,
  index: InstructorIndex,
  completeMatchIds?: string[],
  pendingRestoredQuery = false,
) {
  if (
    !exactFields(v, [
      "query",
      "selector",
      "option",
      "review",
      "scenario",
      "page",
      ...(Object.hasOwn(v ?? {}, "review_facets") ? ["review_facets"] : []),
    ]) ||
    (v.scenario !== null && !exactFields(v.scenario, ["id", "key_sha256"]))
  )
    throw Error("Exact archive filter fields required.");
  if (
    typeof v.query !== "string" ||
    v.query.length > 1000 ||
    !Number.isSafeInteger(v.page) ||
    v.page < 0 ||
    !["all", ...index.entries.map((x) => keySelector(x.id))].includes(
      v.selector,
    ) ||
    ![
      "all",
      ...index.entries
        .filter((x) => v.selector === "all" || keySelector(x.id) === v.selector)
        .map((x) => keyOption(x.id)),
    ].includes(v.option) ||
    !["all", ...index.entries.map((x) => x.review.professional)].includes(
      v.review,
    )
  )
    throw Error("Saved archive filters no longer match this exact archive.");
  if (
    Object.hasOwn(v, "review_facets") &&
    (!exactFields(v.review_facets, ["causal_validation", "grading"]) ||
      Object.entries(v.review_facets ?? {}).some(
        ([key, value]) =>
          value !== null &&
          (typeof value !== "string" ||
            !index.entries.some(
              (row) =>
                row.review[key as "causal_validation" | "grading"] === value,
            )),
      ))
  )
    throw Error("Saved review facets are unavailable in this exact archive.");
  if (
    v.scenario &&
    index.entries.filter(
      (x) => x.id === v.scenario!.id && x.key_sha256 === v.scenario!.key_sha256,
    ).length !== 1
  )
    throw Error(
      "Saved scenario pin is unavailable; no scenario was substituted.",
    );
  if (
    index.semantic_matching &&
    v.query.trim() &&
    completeMatchIds === undefined &&
    !pendingRestoredQuery
  )
    throw Error(
      "Wait for complete authored search matching before saving this view.",
    );
  // A server-validated restored query may be pending. Bound its page by the full
  // archive now; the exact matching receipt validates it again before rendering.
  const rows = pendingRestoredQuery
    ? index.entries
    : filterKeys(index.entries, { ...v, complete_match_ids: completeMatchIds });
  if (v.page >= Math.max(1, Math.ceil(rows.length / 25)))
    throw Error("Saved archive page is outside this exact filter result.");
  return structuredClone(v);
}
export type SavedKeyView = {
  id: string;
  engagement_id: string;
  kind: KeyViewKind;
  version: number;
  status: "ACTIVE" | "DELETED";
  saved_engagement_revision: number;
  current_engagement_revision: number;
  context_status:
    "CURRENT" | "CONTEXT_CHANGED" | "KEY_CHANGED" | "KEY_UNAVAILABLE";
  revision_status: "MATCHING_REVISION" | "ENGAGEMENT_ADVANCED";
  restorable: boolean;
  personal_content_visible: boolean;
  navigation: (KeyViewFilters & { title: string }) | null;
  user?: KeyViewFilters & { title: string };
  key_pin?: string;
};
export function assertSavedKeyView(
  v: SavedKeyView,
  e: Engagement,
  kind: KeyViewKind,
  pin: string,
) {
  if (
    !v ||
    typeof v.id !== "string" ||
    v.engagement_id !== e.id ||
    v.current_engagement_revision !== e.revision ||
    v.kind !== kind ||
    !Number.isSafeInteger(v.version) ||
    v.version < 1 ||
    !["ACTIVE", "DELETED"].includes(v.status) ||
    !["CURRENT", "CONTEXT_CHANGED", "KEY_CHANGED", "KEY_UNAVAILABLE"].includes(
      v.context_status,
    ) ||
    typeof v.restorable !== "boolean" ||
    typeof v.personal_content_visible !== "boolean"
  )
    throw Error("Saved Key view response belongs to a changed context.");
  if (v.personal_content_visible) {
    if (
      v.context_status !== "CURRENT" ||
      v.status !== "ACTIVE" ||
      v.key_pin !== pin ||
      !v.user ||
      typeof v.user.title !== "string" ||
      !v.user.title.trim() ||
      v.user.title.length > 120
    )
      throw Error(
        "Saved Key view content has stale authority or version pins.",
      );
  } else if (
    v.user !== undefined ||
    v.key_pin !== undefined ||
    v.navigation !== null ||
    v.restorable
  )
    throw Error("Unavailable saved Key view contains private navigation.");
  if (v.navigation !== null && (!v.restorable || !v.personal_content_visible))
    throw Error("Saved Key view navigation is unavailable.");
  return v;
}
