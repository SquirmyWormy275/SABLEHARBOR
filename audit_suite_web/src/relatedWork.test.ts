import { expect, it } from "vitest";
import type { Engagement, Row } from "./api";
import { relatedWork, resolveRelatedWork } from "./relatedWork";

const fixture = () =>
  ({
    id: "E",
    title: "Authorized engagement",
    mode: "CLEAN",
    scope: { boundaries: ["corporate"] },
    controls: [
      { id: "C1", title: "Access" },
      { id: "C2", title: "Other" },
    ],
    tasks: [
      {
        id: "T1",
        title: "Inspect access",
        control_id: "C1",
        boundary_id: "corporate",
      },
      { id: "T2", title: "Inspect access again", control_id: "C1" },
      {
        id: "T3",
        title: "Excluded access",
        control_id: "C1",
        boundary_id: "elsewhere",
      },
      {
        id: "T4",
        title: "Old-scope access",
        control_id: "C1",
        applicability: "PRIOR_SCOPE_REQUIRES_REASSESSMENT",
      },
    ],
    requests: [
      { id: "R1", title: "Access export", control_id: "C1" },
      { id: "R2", control_id: "C2" },
    ],
    artifacts: [
      {
        id: "A1",
        title: "Retained export",
        request_id: "R1",
        status: "AVAILABLE",
      },
      { id: "A2", control_id: "C1", status: "UNAVAILABLE" },
      {
        id: "A3",
        title: "Access export",
        request_id: "R2",
        status: "AVAILABLE",
      },
      {
        id: "A4",
        control_id: "C1",
        status: "AVAILABLE",
        boundary_id: "elsewhere",
      },
    ],
    populations: [
      {
        id: "P1",
        title: "Provisional accounts",
        version: 1,
        control_id: "C1",
        status: "DECLARED",
      },
    ],
    notes: [{ id: "N1", title: "Attributed access claim", control_id: "C1" }],
    findings: [{ id: "F1", title: "Recorded limitation", control_id: "C1" }],
    workpapers: [
      {
        id: "W1",
        title: "Access paper",
        versions: [
          { version: 1, task_ids: ["T1"], text: "First exact version" },
          { version: 2, task_ids: ["T2"], text: "Later unlinked task version" },
          { version: 3, task_ids: ["T3"], text: "Other boundary" },
        ],
      },
    ],
    instructor_key: { rubric: "Never index hidden answer" },
    events: [
      {
        id: "FUTURE",
        control_id: "C1",
        title: "Never navigate future Key event",
      },
    ],
  }) as unknown as Engagement;
const refs = (
  e: Engagement,
  kind: "task" | "control",
  id: string,
  groupId: string,
) =>
  relatedWork(e, kind, id)
    ?.groups.find((group) => group.id === groupId)
    ?.links.map((link) => link.reference);

it("separates shared-control context from exact procedure workpaper versions", () => {
  const e = fixture();
  expect(refs(e, "task", "T1", "control")).toEqual([
    { collection: "controls", id: "C1" },
  ]);
  expect(refs(e, "task", "T1", "requests")).toEqual([
    { collection: "requests", id: "R1" },
  ]);
  expect(refs(e, "task", "T1", "artifacts")).toEqual([
    { collection: "artifacts", id: "A1" },
  ]);
  expect(refs(e, "task", "T1", "workpapers")).toEqual([
    { collection: "workpapers", id: "W1", version: 1 },
  ]);
  expect(refs(e, "control", "C1", "procedures")).toEqual([
    { collection: "tasks", id: "T1" },
    { collection: "tasks", id: "T2" },
  ]);
  expect(refs(e, "control", "C1", "workpapers")).toEqual([
    { collection: "workpapers", id: "W1", version: 1 },
    { collection: "workpapers", id: "W1", version: 2 },
  ]);
  expect(
    relatedWork(e, "task", "T1")!.groups.find((g) => g.id === "requests")!
      .links[0].reason,
  ).toContain("procedure support has not been inferred");
});
it("never substitutes the latest workpaper for an earlier explicit task link", () => {
  const e = fixture();
  const ref = refs(e, "task", "T1", "workpapers")![0];
  expect(resolveRelatedWork(e, ref)?.row.id).toBe("W1");
  e.workpapers[0].versions = (e.workpapers[0].versions as Row[]).filter(
    (v) => v.version !== 1,
  );
  expect(resolveRelatedWork(e, ref)).toBeNull();
  expect(refs(e, "task", "T1", "workpapers")).toEqual([]);
});
it("fails closed for duplicate anchor, target and workpaper version identities", () => {
  const e = fixture();
  e.tasks.push({ ...e.tasks[0] });
  expect(relatedWork(e, "task", "T1")).toBeNull();
  expect(refs(e, "control", "C1", "procedures")).toEqual([
    { collection: "tasks", id: "T2" },
  ]);
  e.artifacts.push({ ...e.artifacts[0] });
  expect(refs(e, "control", "C1", "artifacts")).toEqual([]);
  expect(
    resolveRelatedWork(e, { collection: "artifacts", id: "A1" }),
  ).toBeNull();
  (e.workpapers[0].versions as Row[]).push({
    id: "duplicate-v2",
    version: 2,
    task_ids: ["T2"],
  });
  expect(
    resolveRelatedWork(e, { collection: "workpapers", id: "W1", version: 2 }),
  ).toBeNull();
  expect(refs(e, "control", "C1", "workpapers")).toEqual([]);
});
it("respects scope and exact declared population version without inferring absence", () => {
  const e = fixture();
  expect(relatedWork(e, "task", "T3")).toBeNull();
  expect(relatedWork(e, "task", "T4")).toBeNull();
  const ref = refs(e, "control", "C1", "populations")![0];
  expect(ref).toEqual({ collection: "populations", id: "P1", version: 1 });
  e.populations[0].version = 2;
  expect(resolveRelatedWork(e, ref)).toBeNull();
  e.scope.boundaries = ["elsewhere"];
  expect(resolveRelatedWork(e, { collection: "tasks", id: "T1" })).toBeNull();
});
it("uses neither matching names, mode, hidden Key, future events nor other engagement records", () => {
  const e = fixture();
  const before = JSON.stringify(e);
  const context = relatedWork(e, "task", "T1");
  expect(JSON.stringify(context)).not.toContain("Never");
  expect(JSON.stringify(context)).not.toContain("A3");
  expect(JSON.stringify(e)).toBe(before);
  e.mode = "MESSY";
  expect(relatedWork(e, "task", "T1")).toEqual(context);
  const other = fixture();
  other.id = "OTHER";
  other.controls = [];
  other.requests = [];
  other.artifacts = [];
  expect(refs(other, "task", "T1", "control")).toEqual([]);
  expect(refs(other, "task", "T1", "artifacts")).toBeUndefined();
});
