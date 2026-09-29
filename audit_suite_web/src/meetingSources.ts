import type { Row } from "./api";
export type SourcePin = {
  system_id: string;
  record_id: string;
  version: number;
  sha256: string;
};
export function ownedSystems(systems: Row[], person: string): Row[] {
  return systems.filter(
    (s) => s.owner === person && typeof s.system === "string",
  );
}
export function sourcePin(
  row: Row,
  alias: string,
  registry: string,
): SourcePin | null {
  if (
    typeof row.record !== "string" ||
    !row.record ||
    !Number.isSafeInteger(row.version) ||
    Number(row.version) < 1 ||
    typeof row.sha256 !== "string" ||
    !/^[a-f0-9]{64}$/.test(row.sha256)
  )
    return null;
  if (
    registry &&
    (row.registry_sha256 !== registry || row.source_system_alias !== alias)
  )
    return null;
  return {
    system_id: alias,
    record_id: row.record,
    version: Number(row.version),
    sha256: row.sha256,
  };
}
export function samePins(a: SourcePin[], b: SourcePin[]): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}
export function addSourcePin(pins: SourcePin[], pin: SourcePin): SourcePin[] {
  if (
    pins.some(
      (p) => p.system_id === pin.system_id && p.record_id === pin.record_id,
    )
  )
    throw Error(
      "Remove the existing version of this record before selecting another.",
    );
  if (pins.length >= 4) throw Error("Select at most four source records.");
  return [...pins, { ...pin }];
}
