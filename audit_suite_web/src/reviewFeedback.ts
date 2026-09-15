import type { Engagement, Row } from "./api";
export const FEEDBACK_DISPOSITIONS = [
  "agree",
  "disagree",
  "correct",
  "missing_context",
  "human_review",
] as const;
export function reviewFeedbackTarget(
  e: Engagement,
  reviewId: string,
  supported: boolean,
): { payload: Record<string, unknown> | null; reason: string } {
  if (!supported)
    return {
      payload: null,
      reason:
        "This server does not support feedback recorded separately from resolution.",
    };
  if (!e.permissions?.some((p) => ["learn", "review", "instruct"].includes(p)))
    return {
      payload: null,
      reason: "Current engagement permission is required to respond.",
    };
  const matches = e.reviews.filter((row) => row.id === reviewId);
  if (matches.length !== 1)
    return {
      payload: null,
      reason: "This review is no longer available in the current engagement.",
    };
  const row = matches[0];
  if (row.status === "PREPARED" || row.kind === "EXPERIMENTAL_INPUT")
    return {
      payload: null,
      reason:
        "Prepared input is not a review result and cannot receive feedback.",
    };
  const payload: Record<string, unknown> = { review_id: row.id };
  if (row.kind === "EXPERIMENTAL_AI") {
    if (typeof row.input_digest === "string" && row.input_digest)
      payload.input_digest = row.input_digest;
  } else if (
    (row.kind === undefined || row.kind === "HUMAN") &&
    typeof row.workpaper_id === "string"
  ) {
    const paper = e.workpapers.find((p) => p.id === row.workpaper_id),
      versions = paper?.versions;
    const latest = Array.isArray(versions)
      ? (versions.at(-1) as Row | undefined)
      : undefined;
    if (
      !latest ||
      !Number.isInteger(latest.version) ||
      Number(latest.version) < 1
    )
      return {
        payload: null,
        reason: "The response requires the current retained workpaper version.",
      };
    payload.response_workpaper_version = latest.version;
  } else
    return {
      payload: null,
      reason:
        "Only human comments and experimental suggestions accept feedback.",
    };
  return { payload, reason: "" };
}
export function recordedFeedback(row: Row): Row[] {
  const source = row.kind === "EXPERIMENTAL_AI" ? row.appeals : row.history;
  return Array.isArray(source)
    ? source.filter(
        (v): v is Row =>
          v !== null && typeof v === "object" && !Array.isArray(v),
      )
    : [];
}
