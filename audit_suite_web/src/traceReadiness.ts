import type { Engagement, Row } from "./api";
import { investigationKinds, type ContextLink } from "./investigationContext";

export type Trace = {
  id: string;
  digest?: string;
  revision?: number;
  status: string;
  reason_codes: string[];
  exact_refs?: ContextLink[];
  recorded_item_status_counts?: Record<string, number>;
  selected_item_count?: number;
  items_with_no_recorded_observation_count?: number;
  population_reliability?: Record<string, unknown>;
  period_qualification?: Record<string, unknown>;
};
export type TraceReadiness = {
  status: string;
  trace_count: number | null;
  current_leaf_count: number | null;
  current_leaf_item_status_counts: Record<string, number> | null;
  traces: Trace[];
  lineages: {
    root_id: string;
    current_leaf_id: string | null;
    status: string;
    historical_trace_ids: string[];
  }[];
};
export const observationLabels: Record<string, string> = {
  OBSERVED: "Observation recorded",
  EXCEPTION_RECORDED: "Exception recorded",
  SUPPORT_UNAVAILABLE: "Support unavailable",
  NOT_PERFORMED: "Not performed",
};
export function visibleCount(value: unknown) {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0
    ? String(value)
    : "Unavailable";
}
/** Use server-computed pins from the same authorized revision, never hash browser JSON. */
export function resolveTraceReference(
  e: Engagement,
  ref: ContextLink,
): Row | null {
  if (
    !ref ||
    !Object.hasOwn(investigationKinds, ref.kind) ||
    !/^[a-f0-9]{64}$/.test(ref.sha256)
  )
    return null;
  const input = e.sample_execution_inputs as
    Record<string, unknown> | undefined;
  if (
    !input ||
    !["AVAILABLE", "ENGAGEMENT_NOT_ACTIVE"].includes(String(input.status)) ||
    input.engagement_id !== e.id ||
    input.engagement_revision !== e.revision
  )
    return null;
  const collection = investigationKinds[ref.kind];
  const rows = e[collection].filter((row) => row.id === ref.id);
  if (rows.length !== 1) return null;
  const row = rows[0];
  const list = (name: string) =>
    Array.isArray(input[name])
      ? (input[name] as Record<string, unknown>[])
      : [];
  let pins: Record<string, unknown>[] = [];
  if (ref.kind === "workpaper") {
    if (
      !Number.isSafeInteger(ref.version) ||
      !Array.isArray(row.versions) ||
      row.versions.filter((v) => v.version === ref.version).length !== 1
    )
      return null;
    pins = list("workpaper_versions").filter(
      (p) =>
        p.workpaper_id === ref.id &&
        p.workpaper_version === ref.version &&
        p.workpaper_digest === ref.sha256,
    );
  } else if (ref.kind === "artifact") {
    if (
      row.status !== "AVAILABLE" ||
      row.sha256 !== ref.sha256 ||
      row.audience === "INSTRUCTOR"
    )
      return null;
    pins = list("artifacts").filter(
      (p) => p.artifact_id === ref.id && p.sha256 === ref.sha256,
    );
  } else if (ref.kind === "task") {
    pins = list("tasks").filter(
      (p) => p.task_id === ref.id && p.task_digest === ref.sha256,
    );
  } else if (ref.kind === "population") {
    // Multiple selections may legitimately point to one exact population.
    pins = list("selections").filter(
      (p) =>
        p.population_id === ref.id &&
        p.population_version === ref.version &&
        p.population_digest === ref.sha256,
    );
    return pins.length > 0 && row.version === ref.version ? row : null;
  } else if (ref.kind === "selection") {
    pins = list("selections").filter(
      (p) => p.selection_id === ref.id && p.selection_digest === ref.sha256,
    );
  }
  return pins.length === 1 ? row : null;
}
export function tracePosition(data: TraceReadiness, id: string) {
  if (
    data.lineages.some(
      (g) =>
        g.status === "EXACT_VISIBLE_METADATA_LINKS" && g.current_leaf_id === id,
    )
  )
    return "Current trace for this lineage";
  if (data.lineages.some((g) => g.historical_trace_ids.includes(id)))
    return "Historical retained trace";
  return "Correction lineage unavailable";
}
