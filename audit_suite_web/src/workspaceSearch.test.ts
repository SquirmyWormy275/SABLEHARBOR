import { expect, it } from "vitest";
import type { Engagement } from "./api";
import {
  resolveSearchHit,
  searchWorkspace,
  searchContext,
} from "./workspaceSearch";
const fixture = () =>
  ({
    id: "ENG-1",
    title: "Neutral",
    scope: {
      boundaries: ["corporate"],
      period_start: "2027-01-01",
      period_end: "2027-12-31",
    },
    permissions: ["read"],
    controls: [
      {
        id: "C1",
        title: "Access review",
        description: "Quarterly account inspection",
      },
    ],
    requests: [{ id: "R1", title: "Account population" }],
    artifacts: [],
    workpapers: [],
    findings: [],
    people: [{ id: "P1", name: "Neutral owner" }],
    populations: [],
    tasks: [],
    notes: [
      {
        id: "N1",
        text: "Corrected account count",
        content: "Superseded confidential phrase",
        rubric: "private hidden phrase",
      },
    ],
    events: [{ id: "EV1", title: "future hidden phrase" }],
    instructor_key: { facts: ["secret key phrase"] },
  }) as unknown as Engagement;
it("groups actual authorized records with bounded public snippets", () => {
  const groups = searchWorkspace(fixture(), "account");
  expect(groups.map((g) => g.kind)).toEqual(["control", "request", "note"]);
  expect(groups[0].hits[0].snippet).toBe("Quarterly account inspection");
  expect(searchWorkspace(fixture(), "neutral", "person")[0].hits[0].title).toBe(
    "Neutral owner",
  );
});
it.each([
  "private hidden phrase",
  "future hidden phrase",
  "secret key phrase",
  "Superseded confidential phrase",
])("never indexes private/arbitrary/future or stale fields: %s", (q) =>
  expect(searchWorkspace(fixture(), q)).toEqual([]),
);
it("isolates engagement/viewer/scope/permissions and does not mutate input", () => {
  const a = fixture(),
    b = fixture();
  b.id = "ENG-2";
  b.controls = [];
  expect(searchWorkspace(b, "inspection")).toEqual([]);
  expect(searchContext(a, "a")).not.toBe(searchContext(a, "b"));
  expect(searchContext(a, "a")).not.toBe(searchContext(b, "a"));
  const before = JSON.stringify(a);
  searchWorkspace(a, "account");
  expect(JSON.stringify(a)).toBe(before);
  b.id = a.id;
  b.scope.boundaries = ["other"];
  expect(searchContext(a, "a")).not.toBe(searchContext(b, "a"));
  b.scope = a.scope;
  b.permissions = [];
  expect(searchContext(a, "a")).not.toBe(searchContext(b, "a"));
});
it("re-resolves rows and refuses deleted or duplicate record identities", () => {
  const e = fixture(),
    hit = searchWorkspace(e, "access")[0].hits[0];
  expect(resolveSearchHit(e, hit)).toBe(e.controls[0]);
  e.controls.push({ ...e.controls[0] });
  expect(resolveSearchHit(e, hit)).toBeNull();
  expect(searchWorkspace(e, "access")).toEqual([]);
  e.controls = [];
  expect(resolveSearchHit(e, hit)).toBeNull();
});
it("bounds visible hits and snippet/title size without misleading total", () => {
  const e = fixture();
  e.controls = Array.from({ length: 40 }, (_, i) => ({
    id: `C${i}`,
    title: "Account " + "x".repeat(400),
    description: "account " + "y".repeat(400),
  }));
  const g = searchWorkspace(e, "account")[0];
  expect(g.total).toBe(40);
  expect(g.hits).toHaveLength(25);
  expect(
    g.hits.every((h) => h.title.length <= 180 && h.snippet.length <= 212),
  ).toBe(true);
  expect(searchWorkspace(e, "   ")).toEqual([]);
});
it("does not turn HTML or regex-like input into execution or pattern search", () => {
  const e = fixture();
  e.notes = [{ id: "N2", text: "Literal <script> and .* text" }];
  expect(searchWorkspace(e, ".*")[0].hits[0].snippet).toContain(".*");
  expect(searchWorkspace(e, "[invalid")).toEqual([]);
});
