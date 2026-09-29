import { expect, it } from "vitest";
import type { Engagement } from "./api";
import {
  inspectionArtifact,
  inspectionPins,
  inspectionSubmission,
  recordedInspections,
} from "./artifactInspection";
const artifact = {
  id: "ART-1",
  status: "AVAILABLE",
  sha256: "a".repeat(64),
  version: 2,
};
const state = () =>
  ({
    artifacts: [artifact],
    artifact_inspections: [],
  }) as unknown as Engagement;
it("pins an exact available learner original without guessing a version", () => {
  const e = state();
  expect(inspectionArtifact(e, "ART-1")).toEqual(artifact);
  expect(inspectionPins(artifact)).toEqual({
    artifact_id: "ART-1",
    sha256: "a".repeat(64),
    version: 2,
  });
  expect(
    inspectionPins({ ...artifact, version: undefined }).version,
  ).toBeNull();
});
it("withholds hidden, quarantined, ambiguous and malformed originals", () => {
  for (const patch of [
    { audience: "INSTRUCTOR_ONLY" },
    { status: "QUARANTINED" },
    { sha256: "bad" },
    { version: true },
    { version: -1 },
    { version: 1.5 },
  ]) {
    const e = state();
    e.artifacts = [{ ...artifact, ...patch }];
    expect(inspectionArtifact(e, "ART-1")).toBeUndefined();
  }
  const e = state();
  e.artifacts.push(artifact);
  expect(inspectionArtifact(e, "ART-1")).toBeUndefined();
});
it("retains exact form pins and removes only an empty optional task", () => {
  const p = {
    ...inspectionPins(artifact),
    locator: "rows1–3",
    observation: "Recorded exception",
    task_id: "",
  };
  expect(inspectionSubmission(p)).toEqual({
    ...inspectionPins(artifact),
    locator: p.locator,
    observation: p.observation,
  });
  expect(p.task_id).toBe("");
  expect(inspectionSubmission({ ...p, task_id: "TASK-1" }).task_id).toBe(
    "TASK-1",
  );
});
it("displays only records for this exact original and classification", () => {
  const e = state();
  const row = {
    id: "INSP-1",
    artifact_id: artifact.id,
    sha256: artifact.sha256,
    version: 2,
    classification: "SELF_REPORTED_INSPECTION",
  };
  e.artifact_inspections = [
    row,
    { ...row, id: "OLD", version: 1 },
    { ...row, id: "OTHER", sha256: "b".repeat(64) },
    { ...row, id: "UNKNOWN", classification: "AUTOMATIC" },
  ];
  expect(recordedInspections(e, artifact)).toEqual([row]);
  delete e.artifact_inspections;
  expect(recordedInspections(e, artifact)).toEqual([]);
});
