import type { Engagement } from "./api";
import { investigationKinds, type ContextLink } from "./investigationContext";
import { resolveSavedViewReference } from "./savedViews";

export type CheckpointPin = { reference: ContextLink; record_sha256: string };
export type CheckpointChange = {
  change: "ADDED" | "CHANGED";
  prior: CheckpointPin | null;
  current: CheckpointPin;
};
export type VisitCheckpoint = {
  engagement_id: string;
  current_engagement_revision: number;
  version: number;
  status: string;
  saved_at?: string;
  checkpoint_engagement_revision?: number;
  formal_work_mutated: false;
  supported_kinds: string[];
  changes?: CheckpointChange[];
  counts?: { added: number; changed: number; unchanged: number };
};
export const checkpointPath = (id: string) =>
  `/api/engagements/${encodeURIComponent(id)}/visit-checkpoint`;
export function checkpointRecord(e: Engagement, ref: ContextLink) {
  const row = resolveSavedViewReference(e, ref);
  return ref.kind === "artifact" && row?.sha256 !== ref.sha256 ? null : row;
}
const hash = (v: unknown) => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const integer = (v: unknown) => Number.isSafeInteger(v) && Number(v) >= 0;
function validPin(pin: CheckpointPin | null): boolean {
  const ref = pin?.reference;
  return (
    !!ref &&
    Object.hasOwn(investigationKinds, ref.kind) &&
    typeof ref.id === "string" &&
    ref.id.length > 0 &&
    ref.id.length <= 256 &&
    (ref.version === null || integer(ref.version)) &&
    hash(ref.sha256) &&
    hash(pin?.record_sha256)
  );
}
/** Reject stale context and any inventory attached to an unavailable response. */
export function verifyCheckpoint(
  value: VisitCheckpoint,
  e: Engagement,
  comparison = false,
): VisitCheckpoint {
  const invalid = () => {
    throw new Error(
      "Checkpoint response does not match the current workspace. Refresh before continuing.",
    );
  };
  if (
    !value ||
    value.engagement_id !== e.id ||
    value.current_engagement_revision !== e.revision ||
    !integer(value.version) ||
    value.formal_work_mutated !== false ||
    ![
      "NO_CHECKPOINT",
      "CURRENT",
      "CONTEXT_CHANGED",
      "TARGET_UNAVAILABLE",
      "INPUT_LIMIT_EXCEEDED",
      "INPUT_DATA_UNAVAILABLE",
    ].includes(value.status)
  )
    invalid();
  if (value.status !== "CURRENT") {
    if (value.changes !== undefined || value.counts !== undefined) invalid();
    return value;
  }
  if (value.version < 1) invalid();
  if (!comparison) {
    if (value.changes !== undefined || value.counts !== undefined) invalid();
    return value;
  }
  const changes = value.changes,
    counts = value.counts;
  if (
    !Array.isArray(changes) ||
    changes.length > 10000 ||
    !counts ||
    !integer(counts.added) ||
    !integer(counts.changed) ||
    !integer(counts.unchanged)
  )
    invalid();
  const keys = new Set<string>();
  for (const change of changes!) {
    if (
      !change ||
      !validPin(change.current) ||
      (change.change === "ADDED"
        ? change.prior !== null
        : change.change !== "CHANGED" || !validPin(change.prior))
    )
      invalid();
    const ref = change.current.reference;
    const key = JSON.stringify([
      ref.kind,
      ref.id,
      ref.kind === "workpaper" ? ref.version : null,
    ]);
    if (keys.has(key)) invalid();
    keys.add(key);
    if (
      change.prior &&
      JSON.stringify([
        change.prior.reference.kind,
        change.prior.reference.id,
        change.prior.reference.kind === "workpaper"
          ? change.prior.reference.version
          : null,
      ]) !== key
    )
      invalid();
  }
  if (
    counts!.added !== changes!.filter((c) => c.change === "ADDED").length ||
    counts!.changed !== changes!.filter((c) => c.change === "CHANGED").length ||
    counts!.added + counts!.changed + counts!.unchanged > 10000
  )
    invalid();
  return value;
}
