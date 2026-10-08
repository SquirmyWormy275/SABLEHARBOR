export type ReferenceStatus =
  "EXACT" | "SHARED_CONTROL_ONLY" | "OUT_OF_SCOPE" | "UNRESOLVED";
export type ReferenceCrosswalkValue = {
  schema: "SH_PRIVATE_INSTRUCTOR_REFERENCE_CROSSWALK_V1";
  projection: "DECLARED_NAVIGATION_ONLY";
  sha256: string;
  engagement_id: string;
  archive_sha256: string;
  professional_acceptance: "NOT_ASSERTED";
  current_cards: {
    id: string;
    sha256: string;
    control_ids: string[];
    task_ids: string[];
  }[];
  rows: {
    legacy_id: string;
    raw_sha256: string;
    canonical_sha256: string;
    key_sha256: string;
    relations: {
      current_id: string | null;
      status: ReferenceStatus;
      reason: string;
      proof: { legacy_pointer: string; current_pointer: string } | null;
    }[];
  }[];
  inverse: {
    current_id: string;
    legacy_ids: string[];
    unmapped_reason: string | null;
  }[];
};
export function validateReferenceCrosswalk(
  value: ReferenceCrosswalkValue,
  engagement: string,
  archive?: string,
) {
  const statuses = [
    "EXACT",
    "SHARED_CONTROL_ONLY",
    "OUT_OF_SCOPE",
    "UNRESOLVED",
  ];
  if (
    value.schema !== "SH_PRIVATE_INSTRUCTOR_REFERENCE_CROSSWALK_V1" ||
    value.projection !== "DECLARED_NAVIGATION_ONLY" ||
    value.engagement_id !== engagement ||
    value.professional_acceptance !== "NOT_ASSERTED" ||
    !/^[a-f0-9]{64}$/.test(value.sha256) ||
    !/^[a-f0-9]{64}$/.test(value.archive_sha256) ||
    (archive !== undefined && archive !== value.archive_sha256) ||
    !Array.isArray(value.current_cards) ||
    !Array.isArray(value.rows) ||
    !Array.isArray(value.inverse)
  )
    throw Error("Reference crosswalk differs from the protected context.");
  const current = new Set(value.current_cards.map((c) => c.id));
  const legacy = new Set(value.rows.map((r) => r.legacy_id));
  if (
    current.size !== value.current_cards.length ||
    legacy.size !== value.rows.length ||
    value.inverse.length !== current.size ||
    new Set(value.inverse.map((i) => i.current_id)).size !== current.size ||
    value.current_cards.some(
      (c) =>
        !c.id ||
        !/^[a-f0-9]{64}$/.test(c.sha256) ||
        !Array.isArray(c.control_ids) ||
        !Array.isArray(c.task_ids),
    ) ||
    value.rows.some(
      (r) =>
        !r.legacy_id ||
        [r.raw_sha256, r.canonical_sha256, r.key_sha256].some(
          (s) => !/^[a-f0-9]{64}$/.test(s),
        ) ||
        !Array.isArray(r.relations) ||
        !r.relations.length ||
        r.relations.some(
          (x) =>
            !statuses.includes(x.status) ||
            !x.reason?.trim() ||
            (x.status === "UNRESOLVED"
              ? x.proof !== null
              : !x.proof ||
                !x.proof.legacy_pointer?.startsWith("/") ||
                !x.proof.current_pointer?.startsWith("/")) ||
            (x.current_id !== null && !current.has(x.current_id)),
        ),
    ) ||
    value.inverse.some(
      (i) =>
        !current.has(i.current_id) ||
        !Array.isArray(i.legacy_ids) ||
        i.legacy_ids.some((id) => !legacy.has(id)) ||
        JSON.stringify([...i.legacy_ids].sort()) !==
          JSON.stringify(
            value.rows
              .filter((r) =>
                r.relations.some((x) => x.current_id === i.current_id),
              )
              .map((r) => r.legacy_id)
              .sort(),
          ),
    )
  )
    throw Error("Reference crosswalk inventory or inverse links differ.");
}
