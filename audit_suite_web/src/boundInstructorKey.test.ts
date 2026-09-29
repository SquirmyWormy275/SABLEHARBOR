import { expect, it } from "vitest";
import {
  authoredRelationships,
  sourceTimeline,
  validateBoundResponse,
  type BoundResponse,
} from "./boundInstructorKey";
const fixture = () =>
  ({
    binding: {
      manifest_sha256: "a".repeat(64),
      engagement_id: "ENG1",
      bound_revision: 2,
      current_revision: 3,
      status: "HISTORICAL_REVISION",
    },
    snapshot: {
      status: "BOUND_INSTRUCTOR_AUTHORED_UNVALIDATED",
      professional_validation: "UNVALIDATED",
      authored_status: "INSTRUCTOR_AUTHORED_INFERENCE",
      grading: "NOT_PERFORMED",
      engagement: { id: "ENG1", revision: 2 },
      sources: [
        {
          id: "S1",
          record: "R1",
          event_at: "2027-01-01T08:00:00Z",
          available_at: "2027-01-02T08:00:00Z",
          imported_at: "2027-01-03T08:00:00Z",
        },
      ],
      authored: {
        issues: [
          {
            id: "I1",
            source_ids: ["S1"],
            control_ids: ["C1"],
            claim: "Neutral interpretation",
            uncertainty: "Needs review",
          },
        ],
        expectations: [
          {
            id: "E1",
            issue_ids: ["I1"],
            procedure: "Inspect source",
            acceptable_alternatives: ["Other corroboration"],
          },
        ],
        uncertainty: ["Unvalidated"],
      },
    },
  }) as unknown as BoundResponse;
it("keeps historical source identity separate from current revision and professional judgment", () => {
  const v = fixture();
  expect(() => validateBoundResponse(v, "ENG1")).not.toThrow();
  v.binding.status = "MATCHING_REVISION";
  expect(() => validateBoundResponse(v, "ENG1")).toThrow("Historical");
});
it("refuses cross-engagement or unsupported assurance labels", () => {
  const v = fixture();
  expect(() => validateBoundResponse(v, "ENG2")).toThrow();
  (v.snapshot as { professional_validation: string }).professional_validation =
    "APPROVED";
  expect(() => validateBoundResponse(v, "ENG1")).toThrow();
});
it("builds only exact authored references and rejects dangling links", () => {
  const v = fixture();
  expect(authoredRelationships(v.snapshot)).toEqual([
    { from: "I1", to: "S1", relation: "AUTHORED_SOURCE_REFERENCE" },
    { from: "E1", to: "I1", relation: "AUTHORED_EXPECTATION_REFERENCE" },
  ]);
  v.snapshot.authored.issues[0].source_ids.push("ABSENT");
  expect(() => validateBoundResponse(v, "ENG1")).toThrow("references");
});
it("preserves three distinct timestamp types in source timeline", () => {
  const v = fixture();
  expect(sourceTimeline(v.snapshot.sources).map((row) => row.field)).toEqual([
    "event_at",
    "available_at",
    "imported_at",
  ]);
  expect(
    sourceTimeline(v.snapshot.sources).every((row) => row.sourceId === "S1"),
  ).toBe(true);
});

it("requires complete physical routing pins for portfolio sources", () => {
  const v = fixture();
  v.snapshot.snapshot_isolation = "PER_COMPONENT_NOT_GLOBAL";
  expect(() => validateBoundResponse(v, "ENG1")).toThrow("routing pins");
  Object.assign(v.snapshot.sources[0], {
    source_store_id: "physical-one",
    source_system_alias: "ONE:records",
    registry_sha256: "b".repeat(64),
  });
  expect(() => validateBoundResponse(v, "ENG1")).not.toThrow();
  v.snapshot.sources[0].registry_sha256 = "unverified";
  expect(() => validateBoundResponse(v, "ENG1")).toThrow("routing pins");
});

it("rejects partial routing even if a legacy response omits snapshot isolation", () => {
  const v = fixture();
  v.snapshot.sources[0].source_store_id = "physical-one";
  expect(() => validateBoundResponse(v, "ENG1")).toThrow("routing pins");
});

it("preserves optional explicit procedure mappings and rejects duplicate IDs", () => {
  const v = fixture();
  v.snapshot.authored.expectations[0].task_ids = ["TASK-1"];
  expect(() => validateBoundResponse(v, "ENG1")).not.toThrow();
  v.snapshot.authored.expectations[0].task_ids.push("TASK-1");
  expect(() => validateBoundResponse(v, "ENG1")).toThrow("procedure links");
});
