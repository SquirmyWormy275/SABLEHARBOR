import { workpaperVersions, type Engagement, type Row } from "./api";

export const gapCauses = {
  MISSING_OPERATION: "Missing company operation",
  UNCOLLECTED_SOURCE: "Source exists but has not been collected",
  INSUFFICIENT_SOURCE: "Collected source is insufficient",
  DENIED_ACCESS: "Source access was denied",
} as const;
export const gapDispositions = {
  OPEN: "Open",
  FOLLOW_UP_REQUESTED: "Follow-up requested",
  RETEST_LINKED: "Existing retest workpaper linked",
  LIMITATION_RETAINED: "Limitation retained",
} as const;
export type GapCause = keyof typeof gapCauses;
export type GapDisposition = keyof typeof gapDispositions;
export type ArtifactPin = { id: string; sha256: string };
export type RetestPin = { workpaper_id: string; version: number };
export type TaskGapDraft = {
  cause: GapCause;
  owner_id: string;
  disposition: GapDisposition;
  narrative: string;
  artifact_id: string;
  retest_key: string;
  predecessor_id: string;
};
export type TaskGapPayload = {
  task_id: string;
  cause: GapCause;
  owner_id: string;
  disposition: GapDisposition;
  narrative: string;
  artifact_pin: ArtifactPin | null;
  retest: RetestPin | null;
  predecessor_id: string | null;
};
export type TaskGapCommand = {
  command_id: string;
  expected_revision: number;
  kind: "task.gap.record";
  payload: TaskGapPayload;
};
export type TaskGapRow = Row &
  Omit<TaskGapPayload, "artifact_pin" | "retest"> & {
    artifact_pin:
      | (ArtifactPin & { native_source_pin?: Record<string, unknown> | null })
      | null;
    retest: (RetestPin & { version_sha256?: string }) | null;
    actor: string;
    revision: number;
    recorded_at: string;
    qualification: string;
    predecessor_sha256?: string | null;
  };
const isPin = (s: unknown): s is string =>
  typeof s === "string" && /^[a-f0-9]{64}$/.test(s);
export const canRecordTaskGap = (e: Engagement) =>
  e.phase === "ACTIVE" &&
  (e.permissions ?? []).some((p) => p === "learn" || p === "instruct");
export const taskEligibleForGap = (task: Row) =>
  !["NOT_APPLICABLE", "EXCLUDED"].includes(String(task.status)) &&
  task.applicable !== false;
export const taskGapRows = (e: Engagement, taskId: string): TaskGapRow[] =>
  (Array.isArray(e.task_gaps) ? e.task_gaps : []).filter(
    (r): r is TaskGapRow =>
      !!r &&
      typeof r === "object" &&
      r.task_id === taskId &&
      typeof r.id === "string",
  );
export const currentTaskGaps = (rows: TaskGapRow[]) => {
  const predecessors = new Set(
    rows.map((r) => r.predecessor_id).filter(Boolean),
  );
  return rows.filter((r) => !predecessors.has(r.id));
};
export const taskRetests = (e: Engagement, taskId: string): RetestPin[] =>
  e.workpapers.flatMap((paper) =>
    workpaperVersions(paper)
      .filter((v) => Array.isArray(v.task_ids) && v.task_ids.includes(taskId))
      .map((v) => ({ workpaper_id: paper.id, version: Number(v.version) }))
      .filter((r) => Number.isSafeInteger(r.version) && r.version > 0),
  );
export const retestKey = (r: RetestPin) => `${r.workpaper_id}:v${r.version}`;
export function taskGapCommand(
  e: Engagement,
  viewerId: string,
  taskId: string,
  draft: TaskGapDraft,
  commandId: string,
): TaskGapCommand {
  if (
    !canRecordTaskGap(e) ||
    !viewerId ||
    !e.tasks.some((t) => t.id === taskId && taskEligibleForGap(t))
  )
    throw Error(
      "This task is not available for gap recording in the current workroom.",
    );
  if (
    !Object.hasOwn(gapCauses, draft.cause) ||
    !Object.hasOwn(gapDispositions, draft.disposition)
  )
    throw Error("Choose an explicit gap cause and disposition.");
  const narrative = draft.narrative.trim();
  if (narrative.length < 20 || narrative.length > 4000)
    throw Error("Describe the observed gap in 20–4,000 characters.");
  const owner = draft.owner_id.trim();
  if (!owner) throw Error("Name the scoped auditor who owns this gap.");
  const artifact = draft.artifact_id
    ? e.artifacts.find(
        (a) => a.id === draft.artifact_id && a.status === "AVAILABLE",
      )
    : undefined;
  if (draft.artifact_id && (!artifact || !isPin(artifact.sha256)))
    throw Error(
      "Choose an available retained artifact with an exact SHA-256 pin.",
    );
  const retest = taskRetests(e, taskId).find(
    (r) => retestKey(r) === draft.retest_key,
  );
  if (draft.disposition === "RETEST_LINKED" ? !retest : !!draft.retest_key)
    throw Error(
      "Link an exact task-associated workpaper version only for retest-linked disposition.",
    );
  const gaps = taskGapRows(e, taskId);
  const prior = gaps.find((r) => r.id === draft.predecessor_id);
  if (
    draft.predecessor_id &&
    (!prior || gaps.some((r) => r.predecessor_id === prior.id))
  )
    throw Error(
      "Choose a current gap in this task before appending a follow-up.",
    );
  if (!commandId) throw Error("Command identity required.");
  return {
    command_id: commandId,
    expected_revision: e.revision,
    kind: "task.gap.record",
    payload: {
      task_id: taskId,
      cause: draft.cause,
      owner_id: owner,
      disposition: draft.disposition,
      narrative,
      artifact_pin: artifact
        ? { id: artifact.id, sha256: artifact.sha256 as string }
        : null,
      retest: retest ?? null,
      predecessor_id: prior?.id ?? null,
    },
  };
}
export function acceptedTaskGap(
  before: Engagement,
  after: Engagement,
  viewerId: string,
  command: TaskGapCommand,
) {
  if (after.id !== before.id || after.revision !== before.revision + 1)
    return false;
  const previous = new Set(
    taskGapRows(before, command.payload.task_id).map((r) => r.id),
  );
  const matching = taskGapRows(after, command.payload.task_id).filter(
    (r) =>
      !previous.has(r.id) &&
      r.revision === after.revision &&
      r.actor === viewerId &&
      r.qualification ===
        "AUTHOR_RECORDED_GAP_NOT_EVIDENCE_OR_AUDIT_CONCLUSION" &&
      r.cause === command.payload.cause &&
      r.owner_id === command.payload.owner_id &&
      r.disposition === command.payload.disposition &&
      r.narrative === command.payload.narrative &&
      r.predecessor_id === command.payload.predecessor_id &&
      (command.payload.artifact_pin === null
        ? r.artifact_pin === null
        : r.artifact_pin?.id === command.payload.artifact_pin.id &&
          r.artifact_pin?.sha256 === command.payload.artifact_pin.sha256) &&
      (command.payload.retest === null
        ? r.retest === null
        : r.retest?.workpaper_id === command.payload.retest.workpaper_id &&
          r.retest?.version === command.payload.retest.version),
  );
  return matching.length === 1;
}
