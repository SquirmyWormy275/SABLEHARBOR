import type { Engagement, Row } from "./api";
import type { BoundSource } from "./boundInstructorKey";

/** Only current authorized retained copies of this exact bound original; never fetch native sources. */
export function boundRetainedArtifacts(
  e: Engagement,
  source: BoundSource,
): Row[] {
  if (!e.permissions?.includes("instruct")) return [];
  const routed = [
    source.source_store_id,
    source.source_system_alias,
    source.registry_sha256,
  ];
  if (
    routed.some((value) => value !== undefined) &&
    (!routed.every((value) => typeof value === "string" && value.length > 0) ||
      !/^[a-f0-9]{64}$/.test(source.registry_sha256 ?? ""))
  )
    return [];
  return source.retained_audit_artifact_ids.flatMap((id) => {
    const candidates = e.artifacts.filter((a) => a.id === id);
    if (candidates.length !== 1) return [];
    const artifact = candidates[0];
    const origin = artifact.source as
      | {
          kind?: string;
          receipt?: {
            engagement_id?: string;
            source?: Record<string, unknown>;
          };
        }
      | undefined;
    const physical = origin?.receipt?.source;
    if (
      artifact.status !== "AVAILABLE" ||
      artifact.sha256 !== source.sha256 ||
      (artifact.engagement_id !== undefined &&
        artifact.engagement_id !== e.id) ||
      origin?.kind !== "COLLECTED_COMPANY_SOURCE" ||
      origin.receipt?.engagement_id !== e.id ||
      !physical ||
      ["company", "branch", "system", "record", "version", "sha256"].some(
        (key) => physical[key] !== source[key as keyof BoundSource],
      ) ||
      ["source_store_id", "source_system_alias", "registry_sha256"].some(
        (key) => physical[key] !== source[key as keyof BoundSource],
      )
    )
      return [];
    return [artifact];
  });
}
