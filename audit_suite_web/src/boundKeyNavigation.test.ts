import { expect, it } from "vitest";
import {
  boundSourcePage,
  issueControlLabel,
  scopedTimelineSources,
  selectedIssueExpectations,
} from "./boundKeyNavigation";
import type { BoundSnapshot } from "./boundInstructorKey";
const fixture = () =>
  ({
    sources: Array.from({ length: 56 }, (_, i) => ({
      id: `S${i}`,
      record: `R${i}`,
      version: 1,
    })),
    authored: {
      issues: [
        { id: "I1", control_ids: ["C1"], source_ids: ["S0", "S1", "S12"] },
        { id: "I2", control_ids: ["C2"], source_ids: ["S1"] },
      ],
      expectations: [
        { id: "E1", issue_ids: ["I1", "I2"] },
        { id: "E2", issue_ids: ["I2"] },
      ],
    },
  }) as BoundSnapshot;
it("bounds all56 originals and clamps stale page without substituting identities", () => {
  const s = fixture();
  const page = boundSourcePage(s, { issueId: "", query: "", page: 5 });
  expect(page.rows.map((r) => r.id)).toEqual([
    "S50",
    "S51",
    "S52",
    "S53",
    "S54",
    "S55",
  ]);
  expect(page.total).toBe(56);
  expect(
    boundSourcePage(s, { issueId: "I1", query: "", page: 5 }).rows.map(
      (r) => r.id,
    ),
  ).toEqual(["S0", "S1", "S12"]);
});
it("search respects exact issue relationships and preserves empty results", () => {
  expect(
    boundSourcePage(fixture(), { issueId: "I2", query: "R12", page: 4 }).rows,
  ).toEqual([]);
  expect(
    boundSourcePage(fixture(), { issueId: "", query: "R12", page: 0 }).rows.map(
      (r) => r.id,
    ),
  ).toEqual(["S12"]);
});
it("shared source and expectation appear once without inferring control-only links", () => {
  const s = fixture();
  expect(
    boundSourcePage(s, { issueId: "I1", query: "", page: 0 }).rows,
  ).toHaveLength(3);
  expect(selectedIssueExpectations(s, "I1").map((r) => r.id)).toEqual(["E1"]);
  expect(selectedIssueExpectations(s, "I2").map((r) => r.id)).toEqual([
    "E1",
    "E2",
  ]);
});
it("uses actual control labels and bounds timeline to explicit source or current page", () => {
  const s = fixture();
  expect(
    issueControlLabel(s.authored.issues[0], [
      { id: "C1", title: "Access review" },
    ]),
  ).toBe("C1 · Access review");
  expect(issueControlLabel(s.authored.issues[1], [])).toBe("C2");
  const page = boundSourcePage(s, { issueId: "", query: "", page: 0 }).rows;
  expect(scopedTimelineSources(s.sources[30], page)).toEqual([s.sources[30]]);
  expect(scopedTimelineSources(undefined, page)).toHaveLength(10);
});
