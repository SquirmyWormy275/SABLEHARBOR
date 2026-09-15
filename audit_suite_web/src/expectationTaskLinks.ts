import type { Row } from "./api";
import type { BoundExpectation } from "./boundInstructorKey";

/** Authored task associations remain distinct from source links and test conclusions. */
export function validExpectationTaskLinks(
  row: Row,
  expected: BoundExpectation,
): boolean {
  if (row.task_mapping_status === undefined)
    return (
      row.authored_task_ids === undefined &&
      row.task_linked_workpaper_versions === undefined &&
      !expected.task_ids?.length
    );
  const ids = expected.task_ids ?? [];
  if (
    !Array.isArray(row.authored_task_ids) ||
    JSON.stringify(row.authored_task_ids) !== JSON.stringify(ids) ||
    ![
      "UNMAPPED",
      "EXPLICIT_AUTHORED_LINKS",
      "UNRESOLVED_IN_SELECTED_SCOPE",
    ].includes(String(row.task_mapping_status)) ||
    (row.task_mapping_status === "UNMAPPED") !== (ids.length === 0) ||
    !Array.isArray(row.task_linked_workpaper_versions)
  )
    return false;
  return row.task_linked_workpaper_versions.every((value: unknown) => {
    if (!value || typeof value !== "object" || Array.isArray(value))
      return false;
    const version = value as Row;
    return (
      typeof version.id === "string" &&
      Number.isSafeInteger(version.version) &&
      Number(version.version) > 0 &&
      typeof version.version_sha256 === "string" &&
      /^[a-f0-9]{64}$/.test(version.version_sha256) &&
      Array.isArray(version.task_ids) &&
      version.task_ids.length > 0 &&
      new Set(version.task_ids).size === version.task_ids.length &&
      version.task_ids.every(
        (id) => typeof id === "string" && ids.includes(id),
      ) &&
      Array.isArray(version.source_artifact_ids) &&
      version.source_artifact_ids.every(
        (id) => typeof id === "string" && id.length > 0,
      )
    );
  });
}
