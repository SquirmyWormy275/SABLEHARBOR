import type { Engagement, Row } from "./api";
import type { EvidenceContextReference } from "./evidenceContext";
import { ITEM_STATUSES } from "./sampleExecution";
type ObjectRow = Record<string, unknown>;
const object = (v: unknown): ObjectRow =>
  v && typeof v === "object" && !Array.isArray(v) ? (v as ObjectRow) : {};
const string = (v: unknown) => (typeof v === "string" ? v : "");
const positive = (v: unknown): v is number =>
  Number.isSafeInteger(v) && Number(v) > 0;
export type SampleObservation = {
  traceId: string;
  revision: number;
  itemId: string;
  status: string;
  observation: string;
  locators: string[];
  taskId: string;
  taskDigest: string;
  workpaperId: string;
  workpaperVersion: number;
  workpaperDigest: string;
  selectionId: string;
  populationId: string;
  populationStatus: string;
  basis: string;
  actor: string;
  recordedAt: string;
  purpose: string;
  procedure: string;
  correctionRationale: string;
  predecessorId: string;
  successors: { id: string; revision: number; citesOriginal: boolean }[];
  artifactId: string;
  artifactSha256: string;
};
export function sampleOriginalContext(
  e: Engagement,
  artifactId: string,
): { rows: SampleObservation[]; unavailable: boolean } {
  const artifacts = e.artifacts.filter((a) => a.id === artifactId);
  if (
    !e.permissions?.some((r) => ["learn", "review", "instruct"].includes(r)) ||
    artifacts.length !== 1 ||
    artifacts[0].status !== "AVAILABLE" ||
    typeof artifacts[0].sha256 !== "string"
  )
    return { rows: [], unavailable: true };
  const hash = artifacts[0].sha256,
    raw = e.sample_executions;
  if (raw === undefined) return { rows: [], unavailable: false };
  if (!Array.isArray(raw) || raw.length > 10000)
    return { rows: [], unavailable: true };
  const traces = raw.map(object),
    counts = new Map<string, number>(),
    successors = new Map<string, ObjectRow[]>();
  let examined = 0;
  for (const t of traces) {
    const id = string(t.id);
    counts.set(id, (counts.get(id) ?? 0) + 1);
    if (typeof t.predecessor_id === "string")
      successors.set(t.predecessor_id, [
        ...(successors.get(t.predecessor_id) ?? []),
        t,
      ]);
    examined += Array.isArray(t.items) ? t.items.length : 0;
  }
  // A marked unavailable index is preferable to an unmarked partial scan.
  if (examined > 250000) return { rows: [], unavailable: true };
  const supports = (item: ObjectRow) =>
    Array.isArray(item.evidence)
      ? item.evidence
          .map(object)
          .filter(
            (r) =>
              r.artifact_id === artifactId &&
              r.sha256 === hash &&
              typeof r.locator === "string",
          )
      : [];
  const cites = (t: ObjectRow) =>
    Array.isArray(t.items) &&
    t.items.some((i) => supports(object(i)).length > 0);
  const rows: SampleObservation[] = [];
  let unavailable = false;
  for (const t of traces) {
    if (
      !string(t.id) ||
      counts.get(string(t.id)) !== 1 ||
      !positive(t.revision) ||
      !Array.isArray(t.items)
    ) {
      unavailable = true;
      continue;
    }
    const ids = new Map<string, number>();
    for (const i of t.items) {
      const id = string(object(i).item_id);
      ids.set(id, (ids.get(id) ?? 0) + 1);
    }
    for (const value of t.items) {
      const i = object(value),
        refs = supports(i);
      if (!refs.length) continue;
      if (
        !string(i.item_id) ||
        ids.get(string(i.item_id)) !== 1 ||
        !ITEM_STATUSES.includes(i.status as (typeof ITEM_STATUSES)[number]) ||
        typeof i.observation !== "string" ||
        !positive(t.workpaper_version)
      ) {
        unavailable = true;
        continue;
      }
      rows.push({
        traceId: string(t.id),
        revision: t.revision,
        itemId: string(i.item_id),
        status: string(i.status),
        observation: i.observation,
        locators: refs.map((r) => string(r.locator)),
        taskId: string(t.task_id),
        taskDigest: string(t.task_digest),
        workpaperId: string(t.workpaper_id),
        workpaperVersion: t.workpaper_version,
        workpaperDigest: string(t.workpaper_digest),
        selectionId: string(t.selection_id),
        populationId: string(t.population_id),
        populationStatus: string(t.population_status),
        basis: string(i.selection_basis),
        actor: string(t.actor),
        recordedAt: string(t.recorded_at),
        purpose: string(t.purpose),
        procedure: string(t.procedure),
        correctionRationale: string(t.correction_rationale),
        predecessorId: string(t.predecessor_id),
        successors: (successors.get(string(t.id)) ?? [])
          .filter((v) => counts.get(string(v.id)) === 1 && positive(v.revision))
          .map((v) => ({
            id: string(v.id),
            revision: Number(v.revision),
            citesOriginal: cites(v),
          })),
        artifactId,
        artifactSha256: hash,
      });
      if (rows.length > 20000) return { rows: [], unavailable: true };
    }
  }
  return { rows, unavailable };
}
export function sampleObservationReference(
  e: Engagement,
  r: SampleObservation,
  kind: "task" | "workpaper",
): EvidenceContextReference | null {
  const a = e.artifacts.filter(
    (a) =>
      a.id === r.artifactId &&
      a.status === "AVAILABLE" &&
      a.sha256 === r.artifactSha256,
  );
  if (
    a.length !== 1 ||
    !e.permissions?.some((p) => ["learn", "review", "instruct"].includes(p))
  )
    return null;
  const pins = object(e.sample_execution_inputs);
  if (pins.engagement_id !== e.id || pins.engagement_revision !== e.revision)
    return null;
  if (kind === "task") {
    const matches = (Array.isArray(pins.tasks) ? pins.tasks : [])
      .map(object)
      .filter((p) => p.task_id === r.taskId && p.task_digest === r.taskDigest);
    if (
      matches.length === 1 &&
      e.tasks.filter((t) => t.id === r.taskId).length === 1
    )
      return { collection: "tasks", id: r.taskId };
  } else {
    const matches = (
      Array.isArray(pins.workpaper_versions) ? pins.workpaper_versions : []
    )
      .map(object)
      .filter(
        (p) =>
          p.workpaper_id === r.workpaperId &&
          p.workpaper_version === r.workpaperVersion &&
          p.workpaper_digest === r.workpaperDigest,
      );
    const papers = e.workpapers.filter((w) => w.id === r.workpaperId);
    if (
      matches.length === 1 &&
      papers.length === 1 &&
      Array.isArray(papers[0].versions) &&
      papers[0].versions.filter((v: Row) => v.version === r.workpaperVersion)
        .length === 1
    )
      return {
        collection: "workpapers",
        id: r.workpaperId,
        version: r.workpaperVersion,
      };
  }
  return null;
}
