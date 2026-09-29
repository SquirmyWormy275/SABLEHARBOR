import type { Engagement, Row } from "./api";
export type MessagePin = {
  meeting_id: string;
  message_id: string;
  sha256: string;
};
export type Consultation = {
  kind: "REFERRAL" | "CORRECTION_REQUEST";
  question_ref: MessagePin;
  response_ref: MessagePin | null;
};
export type ConsultationResponse = {
  ref: MessagePin;
  person_id: string;
  content: string;
  simulated_at?: string;
};
export type ConsultationQuestion = {
  ref: MessagePin;
  meeting_title: string;
  person_id: string;
  content: string;
  simulated_at?: string;
  responses: ConsultationResponse[];
};
export type ConsultationInputs = {
  status: string;
  questions: ConsultationQuestion[];
};
export function sameMessagePin(
  a: MessagePin | undefined | null,
  b: MessagePin | undefined | null,
): boolean {
  return Boolean(
    a &&
    b &&
    /^[a-f0-9]{64}$/.test(a.sha256) &&
    a.meeting_id === b.meeting_id &&
    a.message_id === b.message_id &&
    a.sha256 === b.sha256,
  );
}
export function consultationInputs(e: Engagement): ConsultationInputs {
  const value = e.company_consultation_inputs as ConsultationInputs | undefined;
  return value?.status === "AVAILABLE" && Array.isArray(value.questions)
    ? value
    : { status: value?.status ?? "UNAVAILABLE", questions: [] };
}
export function consultationAuthority(
  e: Engagement,
  viewerId: string,
  targetMeetingId: string,
): string {
  return JSON.stringify([
    viewerId,
    e.id,
    e.scope,
    e.permissions,
    e.company_source_binding,
    e.evidence_acquisition,
    targetMeetingId,
    e.meetings.find((m) => m.id === targetMeetingId)?.person_id,
  ]);
}
export function eligibleQuestions(
  e: Engagement,
  targetMeetingId: string,
  kind: Consultation["kind"],
): ConsultationQuestion[] {
  const meetings = e.meetings.filter((m) => m.id === targetMeetingId);
  if (meetings.length !== 1) return [];
  return consultationInputs(e).questions.filter((q) =>
    kind === "REFERRAL"
      ? q.person_id !== meetings[0].person_id
      : q.responses.length > 0,
  );
}
/** Exact server pins only; text is never rehashed or substituted in the browser. */
export function validConsultation(
  e: Engagement,
  targetMeetingId: string,
  value: Consultation,
): boolean {
  const matches = eligibleQuestions(e, targetMeetingId, value.kind).filter(
    (q) => sameMessagePin(q.ref, value.question_ref),
  );
  if (matches.length !== 1) return false;
  if (value.response_ref === null) return value.kind === "REFERRAL";
  return (
    matches[0].responses.filter((r) =>
      sameMessagePin(r.ref, value.response_ref),
    ).length === 1
  );
}
export function resolveConsultationMessage(
  e: Engagement,
  pin: MessagePin,
): { meeting: Row; message: Row } | null {
  const inputs = consultationInputs(e);
  if (inputs.status !== "AVAILABLE") return null;
  const references = inputs.questions
    .flatMap((q) => [q.ref, ...q.responses.map((r) => r.ref)])
    .filter((ref) => sameMessagePin(ref, pin));
  if (references.length !== 1) return null;
  const meetings = e.meetings.filter((m) => m.id === pin.meeting_id);
  if (meetings.length !== 1) return null;
  const messages = (
    Array.isArray(meetings[0].messages) ? (meetings[0].messages as Row[]) : []
  ).filter((m) => m.id === pin.message_id);
  return messages.length === 1
    ? { meeting: meetings[0], message: messages[0] }
    : null;
}
export const consultationRelationLabels: Record<string, string> = {
  ANSWERS: "Company contact states an answer",
  CLARIFIES: "Company contact states a clarification",
  CORRECTS: "Company contact states a correction",
  CANNOT_ESTABLISH: "Company contact cannot establish the requested fact",
};

export function sameConsultation(
  a: Consultation | null | undefined,
  b: Consultation | null | undefined,
): boolean {
  if (a == null || b == null) return a == null && b == null;
  return (
    a.kind === b.kind &&
    sameMessagePin(a.question_ref, b.question_ref) &&
    (a.response_ref == null || b.response_ref == null
      ? a.response_ref == null && b.response_ref == null
      : sameMessagePin(a.response_ref, b.response_ref))
  );
}
