import { expect, it } from "vitest";
import type { Engagement } from "./api";
import {
  assertSelectedHistoryIntegrityReference, comparisonHistoryPin, validComparisonHistory,
  sameComparisonHistory, historyIntegrityRows, assertAssessmentOptions, assertAssessmentRecord,
  assessmentDocumentHistoryMatches, assessmentSavePayload, emptyAssessment,
  type SelectedHistoryIntegrityReference, type AssessmentDocument,
  type PinnedAssessmentOptions, type AssessmentRecord,
} from "./instructorAssessments";
import { comparisonPage, type ComparisonHeader } from "./instructorComparisonTransport";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { SelectedHistoryIntegrityRows } from "./InstructorComparison";

const a = "a".repeat(64), b = "b".repeat(64), c = "c".repeat(64);
const engagement = { id: "E", revision: 3 } as Engagement;
const reference: SelectedHistoryIntegrityReference = {
  schema: "SH_SELECTED_HISTORY_INTEGRITY_REFERENCE_V1",
  kind: "MANAGED_STORE_CHECKPOINT",
  algorithm: "SH_VERIFIED_EVENT_CHAIN_AND_CANONICAL_STATE_V1",
  engagement_id: "E", revision: 1,
  selected_event_sha256: a, selected_request_sha256: b,
  state_storage: "CANONICAL_CODEC_GRAPH", selected_state_root_sha256: c,
  selected_state_sha256: a, selected_state_bytes: 2048,
  accepted_base_sha256: a, checkpoint_sha256: b,
};
const legacy = {
  schema_version: "1.0", engagement_id: "E", selected_history_revision: 1,
  selected_state_sha256: a, selected_history_sha256: b, selected_history_tip_sha256: a,
};
const current = {
  schema_version: "2.0", engagement_id: "E", selected_history_revision: 1,
  selected_state_sha256: a, selected_history_integrity_reference: reference,
  selected_history_tip_sha256: a,
};
const optionsCommon = {
  engagement_id: "E", current_engagement_revision: 3, learner_revision: 1,
  key_pin: a, rubric_sha256: a, inventory_sha256: a,
  audited_actor_id: "L", bound_revision: 0,
  selected_state_sha256: a, selected_history_tip_sha256: a,
  issues: [{ id: "I", claim: "Authored", control_ids: ["C"], uncertainty: "Unvalidated" }],
  expectations: [{ id: "X", issue_ids: ["I"], procedure: "Authored", acceptable_alternatives: [] }],
  references: [],
};
const legacyOptions: PinnedAssessmentOptions = { ...optionsCommon, selected_history_sha256: b };
const currentOptions: PinnedAssessmentOptions = {
  ...optionsCommon, history_integrity_format: "SELECTED_HISTORY_INTEGRITY_REFERENCE_V2",
  selected_history_integrity_reference: reference,
};
function document(v2: boolean): AssessmentDocument {
  const common = {
    id: "A", version: 1, actor_id: "INSTRUCTOR", engagement_id: "E", recorded_at: "2026-10-07",
    predecessor: null, authored: { ...emptyAssessment(), title: "Unvalidated instructor judgment" },
    selected_issues: [], selected_expectations: [], references: [], qualification: "UNVALIDATED",
    pins: { key_pin: a, rubric_sha256: a, inventory_sha256: a, audited_actor_id: "L",
      learner_revision: 1, selected_state_sha256: a, selected_history_tip_sha256: a, bound_revision: 0 },
  };
  return v2 ? { ...common, schema: "INSTRUCTOR_AUTHORED_ASSESSMENT_V2",
    pins: { ...common.pins, selected_history_integrity_reference: reference } } :
    { ...common, schema: "INSTRUCTOR_AUTHORED_ASSESSMENT_V1",
      pins: { ...common.pins, selected_history_sha256: b } };
}
function record(d: AssessmentDocument): AssessmentRecord {
  return { id: "A", engagement_id: "E", version: 1, sha256: a, predecessor: null,
    saved_engagement_revision: 3, current_engagement_revision: 3, learner_revision: 1,
    context_status: "CURRENT", personal_content_visible: true, correction_allowed: true,
    title: d.authored.title, document: d };
}
const descriptor = { family: "sources", count: 1, sha256: a };
function pagePair(history: Record<string, unknown>): [ComparisonHeader, ComparisonHeader] {
  const header: ComparisonHeader = {
    ...history, status: "DETERMINISTIC_LINK_INVENTORY_ONLY", audited_actor_id: "L",
    binding_manifest_sha256: a, bound_revision: 0, current_revision: 3,
    grading: "NOT_PERFORMED", professional_validation: "UNVALIDATED",
    comparison_transport: { schema: "SH_INSTRUCTOR_COMPARISON_TRANSPORT_V1", view: "SUMMARY",
      inventory_sha256: a, complete_inventory_changed: false, response_max_bytes: 4 * 1024 * 1024 },
  };
  const page: ComparisonHeader = { ...header,
    comparison_transport: { ...header.comparison_transport!, view: "DETAIL" },
    page: { family: "sources", target_sha256: a, total: 1, offset: 0, next_offset: null, rows: [{ id: "S" }] },
  };
  return [header, page];
}
it("preserves actual V1 options, records, display and detail identity", () => {
  const h = comparisonHistoryPin(legacy), d = document(false), [header, page] = pagePair(legacy);
  expect(validComparisonHistory(legacy)).toBe(true);
  expect(assertAssessmentOptions(legacyOptions, engagement, a, "L", 0, h)).toBe(legacyOptions);
  expect(assessmentDocumentHistoryMatches(d, h, "E")).toBe(true);
  expect(assertAssessmentRecord(record(d), engagement, a).document).toBe(d);
  expect(historyIntegrityRows(h)).toEqual([{ label: "History prefix", value: b }]);
  expect(comparisonPage(page, header, descriptor, 0).rows).toEqual([{ id: "S" }]);
});
it("rejects V1 history tampering in options, document receipt and detail page", () => {
  const h = comparisonHistoryPin(legacy), d = document(false), [header, page] = pagePair(legacy);
  expect(() => assertAssessmentOptions({ ...legacyOptions, selected_history_sha256: c },
    engagement, a, "L", 0, h)).toThrow();
  expect(assessmentDocumentHistoryMatches({ ...d, pins: { ...d.pins, selected_history_sha256: c } } as AssessmentDocument,
    h, "E")).toBe(false);
  expect(() => comparisonPage({ ...page, selected_history_sha256: c }, header, descriptor, 0)).toThrow();
});
it("accepts V2 exact options, record and detail references without a legacy SHA", () => {
  const h = comparisonHistoryPin(current), d = document(true), [header, page] = pagePair(current);
  expect(validComparisonHistory(current)).toBe(true);
  expect(h).not.toHaveProperty("history_sha256");
  expect(assertAssessmentOptions(currentOptions, engagement, a, "L", 0, h)).toBe(currentOptions);
  expect(assessmentDocumentHistoryMatches(d, h, "E")).toBe(true);
  expect(assertAssessmentRecord(record(d), engagement, a).document).toBe(d);
  expect(comparisonPage(page, header, descriptor, 0).rows).toHaveLength(1);
});
it("accepts canonical typed equality independent of JSON object key order", () => {
  const reordered = Object.fromEntries(Object.entries(reference).reverse());
  expect(sameComparisonHistory({ ...current, selected_history_integrity_reference: reordered }, current)).toBe(true);
});
it("accepts the exact root-base and raw-state variants", () => {
  const base = { ...reference, kind: "ROOT_ACCEPTED_BASE", checkpoint_sha256: a };
  const raw = { ...base, state_storage: "RAW_CANONICAL_JSON", selected_state_root_sha256: null };
  expect(assertSelectedHistoryIntegrityReference(base, "E", 1, a, a)).toBe(base);
  expect(assertSelectedHistoryIntegrityReference(raw, "E", 1, a, a)).toBe(raw);
});
const invalidReferences: [string, unknown][] = [
  ["missing", undefined], ["null", null], ["array", []],
  ["wrong schema", { ...reference, schema: "OTHER" }],
  ["wrong kind", { ...reference, kind: "OTHER" }],
  ["wrong algorithm", { ...reference, algorithm: "SHA256" }],
  ["wrong engagement", { ...reference, engagement_id: "OTHER" }],
  ["wrong revision", { ...reference, revision: 2 }],
  ["boolean revision", { ...reference, revision: true }],
  ["unsafe revision", { ...reference, revision: Number.MAX_SAFE_INTEGER + 1 }],
  ["wrong state", { ...reference, selected_state_sha256: b }],
  ["wrong event", { ...reference, selected_event_sha256: b }],
  ["bad request SHA", { ...reference, selected_request_sha256: "wrong" }],
  ["unknown storage", { ...reference, state_storage: "OTHER" }],
  ["graph null root", { ...reference, selected_state_root_sha256: null }],
  ["raw nonnull root", { ...reference, state_storage: "RAW_CANONICAL_JSON" }],
  ["zero bytes", { ...reference, selected_state_bytes: 0 }],
  ["boolean bytes", { ...reference, selected_state_bytes: true }],
  ["fractional bytes", { ...reference, selected_state_bytes: 1.5 }],
  ["unsafe bytes", { ...reference, selected_state_bytes: Number.MAX_SAFE_INTEGER + 1 }],
  ["bad base SHA", { ...reference, accepted_base_sha256: "wrong" }],
  ["bad checkpoint SHA", { ...reference, checkpoint_sha256: "wrong" }],
  ["root base checkpoint mismatch", { ...reference, kind: "ROOT_ACCEPTED_BASE" }],
  ["extra private field", { ...reference, private_path: "/fictional" }],
  ["missing request field", Object.fromEntries(Object.entries(reference).filter(([k]) => k !== "selected_request_sha256"))],
];
for (const [name, invalid] of invalidReferences) it(`rejects ${name} at each V2 guard`, () => {
  const h = comparisonHistoryPin(current), d = document(true), [header, page] = pagePair(current);
  expect(validComparisonHistory({ ...current, selected_history_integrity_reference: invalid })).toBe(false);
  expect(() => assertAssessmentOptions({ ...currentOptions, selected_history_integrity_reference: invalid } as PinnedAssessmentOptions,
    engagement, a, "L", 0, h)).toThrow();
  const changed = { ...d, pins: { ...d.pins, selected_history_integrity_reference: invalid } } as AssessmentDocument;
  expect(assessmentDocumentHistoryMatches(changed, h, "E")).toBe(false);
  expect(() => assertAssessmentRecord(record(changed), engagement, a)).toThrow();
  expect(() => comparisonPage({ ...page, selected_history_integrity_reference: invalid }, header, descriptor, 0)).toThrow();
});
for (const patch of [
  { selected_request_sha256: c }, { selected_state_root_sha256: b },
  { selected_state_bytes: 2049 }, { accepted_base_sha256: c }, { checkpoint_sha256: c },
  { kind: "ROOT_ACCEPTED_BASE", checkpoint_sha256: a },
  { state_storage: "RAW_CANONICAL_JSON", selected_state_root_sha256: null },
]) it(`rejects a valid but changed full reference: ${Object.keys(patch).join(",")}`, () => {
  const changed = { ...reference, ...patch }, h = comparisonHistoryPin(current), d = document(true);
  const [header, page] = pagePair(current);
  expect(validComparisonHistory({ ...current, selected_history_integrity_reference: changed })).toBe(true);
  expect(sameComparisonHistory({ ...current, selected_history_integrity_reference: changed }, current)).toBe(false);
  expect(() => assertAssessmentOptions({ ...currentOptions, selected_history_integrity_reference: changed } as PinnedAssessmentOptions,
    engagement, a, "L", 0, h)).toThrow();
  expect(assessmentDocumentHistoryMatches({ ...d, pins: { ...d.pins, selected_history_integrity_reference: changed } } as AssessmentDocument,
    h, "E")).toBe(false);
  expect(() => comparisonPage({ ...page, selected_history_integrity_reference: changed }, header, descriptor, 0)).toThrow();
});
it("rejects missing, unknown or mixed format discriminants and absent-field equality", () => {
  const h = comparisonHistoryPin(current), d = document(true), [header, page] = pagePair(current);
  for (const patch of [
    { schema_version: undefined }, { schema_version: "3.0" },
    { selected_history_sha256: b }, { selected_history_sha256: undefined },
  ]) expect(validComparisonHistory({ ...current, ...patch })).toBe(false);
  for (const format of [undefined, "OTHER"]) expect(() => assertAssessmentOptions(
    { ...currentOptions, history_integrity_format: format } as PinnedAssessmentOptions,
    engagement, a, "L", 0, h)).toThrow();
  expect(assessmentDocumentHistoryMatches({ ...d, schema: "INSTRUCTOR_AUTHORED_ASSESSMENT_V1" } as AssessmentDocument,
    h, "E")).toBe(false);
  expect(assessmentDocumentHistoryMatches(d, h, "OTHER")).toBe(false);
  expect(() => comparisonPage({ ...page, selected_history_integrity_reference: undefined },
    { ...header, selected_history_integrity_reference: undefined }, descriptor, 0)).toThrow();
});
it("does not display V2 as the legacy prefix digest", () => {
  const rows = historyIntegrityRows(comparisonHistoryPin(current));
  expect(rows).toContainEqual({ label: "Accepted base", value: a });
  expect(rows).toContainEqual({ label: "Selected checkpoint", value: b });
  expect(rows.map(r => r.label)).not.toContain("History prefix");
  expect(() => historyIntegrityRows({ ...comparisonHistoryPin(current), history_integrity_reference: undefined } as never)).toThrow();
});
it("preserves the exact save request envelope for V1 and V2", () => {
  const draft = { ...emptyAssessment(), title: "Unvalidated", issue_ids: ["I"], expectation_ids: ["X"],
    dimensions: emptyAssessment().dimensions.map(row => ({ ...row, assessment: "Not assessed", rationale: "Not evaluated" })) };
  const before = assessmentSavePayload(draft, legacyOptions, "unchanged-command");
  expect(assessmentSavePayload(draft, currentOptions, "unchanged-command")).toEqual(before);
  expect(before).not.toHaveProperty("selected_history_integrity_reference");
  expect(before).not.toHaveProperty("selected_history_sha256");
});
it("renders the unchanged V1 prefix markup without an extra layout wrapper", () => {
  expect(renderToStaticMarkup(createElement(SelectedHistoryIntegrityRows,
    { history: comparisonHistoryPin(legacy) }))).toBe(`<dt>History prefix</dt><dd><code>${b}</code></dd>`);
});
it("renders the actual V2 reference display without a legacy prefix label", () => {
  const markup = renderToStaticMarkup(createElement(SelectedHistoryIntegrityRows,
    { history: comparisonHistoryPin(current) }));
  expect(markup).toContain("History integrity reference");
  expect(markup).toContain("Verified recorded update");
  expect(markup).toContain(`<dt>Accepted base</dt><dd><code>${a}</code></dd>`);
  expect(markup).toContain(`<dt>Selected checkpoint</dt><dd><code>${b}</code></dd>`);
  expect(markup).not.toContain("History prefix");
});
