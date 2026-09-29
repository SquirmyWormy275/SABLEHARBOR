import type { Engagement, Row } from "./api";
import type { SourcePin } from "./meetingSources";
/** Match retained originals by explicit physical identity/version/hash, never narrative. */
export function retainedPinArtifacts(
  e: Pick<Engagement, "id" | "artifacts">,
  pin: SourcePin,
): Row[] {
  return e.artifacts.filter((a) => {
    const source = a.source as
      | {
          kind?: string;
          receipt?: {
            engagement_id?: string;
            source?: Record<string, unknown>;
          };
        }
      | undefined;
    const receipt = source?.receipt,
      physical = receipt?.source;
    return (
      source?.kind === "COLLECTED_COMPANY_SOURCE" &&
      receipt?.engagement_id === e.id &&
      a.status === "AVAILABLE" &&
      a.sha256 === pin.sha256 &&
      physical?.sha256 === pin.sha256 &&
      physical?.record === pin.record_id &&
      physical?.version === pin.version &&
      (physical?.source_system_alias ?? physical?.system) === pin.system_id
    );
  });
}
