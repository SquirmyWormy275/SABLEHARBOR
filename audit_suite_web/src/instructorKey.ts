import {
  validateReferenceCrosswalk,
  type ReferenceCrosswalkValue,
} from "./referenceCrosswalk";
export type KeyReview = {
  professional: string;
  causal_validation: string;
  grading: string;
  gaps: string[];
};
export type KeyEntry = {
  id: string;
  raw_sha256: string;
  canonical_sha256: string;
  key_sha256: string;
  review: KeyReview;
  semantic_search?: {
    schema: "PRIVATE_AUTHORED_SEMANTIC_SEARCH_V1";
    basis: "LITERAL_AUTHORED_SCALARS_NOT_VERIFIED_PERSON_ASSET_PERIOD_OR_CAUSALITY";
    id: string;
    source_sha256: string;
    canonical_sha256: string;
    key_sha256: string;
    coverage_fields: string[];
    included_by_field: Record<string, number>;
    omitted_by_field: Record<string, number>;
    total_scalars: number;
    omitted_scalars: number;
    truncated_values: number;
    terms: {
      pointer: string;
      text: string;
      truncated?: true;
      full_characters?: number;
      value_sha256?: string;
    }[];
  };
};
export type KeyContext = {
  status: "UNBOUND_REFERENCE_LIBRARY";
  binding: { status: "NOT_BOUND"; engagement_id: string };
  archive: { sha256: string };
  reference_crosswalk?: ReferenceCrosswalkValue;
};
export type InstructorIndex = KeyContext & {
  audience: "INSTRUCTOR_ONLY";
  required: number;
  migrated: number;
  entries: KeyEntry[];
  semantic_matching?: {
    schema: "PRIVATE_COMPLETE_AUTHORED_MATCHING_V1";
    coverage_fields: string[];
    display_previews_only: true;
    complete_scalar_matching: true;
    query_max_characters: 1000;
  };
};
export type AuthoredMatchResult = KeyContext & {
  schema: "PRIVATE_COMPLETE_AUTHORED_MATCH_RESULT_V1";
  audience: "INSTRUCTOR_ONLY";
  query: string;
  coverage_fields: string[];
  complete_scalar_matching: true;
  matching_entry_ids: string[];
  matched_entries: number;
  total_entries: number;
};
export function authoredMatchIds(
  value: AuthoredMatchResult,
  index: InstructorIndex,
  query: string,
): string[] {
  assertKeyContext(value, index.binding.engagement_id);
  if (
    Object.keys(value).sort().join(",") !==
      [
        "schema",
        "audience",
        "status",
        "binding",
        "archive",
        "query",
        "coverage_fields",
        "complete_scalar_matching",
        "matching_entry_ids",
        "matched_entries",
        "total_entries",
      ]
        .sort()
        .join(",") ||
    value.schema !== "PRIVATE_COMPLETE_AUTHORED_MATCH_RESULT_V1" ||
    value.audience !== "INSTRUCTOR_ONLY" ||
    value.archive.sha256 !== index.archive.sha256 ||
    value.query !== query ||
    query.length > 1000 ||
    value.complete_scalar_matching !== true ||
    JSON.stringify(value.coverage_fields) !==
      JSON.stringify(index.semantic_matching?.coverage_fields) ||
    value.total_entries !== index.entries.length ||
    !Array.isArray(value.matching_entry_ids) ||
    value.matched_entries !== value.matching_entry_ids.length ||
    new Set(value.matching_entry_ids).size !==
      value.matching_entry_ids.length ||
    value.matching_entry_ids.some(
      (id) =>
        typeof id !== "string" ||
        !index.entries.some((entry) => entry.id === id),
    )
  )
    throw Error(
      "Complete authored matches differ from the current query/archive.",
    );
  return value.matching_entry_ids;
}
export type InstructorDetail = KeyContext & {
  key: {
    schema: "PRIVATE_INSTRUCTOR_KEY_V1";
    audience: "INSTRUCTOR_ONLY";
    id: string;
    source: {
      raw_sha256: string;
      canonical_sha256: string;
      schema_version: string;
    };
    review: KeyReview;
    explanation: {
      title: string;
      mechanism: unknown;
      facts: unknown[];
      actor_knowledge: unknown[];
      artifacts: unknown[];
      events: unknown[];
      playable_paths: unknown[];
      rubric: {
        supported_conclusions: unknown[];
        acceptable_alternatives: unknown[];
        unsupported_guesses: unknown[];
      };
    };
    graph: unknown;
  };
};
export const keyOption = (id: string) => id.replace(/\.V\d+$/, "");
export const keySelector = (id: string) => id.split(".")[0];
export function filterKeys(
  entries: KeyEntry[],
  f: {
    query: string;
    selector: string;
    option: string;
    review: string;
    review_facets?: {
      causal_validation: string | null;
      grading: string | null;
    };
    complete_match_ids?: string[];
  },
) {
  const q = f.query.trim().toLowerCase();
  return entries.filter(
    (e) =>
      (f.selector === "all" || keySelector(e.id) === f.selector) &&
      (f.option === "all" || keyOption(e.id) === f.option) &&
      (f.review === "all" || e.review.professional === f.review) &&
      (!f.review_facets?.causal_validation ||
        e.review.causal_validation === f.review_facets.causal_validation) &&
      (!f.review_facets?.grading ||
        e.review.grading === f.review_facets.grading) &&
      (!q ||
        (f.complete_match_ids
          ? f.complete_match_ids.includes(e.id)
          : [
              e.id,
              e.raw_sha256,
              e.canonical_sha256,
              e.key_sha256,
              e.review.professional,
              e.review.causal_validation,
              e.review.grading,
              ...e.review.gaps,
              ...semanticSearchTerms(e),
            ]
              .join(" ")
              .toLowerCase()
              .includes(q))),
  );
}
export function semanticSearchTerms(entry: KeyEntry): string[] {
  const s = entry.semantic_search;
  if (!s) return [];
  const fields = [
    "title",
    "mechanism",
    "facts",
    "actor_knowledge",
    "artifacts",
    "events",
    "playable_paths",
  ];
  if (
    s.schema !== "PRIVATE_AUTHORED_SEMANTIC_SEARCH_V1" ||
    s.basis !==
      "LITERAL_AUTHORED_SCALARS_NOT_VERIFIED_PERSON_ASSET_PERIOD_OR_CAUSALITY" ||
    s.id !== entry.id ||
    s.source_sha256 !== entry.raw_sha256 ||
    s.canonical_sha256 !== entry.canonical_sha256 ||
    s.key_sha256 !== entry.key_sha256 ||
    JSON.stringify(s.coverage_fields) !== JSON.stringify(fields) ||
    !Array.isArray(s.terms) ||
    s.terms.length > 32 ||
    ![s.total_scalars, s.omitted_scalars, s.truncated_values].every(
      (n) => Number.isSafeInteger(n) && n >= 0,
    ) ||
    s.total_scalars !== s.terms.length + s.omitted_scalars ||
    fields.some(
      (field) =>
        !Number.isSafeInteger(s.included_by_field?.[field]) ||
        s.included_by_field[field] < 0 ||
        !Number.isSafeInteger(s.omitted_by_field?.[field]) ||
        s.omitted_by_field[field] < 0,
    ) ||
    Object.values(s.included_by_field).reduce((a, b) => a + b, 0) !==
      s.terms.length ||
    Object.values(s.omitted_by_field).reduce((a, b) => a + b, 0) !==
      s.omitted_scalars ||
    s.terms.some(
      (t) =>
        typeof t.pointer !== "string" ||
        t.pointer.length > 256 ||
        !fields.some(
          (field) =>
            t.pointer === "/" + field ||
            t.pointer.startsWith("/" + field + "/"),
        ) ||
        typeof t.text !== "string" ||
        [...t.text].length > 128 ||
        (t.truncated &&
          (!Number.isSafeInteger(t.full_characters) ||
            t.full_characters! <= 128 ||
            !/^[a-f0-9]{64}$/.test(t.value_sha256 ?? ""))),
    )
  )
    throw Error(
      "Authored search projection differs from its preserved source.",
    );
  return s.terms.map((t) => t.text);
}
export function assertKeyContext(v: KeyContext, id: string) {
  if (
    v.status !== "UNBOUND_REFERENCE_LIBRARY" ||
    v.binding?.status !== "NOT_BOUND" ||
    v.binding.engagement_id !== id ||
    !/^[a-f0-9]{64}$/.test(v.archive?.sha256 ?? "")
  )
    throw Error("Protected source context does not match this engagement.");
  if ("entries" in v)
    (v as InstructorIndex).entries.forEach(semanticSearchTerms);
  if ("entries" in v && (v as InstructorIndex).semantic_matching) {
    const matching = (v as InstructorIndex).semantic_matching!;
    if (
      matching.schema !== "PRIVATE_COMPLETE_AUTHORED_MATCHING_V1" ||
      matching.display_previews_only !== true ||
      matching.complete_scalar_matching !== true ||
      matching.query_max_characters !== 1000 ||
      JSON.stringify(matching.coverage_fields) !==
        JSON.stringify([
          "title",
          "mechanism",
          "facts",
          "actor_knowledge",
          "artifacts",
          "events",
          "playable_paths",
        ])
    )
      throw Error("Complete authored matching coverage is invalid.");
  }
  if (v.reference_crosswalk)
    validateReferenceCrosswalk(v.reference_crosswalk, id, v.archive.sha256);
  if (v.reference_crosswalk && "entries" in v) {
    const index = v as InstructorIndex;
    if (
      index.entries.length !== v.reference_crosswalk.rows.length ||
      v.reference_crosswalk.rows.some(
        (row) =>
          !index.entries.some(
            (entry) =>
              entry.id === row.legacy_id &&
              entry.raw_sha256 === row.raw_sha256 &&
              entry.canonical_sha256 === row.canonical_sha256 &&
              entry.key_sha256 === row.key_sha256,
          ),
      )
    )
      throw Error(
        "Reference crosswalk differs from the exact preserved variants.",
      );
  }
}
export function assertKeyDetail(
  v: InstructorDetail,
  e: KeyEntry,
  id: string,
  archive: string,
) {
  assertKeyContext(v, id);
  const k = v.key;
  if (
    v.archive.sha256 !== archive ||
    k?.schema !== "PRIVATE_INSTRUCTOR_KEY_V1" ||
    k.audience !== "INSTRUCTOR_ONLY" ||
    k.id !== e.id ||
    k.source.raw_sha256 !== e.raw_sha256 ||
    k.source.canonical_sha256 !== e.canonical_sha256
  )
    throw Error("Explanation differs from the selected immutable source.");
}
