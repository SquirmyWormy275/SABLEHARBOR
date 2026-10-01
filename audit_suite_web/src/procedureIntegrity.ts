import type { Engagement } from "./api";

export type OriginalIntegrity = {
  schema_version: string;
  engagement_id: string;
  engagement_revision: number;
  status: string;
  metadata_status: string;
  automatic_testing_credit: false;
  counts: {
    referenced: number;
    verified: number;
    missing: number;
    integrity_failure: number;
    read_unavailable: number;
  } | null;
  artifacts: { artifact_id: string; status: string }[];
  traces: { id: string; status: string; artifact_ids?: string[] }[];
};

export function currentIntegrity(
  report: OriginalIntegrity,
  engagement: Engagement,
): boolean {
  if (!report || typeof report !== "object") return false;
  if (
    report.schema_version !== "1.0" ||
    report.engagement_id !== engagement.id ||
    report.engagement_revision !== engagement.revision ||
    report.automatic_testing_credit !== false ||
    !Array.isArray(report.artifacts) ||
    !Array.isArray(report.traces) ||
    !["AVAILABLE", "PARTIAL_UNAVAILABLE", "INPUT_UNAVAILABLE"].includes(
      report.metadata_status,
    ) ||
    ![
      "VERIFIED_RETAINED_BYTES_ONLY",
      "PARTIAL_UNAVAILABLE",
      "NO_RECORDED_TRACES",
      "NO_RETAINED_ORIGINAL_REFERENCED",
      "METADATA_UNAVAILABLE",
      "RECHECK_INPUT_UNAVAILABLE",
    ].includes(report.status)
  )
    return false;
  const artifactStatuses = [
    "VERIFIED_RETAINED_BYTES",
    "MISSING_RETAINED_BYTES",
    "RETAINED_BYTE_INTEGRITY_FAILURE",
    "RETAINED_BYTE_READ_UNAVAILABLE",
  ];
  const traceStatuses = [
    "VERIFIED_RETAINED_BYTES",
    "RETAINED_BYTES_UNAVAILABLE",
    "NO_RETAINED_ORIGINAL_REFERENCED",
    "METADATA_UNAVAILABLE",
    "NOT_RECHECKED",
  ];
  if (
    report.artifacts.some(
      (row) =>
        !row ||
        typeof row.artifact_id !== "string" ||
        !row.artifact_id ||
        !artifactStatuses.includes(row.status),
    ) ||
    new Set(report.artifacts.map((row) => row.artifact_id)).size !==
      report.artifacts.length ||
    report.traces.some(
      (row) =>
        !row ||
        typeof row.id !== "string" ||
        !row.id ||
        !traceStatuses.includes(row.status) ||
        (row.artifact_ids !== undefined &&
          (!Array.isArray(row.artifact_ids) ||
            row.artifact_ids.some((id) => typeof id !== "string" || !id))),
    ) ||
    new Set(report.traces.map((row) => row.id)).size !== report.traces.length
  )
    return false;
  const artifactById = new Map(
    report.artifacts.map((row) => [row.artifact_id, row.status]),
  );
  const citedIds = new Set<string>();
  for (const row of report.traces) {
    const ids = row.artifact_ids ?? [];
    if (ids.some((id) => !artifactById.has(id))) return false;
    if (
      row.status === "VERIFIED_RETAINED_BYTES" &&
      (!ids.length ||
        ids.some((id) => artifactById.get(id) !== "VERIFIED_RETAINED_BYTES"))
    )
      return false;
    if (
      row.status === "RETAINED_BYTES_UNAVAILABLE" &&
      (!ids.length ||
        ids.every((id) => artifactById.get(id) === "VERIFIED_RETAINED_BYTES"))
    )
      return false;
    if (
      [
        "NO_RETAINED_ORIGINAL_REFERENCED",
        "METADATA_UNAVAILABLE",
        "NOT_RECHECKED",
      ].includes(row.status) &&
      ids.length
    )
      return false;
    ids.forEach((id) => citedIds.add(id));
  }
  if (
    citedIds.size !== artifactById.size ||
    [...artifactById.keys()].some((id) => !citedIds.has(id))
  )
    return false;
  if (report.counts === null) {
    return (
      ["METADATA_UNAVAILABLE", "RECHECK_INPUT_UNAVAILABLE"].includes(
        report.status,
      ) &&
      report.artifacts.length === 0 &&
      report.traces.every((row) => row.status === "NOT_RECHECKED")
    );
  }
  const counts = report.counts;
  if (!counts || typeof counts !== "object") return false;
  if (
    [
      counts.referenced,
      counts.verified,
      counts.missing,
      counts.integrity_failure,
      counts.read_unavailable,
    ].some((value) => !Number.isSafeInteger(value) || value < 0) ||
    counts.referenced !== report.artifacts.length ||
    counts.referenced !==
      counts.verified +
        counts.missing +
        counts.integrity_failure +
        counts.read_unavailable ||
    counts.verified !==
      report.artifacts.filter((row) => row.status === "VERIFIED_RETAINED_BYTES")
        .length ||
    counts.missing !==
      report.artifacts.filter((row) => row.status === "MISSING_RETAINED_BYTES")
        .length ||
    counts.integrity_failure !==
      report.artifacts.filter(
        (row) => row.status === "RETAINED_BYTE_INTEGRITY_FAILURE",
      ).length ||
    counts.read_unavailable !==
      report.artifacts.filter(
        (row) => row.status === "RETAINED_BYTE_READ_UNAVAILABLE",
      ).length
  )
    return false;
  if (report.status === "VERIFIED_RETAINED_BYTES_ONLY") {
    return (
      report.metadata_status === "AVAILABLE" &&
      counts.referenced > 0 &&
      counts.verified === counts.referenced &&
      report.traces.length > 0 &&
      report.traces.every((row) =>
        ["VERIFIED_RETAINED_BYTES", "NO_RETAINED_ORIGINAL_REFERENCED"].includes(
          row.status,
        ),
      ) &&
      report.traces.some((row) => row.status === "VERIFIED_RETAINED_BYTES")
    );
  }
  if (report.status === "NO_RECORDED_TRACES")
    return (
      report.metadata_status === "AVAILABLE" &&
      counts.referenced === 0 &&
      report.traces.length === 0
    );
  if (report.status === "NO_RETAINED_ORIGINAL_REFERENCED")
    return (
      report.metadata_status === "AVAILABLE" &&
      counts.referenced === 0 &&
      report.traces.length > 0 &&
      report.traces.every(
        (row) => row.status === "NO_RETAINED_ORIGINAL_REFERENCED",
      )
    );
  return report.status === "PARTIAL_UNAVAILABLE";
}

export function traceIntegrity(
  report: OriginalIntegrity | undefined,
  id: string,
) {
  if (!report) return null;
  const rows = report.traces.filter((row) => row.id === id);
  return rows.length === 1 ? rows[0] : null;
}

export const integrityStatusLabels: Record<string, string> = {
  VERIFIED_RETAINED_BYTES_ONLY:
    "Cited retained bytes match their recorded size and hash.",
  VERIFIED_RETAINED_BYTES: "Retained bytes match the recorded size and hash.",
  PARTIAL_UNAVAILABLE:
    "At least one cited copy or trace could not be verified.",
  NO_RECORDED_TRACES: "No procedure trace is recorded.",
  NO_RETAINED_ORIGINAL_REFERENCED:
    "The recorded trace cites no retained original.",
  METADATA_UNAVAILABLE: "Trace metadata or correction lineage is unavailable.",
  RECHECK_INPUT_UNAVAILABLE:
    "The bounded recheck could not run; no byte result is accepted.",
  NOT_RECHECKED: "This trace was not rechecked.",
  RETAINED_BYTES_UNAVAILABLE:
    "One or more cited retained copies could not be verified.",
  MISSING_RETAINED_BYTES: "The cited retained copy is missing.",
  RETAINED_BYTE_INTEGRITY_FAILURE:
    "The cited retained copy differs in size or hash.",
  RETAINED_BYTE_READ_UNAVAILABLE: "The cited retained copy could not be read.",
};
