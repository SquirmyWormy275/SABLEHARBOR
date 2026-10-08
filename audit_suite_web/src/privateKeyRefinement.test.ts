import { expect, it } from "vitest";
import type { BoundSnapshot } from "./boundInstructorKey";
import {
  boundIssuePage,
  boundSourcePage,
  boundRelationshipPage,
} from "./boundKeyNavigation";
import { filterKeys, type InstructorIndex } from "./instructorKey";
import {
  validateBoundFilters,
  validateArchiveFilters,
  type BoundKeyFilters,
} from "./instructorKeyViews";

const pin = "a".repeat(64);
const snapshot = {
  sources: [
    {
      id: "S1",
      company: "C",
      branch: "B",
      system: "physical.inventory",
      record: "ASSET-17",
      version: 2,
      sha256: pin,
      actor_visibility_at_binding: "READABLE_PRIOR_VERSION",
    },
    {
      id: "S2",
      company: "C",
      branch: "B",
      system: "physical.future",
      record: "R2",
      version: 1,
      sha256: "b".repeat(64),
      actor_visibility_at_binding: "FUTURE_UNAVAILABLE",
    },
  ],
  authored: {
    issues: [
      {
        id: "I1",
        control_ids: ["C1"],
        source_ids: ["S1"],
        claim: "Literal claim",
        uncertainty: "UNVALIDATED",
      },
    ],
    expectations: [
      {
        id: "E1",
        issue_ids: ["I1"],
        task_ids: ["TASK-17"],
        procedure: "Inspect Delta entry",
        acceptable_alternatives: ["Corroborate literal P014"],
      },
    ],
  },
} as BoundSnapshot;
const base: BoundKeyFilters = {
  query: "absent",
  issue_id: "I1",
  scope_to_issue: true,
  source: { id: "S1", version: 2, sha256: pin },
  page: 0,
};

it("finds only literal linked procedure, alternative, task and source values", () => {
  for (const query of ["TASK-17", "Delta", "P014", "ASSET-17", pin])
    expect(
      boundIssuePage(snapshot, { query, control_id: null, page: 0 }).rows.map(
        (r) => r.id,
      ),
    ).toEqual(["I1"]);
  expect(
    boundIssuePage(snapshot, { query: "R2", control_id: null, page: 0 }).rows,
  ).toEqual([]);
  expect(
    boundIssuePage(snapshot, {
      query: "invented owner",
      control_id: null,
      page: 0,
    }).rows,
  ).toEqual([]);
});
it("applies exact source metadata facets without turning captured visibility into current authority", () => {
  const filters = {
    system: "physical.inventory",
    visibility: "READABLE_PRIOR_VERSION",
  };
  expect(
    boundSourcePage(snapshot, {
      issueId: "",
      query: "",
      page: 0,
      sourceFilters: filters,
    }).rows.map((r) => r.id),
  ).toEqual(["S1"]);
  expect(
    boundSourcePage(snapshot, {
      issueId: "I1",
      query: "",
      page: 0,
      sourceFilters: { system: "physical.future", visibility: null },
    }).rows,
  ).toEqual([]);
  expect(
    validateBoundFilters({ ...base, source_filters: filters }, snapshot).source,
  ).toEqual(base.source);
  expect(validateBoundFilters(base, snapshot)).toEqual(base);
  expect(() =>
    validateBoundFilters(
      { ...base, source_filters: { system: "foreign", visibility: null } },
      snapshot,
    ),
  ).toThrow();
  expect(() =>
    validateBoundFilters(
      {
        ...base,
        source_filters: { system: null, visibility: null, owner: "made up" },
      } as BoundKeyFilters,
      snapshot,
    ),
  ).toThrow();
});
it("bounds literal relationship projection and does not invent links for an unknown selection", () => {
  expect(boundRelationshipPage(snapshot, "I1", "", 0).rows).toHaveLength(2);
  expect(boundRelationshipPage(snapshot, "", "S1", 0).rows[0].to).toBe("S1");
  expect(boundRelationshipPage(snapshot, "", "", 0, "E1").rows[0].from).toBe(
    "E1",
  );
  expect(boundRelationshipPage(snapshot, "unknown", "", 0).rows).toEqual([]);
  const large = structuredClone(snapshot);
  large.authored.expectations = Array.from({ length: 45 }, (_, i) => ({
    ...snapshot.authored.expectations[0],
    id: `E${i}`,
  }));
  expect(boundRelationshipPage(large, "I1", "", 0).rows).toHaveLength(20);
  expect(boundRelationshipPage(large, "I1", "", 999).page).toBe(2);
});
const index = {
  entries: [
    {
      id: "SEL.ONE.V1",
      raw_sha256: pin,
      canonical_sha256: "b".repeat(64),
      key_sha256: "c".repeat(64),
      review: {
        professional: "UNVALIDATED",
        causal_validation: "NOT_RUN",
        grading: "NOT_PERFORMED",
        gaps: ["missing mapping"],
      },
    },
    {
      id: "SEL.TWO.V1",
      raw_sha256: "d".repeat(64),
      canonical_sha256: "e".repeat(64),
      key_sha256: "f".repeat(64),
      review: {
        professional: "UNVALIDATED",
        causal_validation: "DISPUTED",
        grading: "NOT_PERFORMED",
        gaps: [],
      },
    },
  ],
} as unknown as InstructorIndex;
const archive = {
  query: "",
  selector: "all",
  option: "all",
  review: "all",
  scenario: null,
  page: 0,
};
it("searches exact archive hashes and review fields with optional literal facets", () => {
  expect(
    filterKeys(index.entries, { ...archive, query: pin }).map((r) => r.id),
  ).toEqual(["SEL.ONE.V1"]);
  expect(
    filterKeys(index.entries, {
      ...archive,
      review_facets: { causal_validation: "DISPUTED", grading: null },
    }).map((r) => r.id),
  ).toEqual(["SEL.TWO.V1"]);
  expect(
    filterKeys(index.entries, { ...archive, query: "unindexed person" }),
  ).toEqual([]);
  expect(validateArchiveFilters(archive, index)).toEqual(archive);
  expect(
    validateArchiveFilters(
      {
        ...archive,
        review_facets: { causal_validation: "DISPUTED", grading: null },
      },
      index,
    ).review_facets?.causal_validation,
  ).toBe("DISPUTED");
  expect(() =>
    validateArchiveFilters(
      {
        ...archive,
        review_facets: { causal_validation: "CERTIFIED", grading: null },
      },
      index,
    ),
  ).toThrow();
});
