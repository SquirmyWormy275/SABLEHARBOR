import { expect, it } from "vitest";
import type { Engagement } from "./api";
import type { BoundSnapshot } from "./boundInstructorKey";
import type { InstructorIndex } from "./instructorKey";
import {
  assertSavedKeyView,
  keyViewContext,
  validateBoundFilters,
  validateArchiveFilters,
  type SavedKeyView,
  type BoundKeyFilters,
  type ArchiveKeyFilters,
} from "./instructorKeyViews";
const pin = "a".repeat(64),
  e = {
    id: "E",
    revision: 4,
    permissions: ["instruct"],
    scope: {},
  } as Engagement;
const snapshot = {
  sources: [
    {
      id: "S",
      version: 1,
      sha256: pin,
      company: "C",
      branch: "B",
      system: "SYS",
      record: "R",
    },
  ],
  authored: { issues: [{ id: "I", source_ids: ["S"] }] },
} as BoundSnapshot;
const bound: BoundKeyFilters = {
  query: "no matches",
  issue_id: "I",
  scope_to_issue: true,
  source: { id: "S", version: 1, sha256: pin },
  page: 0,
};
const archive = {
  entries: [
    {
      id: "SEL.OPT.V1",
      key_sha256: pin,
      review: { professional: "UNVALIDATED", gaps: [] },
    },
  ],
} as unknown as InstructorIndex;
const filters: ArchiveKeyFilters = {
  query: "",
  selector: "SEL",
  option: "SEL.OPT",
  review: "UNVALIDATED",
  scenario: { id: "SEL.OPT.V1", key_sha256: pin },
  page: 0,
};
it("restores exact bound source outside filter without substituting latest", () => {
  expect(validateBoundFilters(bound, snapshot)).toEqual(bound);
  expect(() =>
    validateBoundFilters(
      { ...bound, source: { ...bound.source!, version: 2 } },
      snapshot,
    ),
  ).toThrow();
  expect(() =>
    validateBoundFilters({ ...bound, issue_id: "missing" }, snapshot),
  ).toThrow();
  expect(() => validateBoundFilters({ ...bound, page: 1 }, snapshot)).toThrow();
});
it("validates archive selectors, page and exact scenario digest", () => {
  expect(validateArchiveFilters(filters, archive)).toEqual(filters);
  expect(() =>
    validateArchiveFilters(
      {
        ...filters,
        scenario: { ...filters.scenario!, key_sha256: "b".repeat(64) },
      },
      archive,
    ),
  ).toThrow();
  expect(() =>
    validateArchiveFilters({ ...filters, selector: "unrelated" }, archive),
  ).toThrow();
  expect(() =>
    validateArchiveFilters({ ...filters, page: 1 }, archive),
  ).toThrow();
});
function row(): SavedKeyView {
  return {
    id: "V",
    engagement_id: "E",
    kind: "BOUND",
    version: 1,
    status: "ACTIVE",
    saved_engagement_revision: 3,
    current_engagement_revision: 4,
    context_status: "CURRENT",
    revision_status: "ENGAGEMENT_ADVANCED",
    restorable: true,
    personal_content_visible: true,
    key_pin: pin,
    user: { ...bound, title: "Private question" },
    navigation: null,
  };
}
it("ordinary revision advance is separate from changed Key authority", () => {
  expect(assertSavedKeyView(row(), e, "BOUND", pin).revision_status).toBe(
    "ENGAGEMENT_ADVANCED",
  );
  expect(() => assertSavedKeyView(row(), e, "BOUND", "b".repeat(64))).toThrow();
  expect(() =>
    assertSavedKeyView(
      { ...row(), current_engagement_revision: 3 },
      e,
      "BOUND",
      pin,
    ),
  ).toThrow();
});
it("redacted metadata contains no title/query/Key pin/navigation", () => {
  const { user: _, key_pin: __, ...v } = row();
  const hidden = {
    ...v,
    context_status: "KEY_CHANGED" as const,
    personal_content_visible: false,
    restorable: false,
  };
  expect(assertSavedKeyView(hidden, e, "BOUND", pin)).toEqual(hidden);
  expect(() =>
    assertSavedKeyView({ ...hidden, user: row().user }, e, "BOUND", pin),
  ).toThrow();
});
it("viewer, scope, revision and Key changes invalidate UI context", () => {
  const key = keyViewContext(e, "T", "BOUND", pin);
  for (const other of [
    keyViewContext(e, "OTHER", "BOUND", pin),
    keyViewContext({ ...e, revision: 5 }, "T", "BOUND", pin),
    keyViewContext(
      { ...e, company_source_binding: { branch: "other" } },
      "T",
      "BOUND",
      pin,
    ),
    keyViewContext(e, "T", "BOUND", "b".repeat(64)),
  ])
    expect(other).not.toBe(key);
});
