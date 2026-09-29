import { expect, it } from "vitest";
import type { Engagement } from "./api";
import {
  assessmentDimensions,
  emptyAssessment,
  validateAssessmentDraft,
  assessmentSavePayload,
  assertAssessmentOptions,
  assertAssessmentRecord,
  type PinnedAssessmentOptions,
  type AssessmentRecord,
} from "./instructorAssessments";
const pin = "a".repeat(64),
  e = { id: "E", revision: 3 } as Engagement,
  h = {
    revision: 1,
    state_sha256: pin,
    history_sha256: pin,
    event_sha256: pin,
  };
const options: PinnedAssessmentOptions = {
  engagement_id: "E",
  current_engagement_revision: 3,
  learner_revision: 1,
  key_pin: pin,
  rubric_sha256: pin,
  inventory_sha256: pin,
  selected_state_sha256: pin,
  selected_history_sha256: pin,
  selected_history_tip_sha256: pin,
  audited_actor_id: "L",
  bound_revision: 0,
  issues: [
    {
      id: "I",
      claim: "Authored",
      control_ids: ["C"],
      uncertainty: "Unvalidated",
    },
  ],
  expectations: [
    {
      id: "X",
      issue_ids: ["I"],
      procedure: "Authored procedure",
      acceptable_alternatives: [],
    },
  ],
  references: [
    {
      id: "R",
      kind: "workpaper",
      record_id: "W",
      version: 1,
      inventory_sha256: pin,
      content_sha256: pin,
      relation: "EXACT_RECORDED_WORKPAPER_VERSION",
      expectation_ids: ["X"],
    },
    {
      id: "REQUEST",
      kind: "request",
      record_id: "PBC",
      version: null,
      inventory_sha256: pin,
      content_sha256: null,
      relation: "CONTROL_ASSOCIATION_ONLY",
      expectation_ids: ["X"],
    },
  ],
};
function draft() {
  return {
    ...emptyAssessment(),
    title: "Instructor interpretation",
    issue_ids: ["I"],
    expectation_ids: ["X"],
    dimensions: assessmentDimensions.map((dimension) => ({
      dimension,
      assessment: "Not assessed",
      rationale: "No independent evaluation yet",
      reference_ids: dimension === "documentation" ? ["R"] : [],
    })),
  };
}
it("starts blank and never infers an assessment from technical links", () => {
  expect(
    emptyAssessment().dimensions.every(
      (d) =>
        d.assessment === "" &&
        d.rationale === "" &&
        d.reference_ids.length === 0,
    ),
  ).toBe(true);
  expect(() => validateAssessmentDraft(emptyAssessment(), options)).toThrow();
  expect(
    validateAssessmentDraft(draft(), options).dimensions[0].assessment,
  ).toBe("Not assessed");
});
it("pins selected historical work without inventing missing content digests", () => {
  expect(assertAssessmentOptions(options, e, pin, "L", 0, h)).toBe(options);
  const payload = assessmentSavePayload(draft(), options, "command");
  expect(payload.learner_revision).toBe(1);
  expect(payload.inventory_sha256).toBe(pin);
  expect(options.references[1].content_sha256).toBeNull();
  expect(payload).not.toHaveProperty("score");
});
it("rejects missing dimension rationale, foreign refs and unrelated alternative/defect references", () => {
  for (const mutate of [
    (d: ReturnType<typeof draft>) => d.dimensions.pop(),
    (d: ReturnType<typeof draft>) => (d.dimensions[0].rationale = ""),
    (d: ReturnType<typeof draft>) =>
      (d.dimensions[0].reference_ids = ["FOREIGN"]),
    (d: ReturnType<typeof draft>) => (d.expectation_ids = ["MISSING"]),
  ]) {
    const d = draft();
    mutate(d);
    expect(() => validateAssessmentDraft(d, options)).toThrow();
  }
  expect(() =>
    validateAssessmentDraft(
      {
        ...draft(),
        alternatives: [
          {
            expectation_id: "OTHER",
            description: "Alternative",
            rationale: "Reason",
            reference_ids: [],
          },
        ],
      },
      options,
    ),
  ).toThrow();
});
it("rejects stale selected revision, history or rubric choices", () => {
  for (const patch of [
    { current_engagement_revision: 2 },
    { learner_revision: 2 },
    { selected_state_sha256: "b".repeat(64) },
    { key_pin: "b".repeat(64) },
    { audited_actor_id: "OTHER" },
  ])
    expect(() =>
      assertAssessmentOptions({ ...options, ...patch }, e, pin, "L", 0, h),
    ).toThrow();
});
it("unavailable assessment metadata cannot disclose title or document", () => {
  const row: AssessmentRecord = {
    id: "A",
    engagement_id: "E",
    version: 1,
    sha256: pin,
    predecessor: null,
    saved_engagement_revision: 3,
    current_engagement_revision: 3,
    learner_revision: 1,
    context_status: "KEY_CHANGED",
    personal_content_visible: false,
    correction_allowed: false,
  };
  expect(assertAssessmentRecord(row, e, pin)).toBe(row);
  expect(() =>
    assertAssessmentRecord({ ...row, title: "Private judgment" }, e, pin),
  ).toThrow();
});
it("accepts only typed historical support relations and preserves exact pins", () => {
  for (const [kind, relation] of [
    ["workpaper", "EXACT_AUTHORED_TASK_WORKPAPER_VERSION"],
    ["sample_execution", "EXACT_RECORDED_ITEM_OR_AUTHORED_TASK_LINK"],
    ["finding", "DIRECT_RECORDED_FINDING_EVIDENCE_ID"],
    ["remediation", "DIRECT_RECORDED_REMEDIATION_EVIDENCE_ID"],
  ]) {
    const ref = { ...options.references[0], kind, relation };
    const o = { ...options, references: [ref] };
    expect(assertAssessmentOptions(o, e, pin, "L", 0, h).references[0]).toEqual(
      ref,
    );
    expect(
      assessmentSavePayload(draft(), o, "exact").dimensions[4].reference_ids,
    ).toEqual(["R"]);
    for (const patch of [
      { relation: "CONTROL_ASSOCIATION_ONLY" },
      { content_sha256: null },
      { version: true },
      { inventory_sha256: "wrong" },
      { expectation_ids: ["UNSELECTABLE"] },
    ]) {
      expect(() =>
        assertAssessmentOptions(
          { ...o, references: [{ ...ref, ...patch }] as typeof o.references },
          e,
          pin,
          "L",
          0,
          h,
        ),
      ).toThrow();
    }
  }
  expect(() =>
    assertAssessmentOptions(
      {
        ...options,
        references: [{ ...options.references[0], kind: "__proto__" }],
      },
      e,
      pin,
      "L",
      0,
      h,
    ),
  ).toThrow();
});
