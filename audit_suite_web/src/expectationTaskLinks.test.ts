import { expect, it } from "vitest";
import type { BoundExpectation } from "./boundInstructorKey";
import type { Row } from "./api";
import { validExpectationTaskLinks } from "./expectationTaskLinks";

const authored: BoundExpectation = {
  id: "E1",
  issue_ids: ["I1"],
  procedure: "Inspect the original",
  acceptable_alternatives: [],
  task_ids: ["TASK-1"],
};
const report = (): Row => ({
  id: "E1",
  authored_task_ids: ["TASK-1"],
  task_mapping_status: "EXPLICIT_AUTHORED_LINKS",
  task_linked_workpaper_versions: [
    {
      id: "WP-1",
      version: 1,
      version_sha256: "a".repeat(64),
      task_ids: ["TASK-1"],
      source_artifact_ids: [],
    },
  ],
});
it("accepts exact procedure links even when no source artifact intersects", () => {
  expect(validExpectationTaskLinks(report(), authored)).toBe(true);
});
it("rejects changed authored IDs, unrelated workpaper procedures and missing version hashes", () => {
  const value = report();
  value.authored_task_ids = ["TASK-2"];
  expect(validExpectationTaskLinks(value, authored)).toBe(false);
  const second = report();
  (second.task_linked_workpaper_versions as Row[])[0].task_ids = ["TASK-2"];
  expect(validExpectationTaskLinks(second, authored)).toBe(false);
  const third = report();
  delete (third.task_linked_workpaper_versions as Row[])[0].version_sha256;
  expect(validExpectationTaskLinks(third, authored)).toBe(false);
});
it("preserves legacy unmapped responses without silently dropping newly authored IDs", () => {
  expect(
    validExpectationTaskLinks(
      { id: "E1" },
      { ...authored, task_ids: undefined },
    ),
  ).toBe(true);
  expect(validExpectationTaskLinks({ id: "E1" }, authored)).toBe(false);
  expect(
    validExpectationTaskLinks(
      {
        ...report(),
        task_mapping_status: "UNRESOLVED_IN_SELECTED_SCOPE",
        task_linked_workpaper_versions: [],
      },
      authored,
    ),
  ).toBe(true);
});
