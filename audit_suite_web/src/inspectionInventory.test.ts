import { expect, it } from "vitest";
import { inspectionInventory } from "./inspectionInventory";
const row = {
  id: "INSP-1",
  artifact_id: "ART-1",
  sha256: "a".repeat(64),
  version: 1,
  classification: "SELF_REPORTED_INSPECTION",
  actor: "USER-1",
  locator: "row 1",
  observation: "Missing recorded approval",
  history_sha256: "b".repeat(64),
  recorded_revision: 3,
  attribution: "AUDITED_ACTOR",
};
const value = () => ({
  status: "SELF_REPORTED_INSPECTION",
  records: [row],
  audited_actor_count: 1,
  other_actor_count: 0,
  unresolved_record_count: 0,
  qualification:
    "AUTHOR_ASSERTION_NOT_VERIFIED_READING_UNDERSTANDING_TESTING_OR_GRADE",
  absence: "NO_RECORDED_ASSERTION_DOES_NOT_ESTABLISH_NO_INSPECTION",
});
it("accepts exact bounded historical authored links", () => {
  expect(inspectionInventory(value(), 3, "USER-1")?.records).toEqual([row]);
  expect(inspectionInventory(undefined, 3, "USER-1")).toBeNull();
  expect(
    inspectionInventory("NOT_OBSERVABLE_NO_DOWNLOAD_EVENT_LOG", 3, "USER-1"),
  ).toBeNull();
});
it("rejects future, forged attribution and malformed pins", () => {
  for (const patch of [
    { recorded_revision: 4 },
    { recorded_revision: true },
    { actor: "OTHER" },
    { version: 1.5 },
    { history_sha256: "bad" },
    { classification: "VERIFIED_READING" },
  ])
    expect(() =>
      inspectionInventory(
        { ...value(), records: [{ ...row, ...patch }] },
        3,
        "USER-1",
      ),
    ).toThrow();
});
it("rejects inflated counts, duplicated IDs and false credit qualifiers", () => {
  for (const patch of [
    { audited_actor_count: 2 },
    { other_actor_count: 1 },
    { unresolved_record_count: -1 },
    { records: [row, row] },
    { qualification: "AUTOMATIC_PASS" },
  ])
    expect(() =>
      inspectionInventory({ ...value(), ...patch }, 3, "USER-1"),
    ).toThrow();
});
it("keeps other-actor work separate and legacy lack of inspection unknown", () => {
  const v = {
    ...value(),
    records: [{ ...row, actor: "OTHER", attribution: "OTHER_ACTOR" }],
    audited_actor_count: 0,
    other_actor_count: 1,
  };
  expect(inspectionInventory(v, 3, "USER-1")?.audited_actor_count).toBe(0);
  expect(() =>
    inspectionInventory(
      { status: "UNAVAILABLE_SELECTED_CONTEXT_MISMATCH", records: [row] },
      3,
      "USER-1",
    ),
  ).toThrow();
});
