import type { Engagement, Row } from "./api";

const kinds = {
  artifacts: "artifact",
  workpapers: "workpaper",
  populations: "population",
  selections: "selection",
  tasks: "task",
} as const;

/** Resolve only explicit links in the currently authorized workspace snapshot. */
export function sourceReference(e: Engagement, ref: Row) {
  if (
    typeof ref.collection !== "string" ||
    !Object.hasOwn(kinds, ref.collection)
  )
    return null;
  const collection = ref.collection as keyof typeof kinds;
  const rows = e[collection].filter((row) => row.id === ref.id);
  if (rows.length !== 1) return null;
  const row = rows[0];
  if (ref.version !== undefined) {
    const versions = collection === "workpapers" ? row.versions : [row];
    if (
      !Array.isArray(versions) ||
      !versions.some((v: Row) => v.version === ref.version)
    )
      return null;
  }
  return { kind: kinds[collection], row };
}
