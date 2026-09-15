import type { Engagement } from "./api";
export const ITEM_STATUSES = [
  "OBSERVED",
  "EXCEPTION_RECORDED",
  "SUPPORT_UNAVAILABLE",
  "NOT_PERFORMED",
] as const;
export type Item = {
  item_id: string;
  observation: string;
  status: string;
  evidence: { artifact_id: string; sha256: string; locator: string }[];
};
export type Pins = {
  engagement_id: string;
  engagement_revision: number;
  status: string;
  tasks: {
    task_id: string;
    task_digest: string;
    boundary_id: string;
    control_id: string;
  }[];
  selections: {
    selection_id: string;
    selection_digest: string;
    population_id: string;
    population_digest: string;
    boundary_id: string;
    sampling_unit: string;
    population_status: string;
    selection_provisional: boolean;
  }[];
  workpaper_versions: {
    workpaper_id: string;
    workpaper_version: number;
    workpaper_digest: string;
    task_ids: string[];
  }[];
  artifacts: { artifact_id: string; sha256: string; bytes: number }[];
  correctable_executions?: {
    execution_id: string;
    predecessor_digest: string;
  }[];
};
export function inputPins(e: Engagement, supported: boolean): Pins | null {
  const p = e.sample_execution_inputs as Pins | undefined;
  return supported &&
    e.permissions?.some((r) => r === "learn" || r === "instruct") &&
    p?.status === "AVAILABLE" &&
    p.engagement_id === e.id &&
    p.engagement_revision === e.revision
    ? p
    : null;
}
export function selectionItems(e: Engagement, id: string): string[] {
  const rows = e.selections.filter((s) => s.id === id);
  if (rows.length !== 1) return [];
  const row = rows[0];
  const native = (row.immutable ?? row) as Record<string, unknown>;
  const selected = native.selected_ids,
    targeted = native.targeted_ids;
  if (
    !Array.isArray(selected) ||
    !selected.every((x) => typeof x === "string") ||
    (targeted !== undefined &&
      (!Array.isArray(targeted) ||
        !targeted.every((x) => typeof x === "string")))
  )
    return [];
  return [
    ...new Set([...selected, ...(Array.isArray(targeted) ? targeted : [])]),
  ];
}
export type Draft = {
  task: string;
  selection: string;
  workpaper: string;
  purpose: string;
  procedure: string;
  items: Item[];
  predecessor?: string;
  rationale: string;
};
export function executionPayload(
  e: Engagement,
  p: Pins,
  d: Draft,
): Record<string, unknown> {
  if (inputPins(e, true) !== p)
    throw Error("Current authorized input pins are required.");
  const task = p.tasks.find((t) => t.task_id === d.task),
    s = p.selections.find((s) => s.selection_id === d.selection),
    w = p.workpaper_versions.find(
      (w) => `${w.workpaper_id}:${w.workpaper_version}` === d.workpaper,
    );
  if (
    !task ||
    !s ||
    !w ||
    task.boundary_id !== s.boundary_id ||
    !w.task_ids.includes(task.task_id)
  )
    throw Error(
      "Choose a scoped procedure, matching selection and explicitly linked workpaper version.",
    );
  if (
    !d.purpose.trim() ||
    d.purpose.length > 4000 ||
    !d.procedure.trim() ||
    d.procedure.length > 12000 ||
    !d.items.length ||
    d.items.length > 500
  )
    throw Error(
      "Supply purpose, procedure and one to500 explicit item observations.",
    );
  const ids = selectionItems(e, d.selection);
  const seen = new Set<string>();
  for (const i of d.items) {
    if (
      !ids.includes(i.item_id) ||
      seen.has(i.item_id) ||
      !ITEM_STATUSES.includes(i.status as (typeof ITEM_STATUSES)[number]) ||
      !i.observation.trim() ||
      i.observation.length > 8000 ||
      i.evidence.length > 20
    )
      throw Error(
        "Each item requires a unique selected ID, manual status and observation.",
      );
    seen.add(i.item_id);
    if (
      ["OBSERVED", "EXCEPTION_RECORDED"].includes(i.status) &&
      !i.evidence.length
    )
      throw Error("Observed or exception items need retained support.");
    for (const r of i.evidence)
      if (
        !r.locator.trim() ||
        r.locator.length > 1000 ||
        !p.artifacts.some(
          (a) => a.artifact_id === r.artifact_id && a.sha256 === r.sha256,
        )
      )
        throw Error("Choose current retained support and an explicit locator.");
  }
  const payload: Record<string, unknown> = {
    task_id: task.task_id,
    task_digest: task.task_digest,
    selection_id: s.selection_id,
    selection_digest: s.selection_digest,
    population_id: s.population_id,
    population_digest: s.population_digest,
    workpaper_id: w.workpaper_id,
    workpaper_version: w.workpaper_version,
    workpaper_digest: w.workpaper_digest,
    purpose: d.purpose,
    procedure: d.procedure,
    items: d.items.map((i) => ({
      ...i,
      evidence: i.evidence.map((r) => ({ ...r })),
    })),
  };
  if (d.predecessor) {
    const pin = p.correctable_executions?.find(
      (x) => x.execution_id === d.predecessor,
    );
    const prior = (
      (e.sample_executions as Record<string, unknown>[]) ?? []
    ).find((x) => x.id === d.predecessor);
    if (
      !pin ||
      !prior ||
      prior.task_id !== d.task ||
      prior.selection_id !== d.selection ||
      !d.rationale.trim() ||
      d.rationale.length > 4000 ||
      JSON.stringify((prior.items as Item[]).map((i) => i.item_id).sort()) !==
        JSON.stringify([...seen].sort())
    )
      throw Error(
        "Correction requires a current eligible leaf, unchanged item set and rationale.",
      );
    Object.assign(payload, {
      predecessor_id: d.predecessor,
      predecessor_digest: pin.predecessor_digest,
      correction_rationale: d.rationale,
    });
  }
  return payload;
}
