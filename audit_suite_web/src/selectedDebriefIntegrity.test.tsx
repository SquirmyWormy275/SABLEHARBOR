import { expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { DebriefDocument } from "./DebriefDocument";
import {
  debriefPreviewMatches, validSelectedDebriefHistory,
  type SelectedDebrief, type DebriefPreview, type DebriefDraft, type DebriefOptions,
} from "./instructorDebrief";
import type { SelectedHistoryIntegrityReference } from "./instructorAssessments";
const a = "a".repeat(64), b = "b".repeat(64), c = "c".repeat(64);
const reference: SelectedHistoryIntegrityReference = {
  schema: "SH_SELECTED_HISTORY_INTEGRITY_REFERENCE_V1", kind: "MANAGED_STORE_CHECKPOINT",
  algorithm: "SH_VERIFIED_EVENT_CHAIN_AND_CANONICAL_STATE_V1", engagement_id: "E", revision: 1,
  selected_event_sha256: a, selected_request_sha256: b,
  state_storage: "CANONICAL_CODEC_GRAPH", selected_state_root_sha256: c,
  selected_state_sha256: a, selected_state_bytes: 2048, accepted_base_sha256: a, checkpoint_sha256: b,
};
const draft: DebriefDraft = {
  recipient_id: "L", expected_revision: 3, learner_revision: 1, title: "Fictional unvalidated explanation",
  predecessor_release_id: null, sections: [{ issue_ids: ["I"], expectation_ids: ["X"],
    explanation: "Instructor interpretation", limitations: "Not evaluated", prompts: [], annotations: [] }],
};
const options: DebriefOptions = {
  engagement_id: "E", revision: 3, key_manifest_sha256: a,
  recipients: [{ id: "L", name: "Fictional learner" }], issues: [{ id: "I", title: "Authored" }],
  expectations: [{ id: "X", title: "Authored procedure", issue_ids: ["I"] }], artifacts: [],
};
function preview(v2: boolean): DebriefPreview {
  const common = {
    source_references: [], title: draft.title, version: 1, predecessor: null, key_manifest_sha256: a,
    learner: { actor_id: "L", revision: 1, state_sha256: a, event_sha256: a, qualification: "UNVALIDATED" },
    sections: draft.sections.map(section => ({ ...section,
      issues: [{ id: "I", control_ids: ["C"], claim: "Authored" }],
      expectations: [{ id: "X", issue_ids: ["I"], procedure: "Authored", acceptable_alternatives: [] }] })),
    qualification: "UNVALIDATED",
  };
  const document: SelectedDebrief = v2 ? {
    ...common, schema: "SELECTED_INSTRUCTOR_DEBRIEF_V2",
    learner: { ...common.learner, history_integrity_reference: reference },
  } : { ...common, schema: "SELECTED_INSTRUCTOR_DEBRIEF_V1",
    learner: { ...common.learner, history_sha256: a } };
  return { delivered: false, preview_sha256: a, preview: {
    id: "P", engagement_id: "E", instructor_id: "T", recipient_id: "L", revision: 3,
    key_manifest_sha256: a, expires_at: "2099-01-01T00:00:00Z",
    content: { stage: "EXPLANATION", text: draft.title, pointers: [], document },
  } };
}
it("preserves the exact V1 preview and historical SHA display", () => {
  const p = preview(false), doc = p.preview.content.document;
  expect(validSelectedDebriefHistory(doc, "E")).toBe(true);
  expect(debriefPreviewMatches(p, draft, options, "E", "T")).toBe(true);
  const markup = renderToStaticMarkup(createElement(DebriefDocument, { document: doc }));
  expect(markup).toContain(`<p>History SHA256 ${a} · event SHA256 ${a}</p>`);
  expect(markup).not.toContain("History integrity reference");
});
it("accepts exact V2 preview metadata and honestly displays its reference", () => {
  const p = preview(true), doc = p.preview.content.document;
  expect(validSelectedDebriefHistory(doc, "E")).toBe(true);
  expect(debriefPreviewMatches(p, draft, options, "E", "T")).toBe(true);
  expect(doc.learner).not.toHaveProperty("history_sha256");
  const markup = renderToStaticMarkup(createElement(DebriefDocument, { document: doc }));
  expect(markup).toContain("History integrity reference");
  expect(markup).toContain("Verified recorded update");
  expect(markup).not.toContain("History SHA256");
});
it("retains the verified baseline and raw-state reference variants", () => {
  const p = preview(true), doc = p.preview.content.document;
  doc.learner.history_integrity_reference = { ...reference, kind: "ROOT_ACCEPTED_BASE",
    checkpoint_sha256: a, state_storage: "RAW_CANONICAL_JSON", selected_state_root_sha256: null };
  expect(debriefPreviewMatches(p, draft, options, "E", "T")).toBe(true);
  expect(renderToStaticMarkup(createElement(DebriefDocument, { document: doc }))).toContain("Verified baseline");
});
for (const [name, changed] of [
  ["missing", undefined], ["null", null], ["wrong schema", { ...reference, schema: "OTHER" }],
  ["wrong kind", { ...reference, kind: "OTHER" }],
  ["wrong algorithm", { ...reference, algorithm: "SHA256" }],
  ["foreign engagement", { ...reference, engagement_id: "OTHER" }],
  ["wrong revision", { ...reference, revision: 2 }],
  ["boolean revision", { ...reference, revision: true }],
  ["wrong state", { ...reference, selected_state_sha256: b }],
  ["wrong event", { ...reference, selected_event_sha256: b }],
  ["bad request digest", { ...reference, selected_request_sha256: "bad" }],
  ["graph null root", { ...reference, selected_state_root_sha256: null }],
  ["unknown storage", { ...reference, state_storage: "OTHER" }],
  ["zero state bytes", { ...reference, selected_state_bytes: 0 }],
  ["extra field", { ...reference, private_path: "/fictional" }],
  ["root checkpoint mismatch", { ...reference, kind: "ROOT_ACCEPTED_BASE" }],
] as const) it(`rejects V2 debrief ${name}`, () => {
  const p = preview(true), doc = p.preview.content.document;
  doc.learner.history_integrity_reference = changed as never;
  expect(validSelectedDebriefHistory(doc, "E")).toBe(false);
  expect(debriefPreviewMatches(p, draft, options, "E", "T")).toBe(false);
});
it("rejects mixed V1/V2 learner fields and unknown debrief schemas", () => {
  for (const v2 of [false, true]) {
    const p = preview(v2), doc = p.preview.content.document;
    Object.assign(doc.learner, v2 ? { history_sha256: a } : { history_integrity_reference: reference });
    expect(debriefPreviewMatches(p, draft, options, "E", "T")).toBe(false);
  }
  const p = preview(true);
  Object.assign(p.preview.content.document, { schema: "OTHER" });
  expect(debriefPreviewMatches(p, draft, options, "E", "T")).toBe(false);
});
it("still rejects changed learner metadata, instructor, Key and selected sections", () => {
  for (const mutate of [
    (p: DebriefPreview) => { p.preview.content.document.learner.state_sha256 = b; },
    (p: DebriefPreview) => { p.preview.content.document.learner.event_sha256 = b; },
    (p: DebriefPreview) => { p.preview.content.document.learner.revision = 2; },
    (p: DebriefPreview) => { p.preview.instructor_id = "OTHER"; },
    (p: DebriefPreview) => { p.preview.key_manifest_sha256 = b; },
    (p: DebriefPreview) => { p.preview.content.document.sections[0].explanation = "Changed"; },
  ]) {
    const p = preview(true); mutate(p);
    expect(debriefPreviewMatches(p, draft, options, "E", "T")).toBe(false);
  }
});
