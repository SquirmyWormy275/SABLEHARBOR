import type { Engagement, Row } from "./api";
import { record } from "./workpaperSupport";
export type OriginalPair = readonly [string, string];
export function comparisonContext(e: Engagement, viewer: string): string {
  return JSON.stringify([
    viewer,
    e.id,
    e.permissions,
    e.scope,
    e.company_source_binding,
    e.evidence_acquisition,
    e.simulated_at,
  ]);
}
export function comparisonArtifact(e: Engagement, id: string): Row | undefined {
  const rows = e.artifacts.filter((a) => a.id === id);
  const a = rows[0];
  return rows.length === 1 && availableArtifact(e, a) ? a : undefined;
}
function availableArtifact(e: Engagement, a: Row): boolean {
  return (
    a.status === "AVAILABLE" &&
    (a.engagement_id === undefined || a.engagement_id === e.id) &&
    typeof a.sha256 === "string" &&
    /^[a-f0-9]{64}$/.test(a.sha256)
  );
}
export function comparisonPin(
  e: Engagement,
  viewer: string,
  id: string,
): string {
  const a = comparisonArtifact(e, id);
  return JSON.stringify([
    comparisonContext(e, viewer),
    e.revision,
    id,
    a?.sha256,
    a?.version,
    a?.bytes,
    a?.mime,
    a?.source,
    a?.coverage,
  ]);
}
export function acceptsComparison(
  pin: string,
  e: Engagement,
  viewer: string,
  id: string,
): boolean {
  return !!comparisonArtifact(e, id) && comparisonPin(e, viewer, id) === pin;
}
export function originalIdentity(a: Row): {
  native: Record<string, unknown>;
  routeStatus: string;
} {
  const native = record(record(record(a.source).receipt).source);
  const keys = ["source_store_id", "source_system_alias", "registry_sha256"];
  const present = keys.filter((k) => native[k] !== undefined);
  const complete =
    present.length === 3 &&
    keys.every((k) => typeof native[k] === "string" && native[k]) &&
    /^[a-f0-9]{64}$/.test(String(native.registry_sha256));
  return {
    native,
    routeStatus:
      present.length === 0
        ? "No portfolio route recorded"
        : complete
          ? "Complete recorded portfolio route"
          : "Incomplete portfolio route — provenance comparison unavailable",
  };
}

/** Bounded discovery never substitutes the selected exact original. */
export function comparisonOptions(
  e: Engagement,
  query: string,
  selectedId: string,
) {
  const counts = new Map<string, number>();
  for (const a of e.artifacts) counts.set(a.id, (counts.get(a.id) ?? 0) + 1);
  const available = e.artifacts.filter(
    (a) => counts.get(a.id) === 1 && availableArtifact(e, a),
  );
  const q = query.trim().toLocaleLowerCase();
  const matches = available.filter((a) => {
    const { native } = originalIdentity(a);
    return [
      a.id,
      a.name,
      native.company,
      native.branch,
      native.system,
      native.record,
      native.version,
      native.source_store_id,
      native.source_system_alias,
    ].some((v) =>
      String(v ?? "")
        .toLocaleLowerCase()
        .includes(q),
    );
  });
  const options = matches.slice(0, 50),
    selected = comparisonArtifact(e, selectedId);
  if (selected && !options.some((a) => a.id === selected.id))
    options.unshift(selected);
  return { options, total: matches.length };
}
