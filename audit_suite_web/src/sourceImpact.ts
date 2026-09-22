import type { Engagement, Row } from "./api";
export type ImpactReport = {
  engagement_id: string;
  engagement_revision: number;
  changes: Row[];
  unavailable_comparisons: number;
  compared_artifacts: number;
  simulated_as_of: string;
  snapshot_isolation: string;
  limitations: string[];
  started_at: string;
  completed_at: string;
};
export function impactContext(e: Engagement): string {
  return JSON.stringify([
    e.id,
    e.revision,
    e.scope,
    e.permissions,
    e.company_source_binding,
    e.evidence_acquisition,
    e.simulated_at,
  ]);
}
export function validateImpact(
  value: ImpactReport,
  e: Engagement,
): ImpactReport {
  if (
    value.engagement_id !== e.id ||
    value.engagement_revision !== e.revision ||
    value.simulated_as_of !== e.simulated_at
  )
    throw Error(
      "Source comparison is outdated or belongs to another engagement. Check again.",
    );
  if (
    !Array.isArray(value.changes) ||
    !Number.isSafeInteger(value.compared_artifacts) ||
    value.compared_artifacts < 0 ||
    !Number.isSafeInteger(value.unavailable_comparisons) ||
    value.unavailable_comparisons < 0 ||
    value.changes.length > value.compared_artifacts
  )
    throw Error("Source comparison counts are invalid.");
  if (
    value.changes.some(
      (r) =>
        !e.artifacts.some((a) => a.id === r.artifact_id) ||
        !Array.isArray(r.references),
    )
  )
    throw Error("Source comparison references are outside this workspace.");
  return value;
}

function rows(value: unknown): Row[] {
  return Array.isArray(value)
    ? value.filter((r): r is Row => Boolean(r) && typeof r === "object")
    : [];
}
function exactRow(value: unknown, id: unknown): Row | null {
  const found = rows(value).filter((row) => row.id === id);
  return found.length === 1 ? found[0] : null;
}
function same(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (!a || !b || typeof a !== "object" || typeof b !== "object") return false;
  const left = Object.keys(a).sort(),
    right = Object.keys(b).sort();
  return (
    left.length === right.length &&
    left.every((k, i) => k === right[i] && same((a as Row)[k], (b as Row)[k]))
  );
}
function samePin(a: unknown, b: unknown): boolean {
  return typeof a === "string" && /^[0-9a-f]{64}$/.test(a) && a === b;
}
export type ImpactTarget = {
  kind: string;
  row: Row;
  reference: Row;
  item?: Row;
  workpaper?: { row: Row; version: number };
};
/** Server verifies canonical digests; UI preserves those pins without recomputing Python JSON. */
export function impactReference(
  e: Engagement,
  ref: Row,
  artifactId: string,
): ImpactTarget | null {
  if (ref.collection === "sample_executions") {
    const trace = exactRow(e.sample_executions, ref.id);
    const artifact = exactRow(e.artifacts, artifactId);
    const item = rows(trace?.items).filter((r) => r.item_id === ref.item_id);
    if (
      !trace ||
      !artifact ||
      item.length !== 1 ||
      trace.revision !== ref.version ||
      !Number.isSafeInteger(ref.version) ||
      trace.predecessor_id !== ref.predecessor_id ||
      artifact.sha256 !== ref.artifact_sha256 ||
      !rows(item[0].evidence).some(
        (r) => r.artifact_id === artifactId && r.sha256 === ref.artifact_sha256,
      )
    )
      return null;
    const successors = rows(e.sample_executions).filter(
      (r) => r.predecessor_id === trace.id,
    );
    if (
      successors.length > 1 ||
      (successors[0]?.id ?? null) !== (ref.successor_id ?? null)
    )
      return null;
    return {
      kind: "sample_execution",
      row: trace,
      reference: ref,
      item: item[0],
    };
  }
  if (ref.collection === "reviews") {
    const review = exactRow(e.reviews, ref.id),
      paper = exactRow(e.workpapers, ref.workpaper_id);
    const versions = rows(paper?.versions).filter(
      (r) => r.version === ref.version,
    );
    if (
      !review ||
      !paper ||
      versions.length !== 1 ||
      review.kind !== "HUMAN" ||
      !Number.isSafeInteger(ref.version) ||
      review.workpaper_id !== paper.id ||
      review.workpaper_version !== ref.version ||
      review.workpaper_version_digest !== ref.workpaper_version_digest ||
      !same(review.anchor, ref.anchor)
    )
      return null;
    if (ref.anchor) {
      const anchor = ref.anchor as Row,
        field = anchor.field;
      const text = typeof field === "string" ? versions[0][field] : undefined;
      if (
        typeof text !== "string" ||
        anchor.offset_unit !== "UNICODE_CODEPOINT" ||
        !Number.isSafeInteger(anchor.start) ||
        !Number.isSafeInteger(anchor.end) ||
        (anchor.start as number) < 0 ||
        (anchor.end as number) <= (anchor.start as number) ||
        Array.from(text)
          .slice(anchor.start as number, anchor.end as number)
          .join("") !== anchor.excerpt
      )
        return null;
    }
    return {
      kind: "review",
      row: review,
      reference: ref,
      workpaper: { row: paper, version: ref.version as number },
    };
  }
  if (ref.collection === "findings") {
    const finding = exactRow(e.findings, ref.id);
    if (!finding) return null;
    const source = ref.remediation_id
      ? exactRow(finding.remediations, ref.remediation_id)
      : finding;
    if (
      !source ||
      !Array.isArray(source.evidence_ids) ||
      !source.evidence_ids.includes(artifactId)
    )
      return null;
    return { kind: "finding", row: finding, reference: ref };
  }
  const collection = ref.collection;
  const kinds: Record<string, string> = {
    artifacts: "artifact",
    workpapers: "workpaper",
    tasks: "task",
    populations: "population",
    selections: "selection",
  };
  if (typeof collection !== "string" || !Object.hasOwn(kinds, collection))
    return null;
  const row = exactRow(e[collection], ref.id);
  if (!row || (ref.sha256 !== undefined && row.sha256 !== ref.sha256))
    return null;
  if (ref.version !== undefined) {
    if (
      !Number.isSafeInteger(ref.version) ||
      (collection === "workpapers"
        ? rows(row.versions).filter((v) => v.version === ref.version).length !==
          1
        : row.version !== ref.version)
    )
      return null;
  }
  return { kind: kinds[collection], row, reference: ref };
}

/** Resolve trace relationships only through server-issued current exact input pins. */
export function impactTraceLinks(e: Engagement, trace: Row): Row[] {
  const inputs = e.sample_execution_inputs as Row | undefined;
  if (!inputs || inputs.status !== "AVAILABLE") return [];
  const links: Row[] = [];
  const tasks = rows(inputs.tasks).filter(
    (r) =>
      r.task_id === trace.task_id && samePin(r.task_digest, trace.task_digest),
  );
  if (tasks.length === 1)
    links.push({ id: String(trace.task_id), collection: "tasks" });
  const selections = rows(inputs.selections).filter(
    (r) =>
      r.selection_id === trace.selection_id &&
      samePin(r.selection_digest, trace.selection_digest) &&
      r.population_id === trace.population_id &&
      samePin(r.population_digest, trace.population_digest),
  );
  if (selections.length === 1) {
    links.push({ id: String(trace.selection_id), collection: "selections" });
    links.push({
      id: String(trace.population_id),
      collection: "populations",
      version: selections[0].population_version,
    });
  }
  const papers = rows(inputs.workpaper_versions).filter(
    (r) =>
      r.workpaper_id === trace.workpaper_id &&
      r.workpaper_version === trace.workpaper_version &&
      samePin(r.workpaper_digest, trace.workpaper_digest),
  );
  if (papers.length === 1)
    links.push({
      id: String(trace.workpaper_id),
      collection: "workpapers",
      version: trace.workpaper_version,
    });
  return links;
}
