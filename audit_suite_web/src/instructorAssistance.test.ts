import { it, expect } from "vitest";
import type { Engagement } from "./api";
import {
  previewMatches,
  assistanceContext,
  validateAssistanceDraft,
  type AssistanceDraft,
  type AssistanceOptions,
  type ReleasePreview,
} from "./instructorAssistance";
const e = {
  id: "E",
  revision: 2,
  permissions: ["instruct"],
  scope: {},
} as Engagement;
const d: AssistanceDraft = {
  recipient_id: "L",
  expected_revision: 2,
  stage: "POINTER",
  text: "Inspect row one.",
  pointers: [{ kind: "artifact", id: "A", sha256: "a".repeat(64) }],
};
const options: AssistanceOptions = {
  engagement_id: "E",
  revision: 2,
  recipients: [{ id: "L", name: "Learner" }],
  tasks: [],
  artifacts: [{ id: "A", name: "Original", sha256: "a".repeat(64) }],
};
function preview(): ReleasePreview {
  return {
    preview: {
      id: "P",
      engagement_id: "E",
      instructor_id: "I",
      recipient_id: "L",
      revision: 2,
      expires_at: new Date(Date.now() + 60000).toISOString(),
      content: {
        stage: d.stage,
        text: d.text,
        pointers: [{ id: "A", sha256: "a".repeat(64), kind: "artifact" }],
      },
    },
    preview_sha256: "b".repeat(64),
    delivered: false,
  };
}
it("accepts server object key ordering without changing explicit pointers", () =>
  expect(previewMatches(preview(), d, e, "I")).toBe(true));
it("invalidates preview for recipient/text/pointer/revision/actor changes and expiry", () => {
  for (const patch of [
    { recipient_id: "other" },
    { text: "Edited" },
    { pointers: [] },
    { expected_revision: 3 },
  ])
    expect(previewMatches(preview(), { ...d, ...patch }, e, "I")).toBe(false);
  expect(previewMatches(preview(), d, e, "other")).toBe(false);
  const p = preview();
  p.preview.expires_at = "2000-01-01";
  expect(previewMatches(p, d, e, "I")).toBe(false);
});
it("requires server-recognized exact pointers and named recipients", () => {
  expect(validateAssistanceDraft(d, options)).toBe(d);
  for (const patch of [
    { recipient_id: "foreign" },
    { pointers: [{ kind: "artifact" as const, id: "A", sha256: "changed" }] },
    { stage: "HINT" as const },
    { text: "" },
  ])
    expect(() =>
      validateAssistanceDraft({ ...d, ...patch }, options),
    ).toThrow();
});
it("clears context for actor/permission/branch/revision changes", () => {
  for (const next of [
    { ...e, revision: 3 },
    { ...e, permissions: ["learn"] },
    { ...e, company_source_binding: { branch: "other" } },
  ])
    expect(assistanceContext(next, "I")).not.toBe(assistanceContext(e, "I"));
  expect(assistanceContext(e, "L")).not.toBe(assistanceContext(e, "I"));
});

import { assistancePointer } from "./instructorAssistance";
it("opens only exact authorized artifact and authoritative task pins", () => {
  const state = {
    ...e,
    artifacts: [{ id: "A", status: "AVAILABLE", sha256: "p" }],
    tasks: [{ id: "T" }],
    sample_execution_inputs: {
      engagement_id: "E",
      engagement_revision: 2,
      tasks: [{ task_id: "T", task_digest: "t" }],
    },
  } as unknown as Engagement;
  expect(
    assistancePointer(state, { kind: "artifact", id: "A", sha256: "p" })
      ?.collection,
  ).toBe("artifacts");
  expect(
    assistancePointer(state, { kind: "artifact", id: "A", sha256: "changed" }),
  ).toBeNull();
  expect(
    assistancePointer(state, { kind: "task", id: "T", sha256: "t" })
      ?.collection,
  ).toBe("tasks");
  expect(
    assistancePointer(
      { ...state, revision: 3 },
      { kind: "task", id: "T", sha256: "t" },
    ),
  ).toBeNull();
});
