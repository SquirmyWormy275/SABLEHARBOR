import type { Engagement } from "./api";
const collections = {
  control: "controls",
  task: "tasks",
  request: "requests",
  artifact: "artifacts",
  person: "people",
  population: "populations",
  selection: "selections",
  finding: "findings",
  workpaper: "workpapers",
  review: "reviews",
} as const;
/** Preserve inspected list order, resolving every identifier against current authorized rows. */
export function recordSequence(
  e: Engagement,
  kind: string,
  ids: string[],
  current: string,
) {
  if (
    !Object.hasOwn(collections, kind) ||
    ids.length > 10000 ||
    new Set(ids).size !== ids.length
  )
    return null;
  const source = e[collections[kind as keyof typeof collections]];
  const rows = ids.flatMap((id) => {
    const matches = source.filter((row) => row.id === id);
    return matches.length === 1 ? matches : [];
  });
  const at = rows.findIndex((row) => row.id === current);
  return at < 0
    ? null
    : {
        total: rows.length,
        position: at + 1,
        previous: rows[at - 1],
        next: rows[at + 1],
      };
}
