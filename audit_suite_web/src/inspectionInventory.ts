import type { Row } from "./api";
export type InspectionInventory = {
  status: "SELF_REPORTED_INSPECTION";
  records: Row[];
  audited_actor_count: number;
  other_actor_count: number;
  unresolved_record_count: number;
  qualification: "AUTHOR_ASSERTION_NOT_VERIFIED_READING_UNDERSTANDING_TESTING_OR_GRADE";
  absence: "NO_RECORDED_ASSERTION_DOES_NOT_ESTABLISH_NO_INSPECTION";
};
export function inspectionInventory(
  value: unknown,
  revision: number,
  actor: string,
): InspectionInventory | null {
  if (value === undefined || typeof value === "string") return null; // Older server has no inspection records.
  const v = value as InspectionInventory;
  const invalid = () => {
    throw Error("Inspection links do not match the selected history.");
  };
  if (
    !v ||
    v.status !== "SELF_REPORTED_INSPECTION" ||
    !Array.isArray(v.records) ||
    v.records.length > 10000 ||
    v.qualification !==
      "AUTHOR_ASSERTION_NOT_VERIFIED_READING_UNDERSTANDING_TESTING_OR_GRADE" ||
    v.absence !== "NO_RECORDED_ASSERTION_DOES_NOT_ESTABLISH_NO_INSPECTION"
  )
    return invalid();
  if (
    ![
      v.audited_actor_count,
      v.other_actor_count,
      v.unresolved_record_count,
    ].every((n) => Number.isSafeInteger(n) && n >= 0)
  )
    return invalid();
  const ids = new Set<string>();
  for (const row of v.records) {
    if (
      !row ||
      typeof row.id !== "string" ||
      !row.id ||
      ids.has(row.id) ||
      row.classification !== "SELF_REPORTED_INSPECTION" ||
      typeof row.artifact_id !== "string" ||
      typeof row.actor !== "string" ||
      !row.actor ||
      typeof row.locator !== "string" ||
      typeof row.observation !== "string" ||
      ![row.sha256, row.history_sha256].every(
        (pin) => typeof pin === "string" && /^[a-f0-9]{64}$/.test(pin),
      ) ||
      !Number.isSafeInteger(row.recorded_revision) ||
      Number(row.recorded_revision) < 0 ||
      Number(row.recorded_revision) > revision ||
      (row.version !== null &&
        (!Number.isSafeInteger(row.version) || Number(row.version) < 0)) ||
      row.attribution !==
        (row.actor === actor ? "AUDITED_ACTOR" : "OTHER_ACTOR")
    )
      return invalid();
    ids.add(row.id);
  }
  if (
    v.audited_actor_count !==
      v.records.filter((row) => row.actor === actor).length ||
    v.other_actor_count !==
      v.records.filter((row) => row.actor !== actor).length
  )
    return invalid();
  return v;
}
