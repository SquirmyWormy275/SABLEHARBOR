import { ApiError, request } from "./api";
import type { DraftKey } from "./draftContext";
export type PersonalDraft = {
  status: "DRAFT" | "EMPTY" | "STALE";
  version: number;
  fields?: Record<string, unknown>;
  base_workpaper_version: number | null;
  workpaper_stale?: boolean;
  updated_at?: string;
};
export function draftURL(key: DraftKey) {
  return `/api/engagements/${encodeURIComponent(key.engagementId)}/drafts/${encodeURIComponent(key.kind)}/${encodeURIComponent(key.objectId)}`;
}
export function draftFields(key: DraftKey, values: Record<string, unknown>) {
  const common =
    key.kind === "note.create"
      ? ["title", "text", "control_id", "source_message_id"]
      : [
          "title",
          "text",
          "objective",
          "procedures",
          "conclusion",
          "section",
          "evidence_ids",
          "artifact_id",
        ];
  const fields: Record<string, unknown> = {};
  for (const field of common)
    if (values[field] !== undefined) {
      fields[field] =
        field === "evidence_ids" && typeof values[field] === "string"
          ? (values[field] as string)
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
          : values[field];
    }
  return fields;
}
export function formDraftFields(fields: Record<string, unknown>) {
  return {
    ...fields,
    ...(Array.isArray(fields.evidence_ids)
      ? { evidence_ids: fields.evidence_ids.join(", ") }
      : {}),
  };
}
/** Explicit optimistic versioning; callers must surface409 and never retry with a newer version implicitly. */
export const readDraft = (key: DraftKey) =>
  request<PersonalDraft>(draftURL(key));
export const writeDraft = (
  key: DraftKey,
  version: number,
  values: Record<string, unknown>,
  commandId: string = crypto.randomUUID(),
) =>
  request<PersonalDraft>(draftURL(key), "PUT", {
    command_id: commandId,
    expected_version: version,
    fields: draftFields(key, values),
    base_workpaper_version:
      key.kind === "workpaper.update" ? Number(key.baseVersion) : null,
  });
export const deleteDraft = (
  key: DraftKey,
  version: number,
  commandId: string = crypto.randomUUID(),
) =>
  request<PersonalDraft>(draftURL(key), "DELETE", {
    command_id: commandId,
    expected_version: version,
  });
export const draftConflict = (error: unknown) =>
  error instanceof ApiError && error.status === 409;
