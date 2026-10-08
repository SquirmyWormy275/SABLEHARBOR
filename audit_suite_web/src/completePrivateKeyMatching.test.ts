import { expect, it } from "vitest";
import {
  authoredMatchIds,
  filterKeys,
  type InstructorIndex,
  type AuthoredMatchResult,
} from "./instructorKey";
import { validateArchiveFilters } from "./instructorKeyViews";

const fields = [
  "title",
  "mechanism",
  "facts",
  "actor_knowledge",
  "artifacts",
  "events",
  "playable_paths",
];
const index: InstructorIndex = {
  status: "UNBOUND_REFERENCE_LIBRARY",
  binding: { status: "NOT_BOUND", engagement_id: "E1" },
  archive: { sha256: "a".repeat(64) },
  audience: "INSTRUCTOR_ONLY",
  required: 30,
  migrated: 30,
  entries: Array.from({ length: 30 }, (_, i) => ({
    id: "MM-13.03.V" + i.toString().padStart(2, "0"),
    raw_sha256: "b".repeat(64),
    canonical_sha256: "c".repeat(64),
    key_sha256: "d".repeat(64),
    review: {
      professional: "UNVALIDATED",
      causal_validation: "NOT_RUN",
      grading: "NOT_RUN",
      gaps: [],
    },
  })),
  semantic_matching: {
    schema: "PRIVATE_COMPLETE_AUTHORED_MATCHING_V1",
    coverage_fields: fields,
    display_previews_only: true,
    complete_scalar_matching: true,
    query_max_characters: 1000,
  },
};
const query = "BeyondScalarNeedle";
const result: AuthoredMatchResult = {
  status: index.status,
  binding: index.binding,
  archive: index.archive,
  schema: "PRIVATE_COMPLETE_AUTHORED_MATCH_RESULT_V1",
  audience: "INSTRUCTOR_ONLY",
  query,
  coverage_fields: fields,
  complete_scalar_matching: true,
  matching_entry_ids: index.entries.map((x) => x.id),
  matched_entries: 30,
  total_entries: 30,
};
const filter = {
  query,
  selector: "all",
  option: "all",
  review: "all",
  scenario: null,
  page: 1,
};
it("uses complete source-bound match IDs beyond absent display previews and validates the saved exact page", () => {
  expect(filterKeys(index.entries, filter)).toHaveLength(0);
  const ids = authoredMatchIds(result, index, query);
  expect(
    filterKeys(index.entries, { ...filter, complete_match_ids: ids }),
  ).toHaveLength(30);
  expect(validateArchiveFilters(filter, index, ids)).toEqual(filter);
  expect(() => validateArchiveFilters(filter, index)).toThrow(
    "Wait for complete",
  );
  expect(validateArchiveFilters(filter, index, undefined, true)).toEqual(
    filter,
  );
  expect(() => validateArchiveFilters(filter, index, ids.slice(0, 1))).toThrow(
    "exact filter",
  );
});
it("refuses stale/foreign/duplicate/unknown match receipts instead of using previews as fallback", () => {
  for (const changed of [
    { ...result, query: "prior query" },
    { ...result, archive: { sha256: "e".repeat(64) } },
    { ...result, matching_entry_ids: ["unknown"], matched_entries: 1 },
    {
      ...result,
      matching_entry_ids: [index.entries[0].id, index.entries[0].id],
      matched_entries: 2,
    },
    { ...result, coverage_fields: ["private_credentials"] },
    { ...result, full_text: "never ship corpus text" },
  ])
    expect(() => authoredMatchIds(changed, index, query)).toThrow();
});
it("keeps old thin-index metadata and saved row shape compatible", () => {
  const old = { ...index };
  delete old.semantic_matching;
  const saved = { ...filter, query: "MM-13.03", page: 1 };
  expect(validateArchiveFilters(saved, old)).toEqual(saved);
  expect(filterKeys(old.entries, saved)).toHaveLength(30);
});
