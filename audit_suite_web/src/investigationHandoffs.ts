import type { Engagement, Row } from "./api";
import type { ContextLink } from "./investigationContext";
import { resolveSavedViewReference } from "./savedViews";
export const handoffsPath = (id: string) =>
  `/api/engagements/${encodeURIComponent(id)}/handoffs`;
/** Revision is separate: ordinary work changes must not discard authored form text. */
export function handoffAuthority(e: Engagement, viewerId: string): string {
  return JSON.stringify([
    viewerId,
    e.id,
    e.scope,
    e.permissions,
    e.company_source_binding,
    e.evidence_acquisition,
  ]);
}
export function handoffLinkKey(link: ContextLink): string {
  return JSON.stringify([link.kind, link.id, link.version, link.sha256]);
}
export function resolveHandoffReference(
  e: Engagement,
  link: ContextLink,
  status: string,
): Row | null {
  if (!["EXACT_PIN_AVAILABLE", "HISTORICAL_VERSION_AVAILABLE"].includes(status))
    return null;
  const row = resolveSavedViewReference(e, link);
  if (link.kind === "artifact" && row?.sha256 !== link.sha256) return null;
  return row;
}
export type PendingHandoffCommand = {
  path: string;
  body: Record<string, unknown>;
};
/** Detach the exact envelope so later typing cannot change an ambiguous transport retry. */
export function freezeHandoffCommand(
  path: string,
  body: Record<string, unknown>,
): PendingHandoffCommand {
  return { path, body: structuredClone(body) };
}
export type Handoff = {
  id: string;
  version: number;
  status: string;
  engagement_id: string;
  current_engagement_revision: number;
  sender_id: string;
  recipient_id: string;
  acting_role: "SENDER" | "RECIPIENT";
  shared_content_visible: boolean;
  context_status: string;
  allowed_actions: string[];
  content?: {
    title: string;
    question: string;
    next_step: string;
    links: ContextLink[];
    response: string;
    response_author_id: string | null;
  };
};
export function currentHandoff(
  h: Handoff,
  e: Engagement,
  viewer: string,
): boolean {
  return (
    h.engagement_id === e.id &&
    h.current_engagement_revision === e.revision &&
    [h.sender_id, h.recipient_id].includes(viewer) &&
    Number.isSafeInteger(h.version) &&
    h.version > 0
  );
}
export function handoffWaiting(h: Handoff, viewer: string): string {
  const other = h.sender_id === viewer ? h.recipient_id : h.sender_id;
  if (h.status === "OFFERED")
    return h.recipient_id === viewer
      ? "Awaiting your decision"
      : `Awaiting ${other}'s decision`;
  if (h.status === "ACCEPTED")
    return h.recipient_id === viewer
      ? "Your response is awaited"
      : `Awaiting ${other}'s response`;
  if (h.status === "COMPLETED") return "Coordination response completed";
  return h.status === "WITHDRAWN"
    ? "Withdrawn by sender"
    : "Declined by recipient";
}
