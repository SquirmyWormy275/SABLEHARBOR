import { canReviewWorkpaper, type Engagement, type Row } from "./api";
export const FEEDBACK_DISPOSITIONS = [
  "agree",
  "disagree",
  "correct",
  "missing_context",
  "human_review",
] as const;
const COMMENT_KINDS = ["HUMAN", "SCRIPTED_ENGINEERING", "SYNTHETIC_TECHNICAL"];
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
    (row.kind === undefined || COMMENT_KINDS.includes(String(row.kind))) &&
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
        "Only recorded comments and experimental suggestions accept feedback.",
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

export function humanResolutionTarget(
  e: Engagement,
  reviewId: string,
  viewerId: string | undefined,
  supported: boolean,
): Record<string, unknown> | null {
  const rows = e.reviews.filter((row) => row.id === reviewId);
  if (rows.length !== 1) return null;
  const review = rows[0];
  if (
    (review.kind !== undefined && !COMMENT_KINDS.includes(String(review.kind))) ||
    review.status !== "OPEN"
  )
    return null;
  const target = reviewFeedbackTarget(e, reviewId, supported);
  if (!target.payload) return null;
  const paper = e.workpapers.find((row) => row.id === review.workpaper_id);
  const latest = Array.isArray(paper?.versions)
    ? (paper.versions.at(-1) as Row | undefined)
    : undefined;
  if (
    !paper ||
    !latest ||
    !canReviewWorkpaper(paper, viewerId, e.permissions, latest)
  )
    return null;
  return { review_id: review.id, response_workpaper_version: latest.version };
}
