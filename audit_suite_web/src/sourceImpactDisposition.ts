import type { Engagement, Row } from "./api";
import { impactContext } from "./sourceImpact";
export const dispositions = {
  ACKNOWLEDGED: "Change noted — no reassessment decision yet",
  REASSESSMENT_NEEDED: "Reassessment needed",
  RETEST_LINKED: "Existing reassessment work linked",
  NOT_APPLICABLE_TO_SELECTED_WORK: "Not applicable to this selected work",
} as const;
export type Disposition = keyof typeof dispositions;
export type ImpactChoice = {
  sha256: string;
  reference: Row;
  record_sha256: string;
};
export type DispositionInputs = {
  engagement_id: string;
  engagement_revision: number;
  artifact_id: string;
  comparison: Record<string, unknown> & { sha256: string };
  observed: { discovered_at: string; rechecked_at: string };
  targets: ImpactChoice[];
  retests: ImpactChoice[];
  predecessors: { id: string; sha256: string; target_sha256: string }[];
};
export type DispositionDraft = {
  target_sha256: string;
  disposition: Disposition;
  rationale: string;
  intended_action: string;
  retest_sha256: string | null;
  predecessor: { id: string; sha256: string } | null;
};
export type DispositionCommand = {
  command_id: string;
  expected_revision: number;
  kind: "source.impact.disposition.record";
  payload: DispositionDraft & {
    artifact_id: string;
    comparison_sha256: string;
  };
};
const pin = (v: unknown): v is string =>
  typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
export function dispositionContext(e: Engagement, viewer: string) {
  return JSON.stringify([viewer, impactContext(e)]);
}
export function dispositionLabel(c: ImpactChoice) {
  const r = c.reference;
  return `${String(r.collection ?? "record")} · ${r.id}${r.version == null ? "" : ` · version ${r.version}`}${r.item_id ? ` · item ${r.item_id}` : ""}${r.remediation_id ? ` · remediation ${r.remediation_id}` : ""}`;
}
export function validateDispositionInputs(
  v: DispositionInputs,
  e: Engagement,
  artifact: string,
) {
  if (
    !v ||
    v.engagement_id !== e.id ||
    v.engagement_revision !== e.revision ||
    v.artifact_id !== artifact ||
    !e.artifacts.some((a) => a.id === artifact) ||
    !pin(v.comparison?.sha256) ||
    v.comparison.artifact_id !== artifact ||
    !pin(v.comparison.collected_sha256) ||
    !pin(v.comparison.latest_visible_sha256) ||
    !e.artifacts.some(
      (a) => a.id === artifact && a.sha256 === v.comparison.collected_sha256,
    ) ||
    !Number.isSafeInteger(v.comparison.collected_version) ||
    !Number.isSafeInteger(v.comparison.latest_visible_version) ||
    Number(v.comparison.collected_version) < 1 ||
    Number(v.comparison.latest_visible_version) <=
      Number(v.comparison.collected_version) ||
    v.comparison.simulated_as_of !== e.simulated_at ||
    !v.observed ||
    typeof v.observed.discovered_at !== "string" ||
    typeof v.observed.rechecked_at !== "string"
  )
    throw Error(
      "Reassessment choices no longer match this workspace. Check again.",
    );
  for (const choices of [v.targets, v.retests]) {
    if (
      !Array.isArray(choices) ||
      choices.length > 256 ||
      new Set(choices.map((c) => c.sha256)).size !== choices.length ||
      choices.some(
        (c) =>
          !pin(c.sha256) ||
          !pin(c.record_sha256) ||
          !c.reference ||
          typeof c.reference.id !== "string" ||
          typeof c.reference.collection !== "string",
      )
    )
      throw Error("Exact reassessment choices are unavailable.");
  }
  if (
    !Array.isArray(v.predecessors) ||
    v.predecessors.length > 256 ||
    v.predecessors.some(
      (p) =>
        typeof p.id !== "string" || !pin(p.sha256) || !pin(p.target_sha256),
    )
  )
    throw Error("Reassessment history pins are unavailable.");
  return v;
}
export function dispositionCommand(
  e: Engagement,
  input: DispositionInputs,
  draft: DispositionDraft,
  commandId: string,
): DispositionCommand {
  validateDispositionInputs(input, e, input.artifact_id);
  if (
    !input.targets.some((c) => c.sha256 === draft.target_sha256) ||
    !Object.hasOwn(dispositions, draft.disposition) ||
    !draft.rationale.trim() ||
    Array.from(draft.rationale).length > 4000 ||
    !draft.intended_action.trim() ||
    Array.from(draft.intended_action).length > 2000
  )
    throw Error(
      "Choose the exact affected work and describe your rationale and intended action.",
    );
  if (
    draft.disposition === "RETEST_LINKED"
      ? !input.retests.some((c) => c.sha256 === draft.retest_sha256) ||
        draft.retest_sha256 === draft.target_sha256
      : draft.retest_sha256 !== null
  )
    throw Error(
      "Link existing pinned reassessment work only for the linked-work disposition.",
    );
  if (
    !draft.predecessor &&
    input.predecessors.some((p) => p.target_sha256 === draft.target_sha256)
  )
    throw Error(
      "Select the exact prior disposition before appending a correction.",
    );
  if (
    draft.predecessor &&
    !input.predecessors.some(
      (p) =>
        p.id === draft.predecessor!.id &&
        p.sha256 === draft.predecessor!.sha256 &&
        p.target_sha256 === draft.target_sha256,
    )
  )
    throw Error("Choose an exact current predecessor for this target.");
  return {
    command_id: commandId,
    expected_revision: e.revision,
    kind: "source.impact.disposition.record",
    payload: structuredClone({
      ...draft,
      artifact_id: input.artifact_id,
      comparison_sha256: input.comparison.sha256,
    }),
  };
}
export type ImpactDispositionRecord = {
  id: string;
  revision: number;
  version: number;
  actor: string;
  recorded_at: string;
  context_status?: string;
  personal_content_visible?: boolean;
  artifact_id?: string;
  comparison?: DispositionInputs["comparison"];
  observed?: DispositionInputs["observed"];
  target?: ImpactChoice;
  disposition?: Disposition;
  rationale?: string;
  intended_action?: string;
  retest?: ImpactChoice | null;
  predecessor?: { id: string; sha256: string } | null;
  qualification?: string;
};
export function dispositionRecords(e: Engagement): ImpactDispositionRecord[] {
  const rows = e.source_impact_dispositions;
  return Array.isArray(rows) ? (rows as ImpactDispositionRecord[]) : [];
}
export function acceptedDisposition(
  e: Engagement,
  value: Engagement,
  viewer: string,
  c: DispositionCommand,
): boolean {
  if (
    value.id !== e.id ||
    value.revision !== e.revision + 1 ||
    dispositionContext({ ...value, revision: e.revision }, viewer) !==
      dispositionContext(e, viewer)
  )
    return false;
  const prior = new Set(dispositionRecords(e).map((r) => r.id));
  const rows = dispositionRecords(value).filter((r) => !prior.has(r.id));
  if (rows.length !== 1) return false;
  const r = rows[0],
    p = c.payload;
  return (
    r.revision === value.revision &&
    r.context_status === "CURRENT" &&
    r.personal_content_visible === true &&
    r.actor === viewer &&
    r.artifact_id === p.artifact_id &&
    r.comparison?.sha256 === p.comparison_sha256 &&
    r.target?.sha256 === p.target_sha256 &&
    r.disposition === p.disposition &&
    r.rationale === p.rationale &&
    r.intended_action === p.intended_action &&
    (r.retest?.sha256 ?? null) === p.retest_sha256 &&
    (r.predecessor?.id ?? null) === (p.predecessor?.id ?? null) &&
    (r.predecessor?.sha256 ?? null) === (p.predecessor?.sha256 ?? null)
  );
}
