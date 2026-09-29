import { describe, it, expect } from "vitest";
import type { Engagement } from "./api";
import {
  eligibleQuestions,
  validConsultation,
  resolveConsultationMessage,
  consultationAuthority,
  consultationRelationLabels,
} from "./companyConsultation";
const q = { meeting_id: "M1", message_id: "Q", sha256: "a".repeat(64) },
  r = { meeting_id: "M1", message_id: "R", sha256: "b".repeat(64) };
const e = {
  id: "E",
  revision: 1,
  scope: {},
  permissions: ["learn"],
  meetings: [
    {
      id: "M1",
      person_id: "P1",
      messages: [
        { id: "Q", role: "user" },
        { id: "R", role: "assistant", claim_type: "PERSONA_STATEMENT" },
      ],
    },
    { id: "M2", person_id: "P2", messages: [] },
  ],
  company_consultation_inputs: {
    status: "AVAILABLE",
    questions: [
      {
        ref: q,
        person_id: "P1",
        content: "Question",
        meeting_title: "Earlier",
        responses: [{ ref: r, person_id: "P1", content: "Reply" }],
      },
    ],
  },
} as unknown as Engagement;
describe("exact learner-requested consultation", () => {
  it("requires another contact for referral and explicit reply for correction", () => {
    expect(eligibleQuestions(e, "M1", "REFERRAL")).toHaveLength(0);
    expect(
      validConsultation(e, "M2", {
        kind: "REFERRAL",
        question_ref: q,
        response_ref: null,
      }),
    ).toBe(true);
    expect(
      validConsultation(e, "M2", {
        kind: "CORRECTION_REQUEST",
        question_ref: q,
        response_ref: null,
      }),
    ).toBe(false);
    expect(
      validConsultation(e, "M1", {
        kind: "CORRECTION_REQUEST",
        question_ref: q,
        response_ref: r,
      }),
    ).toBe(true);
  });
  it("rejects changed pins and an unrelated reply without rehashing text", () => {
    expect(
      validConsultation(e, "M2", {
        kind: "REFERRAL",
        question_ref: { ...q, sha256: "c".repeat(64) },
        response_ref: null,
      }),
    ).toBe(false);
    expect(
      validConsultation(e, "M2", {
        kind: "CORRECTION_REQUEST",
        question_ref: q,
        response_ref: { ...r, message_id: "OTHER" },
      }),
    ).toBe(false);
  });
  it("does not substitute latest/missing or ambiguous historical messages", () => {
    expect(resolveConsultationMessage(e, r)?.message.id).toBe("R");
    expect(
      resolveConsultationMessage(
        { ...e, meetings: [{ id: "M1", messages: [{ id: "Q" }] }] },
        r,
      ),
    ).toBeNull();
    expect(
      resolveConsultationMessage(
        { ...e, meetings: [...e.meetings, e.meetings[0]] },
        r,
      ),
    ).toBeNull();
  });
  it("unavailable projection gives no eligible choices or navigation", () => {
    const unavailable = {
      ...e,
      company_consultation_inputs: {
        status: "INPUT_LIMIT_EXCEEDED",
        questions: [],
      },
    };
    expect(eligibleQuestions(unavailable, "M2", "REFERRAL")).toEqual([]);
    expect(resolveConsultationMessage(unavailable, r)).toBeNull();
  });
  it("isolates viewer, target and source context without discarding for unrelated revisions", () => {
    expect(consultationAuthority(e, "A", "M2")).not.toBe(
      consultationAuthority(e, "B", "M2"),
    );
    expect(consultationAuthority(e, "A", "M2")).not.toBe(
      consultationAuthority(e, "A", "M1"),
    );
    expect(consultationAuthority(e, "A", "M2")).toBe(
      consultationAuthority({ ...e, revision: 2 }, "A", "M2"),
    );
    expect(consultationRelationLabels.CORRECTS).toBe(
      "Company contact states a correction",
    );
  });
});

import { sameConsultation } from "./companyConsultation";
it("compares exact consultation intent for pending retry guards", () => {
  const a = { kind: "REFERRAL" as const, question_ref: q, response_ref: null };
  expect(sameConsultation(null, undefined)).toBe(true);
  expect(sameConsultation(a, structuredClone(a))).toBe(true);
  expect(sameConsultation(a, null)).toBe(false);
  expect(
    sameConsultation(a, { ...a, kind: "CORRECTION_REQUEST", response_ref: r }),
  ).toBe(false);
  expect(
    sameConsultation(a, {
      ...a,
      question_ref: { ...q, sha256: "c".repeat(64) },
    }),
  ).toBe(false);
});
