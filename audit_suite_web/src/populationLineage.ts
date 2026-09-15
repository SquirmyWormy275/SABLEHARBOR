import type { Engagement, Row } from "./api";
import { sourceReference } from "./sourceReferences";
export function lineageReference(e: Engagement, ref: Row) {
  const target = sourceReference(e, ref);
  return target &&
    (target.kind !== "artifact" || target.row.status === "AVAILABLE")
    ? target
    : null;
}
export type LineageLink = { label: string; reference: Row };
function object(value: unknown): Record<string, unknown> {
  if (value && typeof value === "object" && !Array.isArray(value))
    return value as Record<string, unknown>;
  return {};
}
function source(row: Row) {
  try {
    return object(
      JSON.parse(
        String(object(row.immutable).source_json ?? row.source_json ?? "{}"),
      ),
    );
  } catch {
    return {};
  }
}
export function populationLineage(
  e: Engagement,
  kind: string,
  row: Row,
): {
  population: Row | null;
  links: LineageLink[];
  unavailable: string[];
  workpaperLinks: number;
} {
  const links: LineageLink[] = [],
    unavailable: string[] = [];
  let population: Row | null = null;
  if (kind === "population")
    population =
      e.populations.find((p) => p.id === row.id && p.version === row.version) ??
      null;
  else if (kind === "selection") {
    const version =
      row.population_version ?? object(row.immutable).population_version;
    const candidates = e.populations.filter(
      (p) => p.id === row.population_id && p.version === version,
    );
    if (candidates.length === 1) population = candidates[0];
    if (!population)
      unavailable.push(
        `The exact population ${String(row.population_id)} version ${String(version ?? "not recorded")} is unavailable; no current version was substituted.`,
      );
  }
  if (!population)
    return { population: null, links, unavailable, workpaperLinks: 0 };
  const add = (label: string, reference: Row) => {
    if (lineageReference(e, reference)) links.push({ label, reference });
    else
      unavailable.push(
        `${label} is unavailable at its recorded version or hash.`,
      );
  };
  if (kind === "selection")
    add(
      `Open population ${population.id} version ${String(population.version)}`,
      {
        id: population.id,
        collection: "populations",
        version: population.version,
      },
    );
  const provenance = source(population),
    original = population.artifact_id;
  const pinnedOriginal =
    typeof provenance.original_sha256 === "string" &&
    typeof original === "string"
      ? {
          id: original,
          collection: "artifacts",
          sha256: provenance.original_sha256,
        }
      : null;
  if (pinnedOriginal)
    add(`Open pinned population original ${original}`, pinnedOriginal);
  else
    unavailable.push(
      "The population original has no recorded hash pin; no unpinned original link is substituted.",
    );
  if (provenance.query_manifest_artifact_id) {
    if (typeof provenance.query_manifest_sha256 === "string")
      add(
        `Open pinned query manifest ${provenance.query_manifest_artifact_id}`,
        {
          id: String(provenance.query_manifest_artifact_id),
          collection: "artifacts",
          sha256: provenance.query_manifest_sha256,
        },
      );
    else unavailable.push("The query manifest has no recorded hash pin.");
  }
  if (kind === "population")
    for (const selected of e.selections)
      if (
        selected.population_id === population.id &&
        selected.population_version === population.version
      )
        add(`Open selection ${selected.id}`, {
          id: selected.id,
          collection: "selections",
        });
  let workpaperLinks = 0;
  // Exact source-ID links are associations with this original, not proof selected items were tested.
  if (pinnedOriginal && lineageReference(e, pinnedOriginal))
    for (const paper of e.workpapers)
      for (const version of Array.isArray(paper.versions)
        ? (paper.versions as Row[])
        : []) {
        if (
          version.artifact_id === original ||
          (Array.isArray(version.evidence_ids) &&
            version.evidence_ids.includes(original))
        ) {
          add(`Open workpaper ${paper.id} version ${String(version.version)}`, {
            id: paper.id,
            collection: "workpapers",
            version: version.version,
          });
          workpaperLinks++;
        }
      }
  return { population, links, unavailable, workpaperLinks };
}
