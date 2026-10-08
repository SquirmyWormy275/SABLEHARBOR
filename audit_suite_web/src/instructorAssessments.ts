import type { Engagement } from "./api";
import { debriefPin, sameDebriefValue } from "./instructorDebrief";
export const assessmentDimensions = [
  "discovery",
  "evidence",
  "testing",
  "judgment",
  "documentation",
  "follow-through",
] as const;
export type AssessmentDimension = (typeof assessmentDimensions)[number];
export type Judgment = {
  dimension: AssessmentDimension;
  assessment: string;
  rationale: string;
  reference_ids: string[];
};
export type Alternative = {
  expectation_id: string;
  description: string;
  rationale: string;
  reference_ids: string[];
};
export type Override = {
  expectation_id: string;
  prior_interpretation: string;
  replacement: string;
  rationale: string;
  reference_ids: string[];
};
export type Defect = {
  issue_id: string;
  description: string;
  impact: string;
  rationale: string;
  reference_ids: string[];
};
export type AssessmentDraft = {
  title: string;
  issue_ids: string[];
  expectation_ids: string[];
  dimensions: Judgment[];
  alternatives: Alternative[];
  overrides: Override[];
  defects: Defect[];
  predecessor: null | { id: string; sha256: string };
};
export type AssessmentReference = {
  id: string;
  kind: string;
  record_id: string;
  version: number | null;
  inventory_sha256: string;
  content_sha256: string | null;
  relation: string;
  expectation_ids: string[];
};
export type AssessmentOptions = {
  engagement_id: string;
  current_engagement_revision: number;
  learner_revision: number;
  key_pin: string;
  rubric_sha256: string;
  inventory_sha256: string;
  issues: {
    id: string;
    claim: string;
    control_ids: string[];
    uncertainty: string;
  }[];
  expectations: {
    id: string;
    issue_ids: string[];
    procedure: string;
    acceptable_alternatives: string[];
  }[];
  references: AssessmentReference[];
  reference_catalogue?: AssessmentReferenceCatalogue;
};
export type AssessmentReferenceCatalogue = {
  schema: "ASSESSMENT_REFERENCE_CATALOGUE_V1";
  count: number;
  sha256: string;
  context_sha256: string;
};
export type AssessmentReferenceSelector = {
  query: string;
  expectation_ids: string[];
  reference_ids: string[];
};
export type AssessmentReferencePage = {
  reference_catalogue: AssessmentReferenceCatalogue;
  selector: AssessmentReferenceSelector;
  offset: number;
  total: number;
  next_offset: number | null;
  references: AssessmentReference[];
};
export type SelectedHistoryIntegrityReference = {
  schema: "SH_SELECTED_HISTORY_INTEGRITY_REFERENCE_V1";
  kind: "ROOT_ACCEPTED_BASE" | "MANAGED_STORE_CHECKPOINT";
  algorithm: "SH_VERIFIED_EVENT_CHAIN_AND_CANONICAL_STATE_V1";
  engagement_id: string;
  revision: number;
  selected_event_sha256: string;
  selected_request_sha256: string;
  selected_state_sha256: string;
  selected_state_bytes: number;
  accepted_base_sha256: string;
  checkpoint_sha256: string;
} & (
  | { state_storage: "CANONICAL_CODEC_GRAPH"; selected_state_root_sha256: string }
  | { state_storage: "RAW_CANONICAL_JSON"; selected_state_root_sha256: null }
);
export type ComparisonHistoryFields =
  | { schema_version?: "1.0"; selected_history_sha256: string; selected_history_integrity_reference?: never }
  | { schema_version: "2.0"; selected_history_sha256?: never; selected_history_integrity_reference: SelectedHistoryIntegrityReference };
export type AssessmentHistoryPin = {
  revision: number;
  state_sha256: string;
  event_sha256: string;
} & (
  | { history_integrity_format?: never; history_sha256: string; history_integrity_reference?: never }
  | { history_integrity_format: "SELECTED_HISTORY_INTEGRITY_REFERENCE_V2"; history_sha256?: never; history_integrity_reference: SelectedHistoryIntegrityReference }
);
const integrityReferenceKeys = [
  "schema", "kind", "algorithm", "engagement_id", "revision",
  "selected_event_sha256", "selected_request_sha256", "state_storage",
  "selected_state_root_sha256", "selected_state_sha256", "selected_state_bytes",
  "accepted_base_sha256", "checkpoint_sha256",
].sort();
export function assertSelectedHistoryIntegrityReference(
  value: unknown, engagementId: string, revision: number, state: string, event: string,
): SelectedHistoryIntegrityReference {
  const r = value as SelectedHistoryIntegrityReference;
  if (!r || typeof r !== "object" || Array.isArray(r) ||
      Object.keys(r).sort().join("|") !== integrityReferenceKeys.join("|") ||
      r.schema !== "SH_SELECTED_HISTORY_INTEGRITY_REFERENCE_V1" ||
      !["ROOT_ACCEPTED_BASE", "MANAGED_STORE_CHECKPOINT"].includes(r.kind) ||
      r.algorithm !== "SH_VERIFIED_EVENT_CHAIN_AND_CANONICAL_STATE_V1" ||
      typeof engagementId !== "string" || !engagementId || r.engagement_id !== engagementId ||
      !Number.isSafeInteger(revision) || revision < 0 || r.revision !== revision ||
      !Number.isSafeInteger(r.selected_state_bytes) || r.selected_state_bytes < 1 ||
      ![state, event, r.selected_state_sha256, r.selected_event_sha256,
        r.selected_request_sha256, r.accepted_base_sha256, r.checkpoint_sha256].every(debriefPin) ||
      r.selected_state_sha256 !== state || r.selected_event_sha256 !== event ||
      !(r.state_storage === "CANONICAL_CODEC_GRAPH" ? debriefPin(r.selected_state_root_sha256) :
        r.state_storage === "RAW_CANONICAL_JSON" && r.selected_state_root_sha256 === null) ||
      (r.kind === "ROOT_ACCEPTED_BASE" && r.checkpoint_sha256 !== r.accepted_base_sha256))
    throw Error("Selected history integrity reference does not match the protected context.");
  return r;
}
function responseHistoryPin(
  value: Record<string, unknown>, version: "1.0" | "2.0", engagementId: string, revision: number,
): AssessmentHistoryPin {
  const state = value.selected_state_sha256, event = value.selected_history_tip_sha256;
  if (typeof engagementId !== "string" || !engagementId ||
      !Number.isSafeInteger(revision) || revision < 0 || !debriefPin(state) || !debriefPin(event))
    throw Error("Exact selected history context required.");
  if (version === "2.0") {
    if (Object.prototype.hasOwnProperty.call(value, "selected_history_sha256"))
      throw Error("V2 integrity references must not be labelled as a legacy history digest.");
    const reference = assertSelectedHistoryIntegrityReference(
      value.selected_history_integrity_reference, engagementId, revision, state, event,
    );
    return { revision, state_sha256: state,
      history_integrity_format: "SELECTED_HISTORY_INTEGRITY_REFERENCE_V2",
      history_integrity_reference: reference, event_sha256: event };
  }
  if (!debriefPin(value.selected_history_sha256) ||
      Object.prototype.hasOwnProperty.call(value, "selected_history_integrity_reference"))
    throw Error("Exact legacy selected history digest required.");
  return { revision, state_sha256: state, history_sha256: value.selected_history_sha256, event_sha256: event };
}
export function comparisonHistoryPin(value: Record<string, unknown>): AssessmentHistoryPin {
  if (![undefined, "1.0", "2.0"].includes(value.schema_version as undefined | string))
    throw Error("Selected comparison history format is unavailable.");
  return responseHistoryPin(value, value.schema_version === "2.0" ? "2.0" : "1.0",
    value.engagement_id as string, value.selected_history_revision as number);
}
export function validComparisonHistory(value: Record<string, unknown>): boolean {
  try { comparisonHistoryPin(value); return true; } catch { return false; }
}
export function sameComparisonHistory(left: Record<string, unknown>, right: Record<string, unknown>): boolean {
  try {
    return left.engagement_id === right.engagement_id &&
      sameDebriefValue(comparisonHistoryPin(left), comparisonHistoryPin(right));
  } catch { return false; }
}
function validAssessmentHistoryPin(h: AssessmentHistoryPin): boolean {
  if (!h || !Number.isSafeInteger(h.revision) || h.revision < 0 ||
      !debriefPin(h.state_sha256) || !debriefPin(h.event_sha256)) return false;
  if (h.history_integrity_format === "SELECTED_HISTORY_INTEGRITY_REFERENCE_V2") {
    if (Object.prototype.hasOwnProperty.call(h, "history_sha256")) return false;
    try {
      assertSelectedHistoryIntegrityReference(h.history_integrity_reference,
        h.history_integrity_reference?.engagement_id, h.revision, h.state_sha256, h.event_sha256);
      return true;
    } catch { return false; }
  }
  return h.history_integrity_format === undefined && debriefPin(h.history_sha256) &&
    !Object.prototype.hasOwnProperty.call(h, "history_integrity_reference");
}
export function assessmentOptionsHistoryMatches(o: PinnedAssessmentOptions, h: AssessmentHistoryPin): boolean {
  try {
    if (!validAssessmentHistoryPin(h) ||
        ![undefined, "SELECTED_HISTORY_INTEGRITY_REFERENCE_V2"].includes(o.history_integrity_format)) return false;
    return sameDebriefValue(responseHistoryPin(o,
      o.history_integrity_format === "SELECTED_HISTORY_INTEGRITY_REFERENCE_V2" ? "2.0" : "1.0",
      o.engagement_id, o.learner_revision), h);
  } catch { return false; }
}
export function assessmentDocumentHistoryMatches(
  d: AssessmentDocument, h: AssessmentHistoryPin, engagementId: string,
): boolean {
  try {
    return d.engagement_id === engagementId && validAssessmentHistoryPin(h) &&
      ["INSTRUCTOR_AUTHORED_ASSESSMENT_V1", "INSTRUCTOR_AUTHORED_ASSESSMENT_V2"].includes(d.schema) &&
      sameDebriefValue(responseHistoryPin(d.pins,
        d.schema === "INSTRUCTOR_AUTHORED_ASSESSMENT_V2" ? "2.0" : "1.0",
        d.engagement_id, d.pins.learner_revision), h);
  } catch { return false; }
}
export function historyIntegrityRows(h: AssessmentHistoryPin): { label: string; value: string }[] {
  if (!validAssessmentHistoryPin(h)) throw Error("Exact selected history context required.");
  if (h.history_integrity_format === "SELECTED_HISTORY_INTEGRITY_REFERENCE_V2") {
    const r = h.history_integrity_reference;
    return [
      { label: "History integrity reference", value: "Verified event chain and canonical state" },
      { label: "Reference kind", value: r.kind === "ROOT_ACCEPTED_BASE" ? "Verified baseline" : "Verified recorded update" },
      { label: "Accepted base", value: r.accepted_base_sha256 },
      { label: "Selected checkpoint", value: r.checkpoint_sha256 },
    ];
  }
  return [{ label: "History prefix", value: h.history_sha256 }];
}
export function assessmentContext(
  e: Engagement,
  actor: string,
  key: string,
  history: AssessmentHistoryPin,
) {
  return JSON.stringify([
    actor,
    e.id,
    e.revision,
    e.permissions,
    e.scope,
    e.company_source_binding,
    e.evidence_acquisition,
    key,
    history,
  ]);
}
export function emptyAssessment(): AssessmentDraft {
  return {
    title: "",
    issue_ids: [],
    expectation_ids: [],
    dimensions: assessmentDimensions.map((dimension) => ({
      dimension,
      assessment: "",
      rationale: "",
      reference_ids: [],
    })),
    alternatives: [],
    overrides: [],
    defects: [],
    predecessor: null,
  };
}
export function validateAssessmentDraft(
  d: AssessmentDraft,
  o: AssessmentOptions,
) {
  const text = (x: string, n: number) =>
    typeof x === "string" && !!x.trim() && Array.from(x).length <= n;
  const unique = (a: string[]) => new Set(a).size === a.length;
  if (
    !text(d.title, 200) ||
    !d.issue_ids.length ||
    d.issue_ids.length > 10 ||
    d.expectation_ids.length > 10 ||
    !unique(d.issue_ids) ||
    !unique(d.expectation_ids) ||
    d.issue_ids.some(
      (id) => o.issues.filter((i) => i.id === id).length !== 1,
    ) ||
    d.expectation_ids.some((id) => {
      const rows = o.expectations.filter((i) => i.id === id);
      return (
        rows.length !== 1 ||
        rows[0].issue_ids.some((i) => !d.issue_ids.includes(i))
      );
    })
  )
    throw Error(
      "Choose explicit current issues and related expectations, and name this assessment.",
    );
  if (
    d.dimensions.length !== 6 ||
    !sameDebriefValue(
      [...d.dimensions.map((x) => x.dimension)].sort(),
      [...assessmentDimensions].sort(),
    )
  )
    throw Error(
      "All six dimensions require separate instructor-authored judgments.",
    );
  if (
    d.alternatives.length > 8 ||
    d.overrides.length > 8 ||
    d.defects.length > 8
  )
    throw Error("At most eight alternatives, overrides and defects each.");
  const refs = new Set<string>();
  const checkRefs = (ids: string[]) => {
    if (
      !Array.isArray(ids) ||
      !unique(ids) ||
      ids.some((id) => o.references.filter((r) => r.id === id).length !== 1)
    )
      throw Error("Use exact references from this historical inventory.");
    ids.forEach((id) => refs.add(id));
  };
  for (const row of d.dimensions) {
    if (!text(row.assessment, 2000) || !text(row.rationale, 4000))
      throw Error(
        "State an assessment and rationale for every dimension; explicitly describe anything not assessed.",
      );
    checkRefs(row.reference_ids);
  }
  for (const row of d.alternatives) {
    if (
      !d.expectation_ids.includes(row.expectation_id) ||
      !text(row.description, 2000) ||
      !text(row.rationale, 4000)
    )
      throw Error(
        "Alternatives require a selected expectation, description and rationale.",
      );
    checkRefs(row.reference_ids);
  }
  for (const row of d.overrides) {
    if (
      !d.expectation_ids.includes(row.expectation_id) ||
      !text(row.prior_interpretation, 2000) ||
      !text(row.replacement, 2000) ||
      !text(row.rationale, 4000)
    )
      throw Error(
        "Overrides require explicit prior and replacement interpretations with rationale.",
      );
    checkRefs(row.reference_ids);
  }
  for (const row of d.defects) {
    if (
      !d.issue_ids.includes(row.issue_id) ||
      !text(row.description, 2000) ||
      !text(row.impact, 2000) ||
      !text(row.rationale, 4000)
    )
      throw Error(
        "Defect flags require a selected issue, description, impact and rationale.",
      );
    checkRefs(row.reference_ids);
  }
  if (refs.size > 32)
    throw Error("Select no more than 32 distinct historical work references.");
  if (
    d.predecessor &&
    (!text(d.predecessor.id, 128) || !debriefPin(d.predecessor.sha256))
  )
    throw Error("Exact prior assessment identity required.");
  return structuredClone(d);
}
export type AssessmentDocument = {
  id: string;
  version: number;
  actor_id: string;
  engagement_id: string;
  recorded_at: string;
  predecessor: AssessmentDraft["predecessor"];
  pins: {
    key_pin: string;
    rubric_sha256: string;
    inventory_sha256: string;
    audited_actor_id: string;
    learner_revision: number;
    selected_state_sha256: string;
    selected_history_tip_sha256: string;
    bound_revision: number;
  };
  authored: Omit<AssessmentDraft, "predecessor">;
  selected_issues: AssessmentOptions["issues"];
  selected_expectations: AssessmentOptions["expectations"];
  references: AssessmentReference[];
  qualification: string;
} & (
  | { schema: "INSTRUCTOR_AUTHORED_ASSESSMENT_V1"; pins: { selected_history_sha256: string; selected_history_integrity_reference?: never } }
  | { schema: "INSTRUCTOR_AUTHORED_ASSESSMENT_V2"; pins: { selected_history_sha256?: never; selected_history_integrity_reference: SelectedHistoryIntegrityReference } }
);
export type AssessmentRecord = {
  id: string;
  engagement_id: string;
  version: number;
  sha256: string;
  predecessor: AssessmentDraft["predecessor"];
  saved_engagement_revision: number;
  current_engagement_revision: number;
  learner_revision: number;
  context_status:
    "CURRENT" | "CONTEXT_CHANGED" | "KEY_CHANGED" | "KEY_UNAVAILABLE";
  personal_content_visible: boolean;
  correction_allowed: boolean;
  title?: string;
  document?: AssessmentDocument;
};
export type PinnedAssessmentOptions = AssessmentOptions & {
  selected_state_sha256: string;
  selected_history_tip_sha256: string;
  audited_actor_id: string;
  bound_revision: number;
} & (
  | { history_integrity_format?: never; selected_history_sha256: string; selected_history_integrity_reference?: never }
  | { history_integrity_format: "SELECTED_HISTORY_INTEGRITY_REFERENCE_V2"; selected_history_sha256?: never; selected_history_integrity_reference: SelectedHistoryIntegrityReference }
);
const assessmentRelations: Record<string, readonly string[]> = {
  artifact: ["EXACT_RETAINED_METADATA_LINK_NOT_BYTE_REREAD"],
  request: ["CONTROL_ASSOCIATION_ONLY"],
  task: ["CONTROL_ASSOCIATION_ONLY"],
  population: ["EXPLICIT_SOURCE_LINK"],
  selection: ["RECORDED_POPULATION_LINK"],
  workpaper: [
    "EXACT_RECORDED_WORKPAPER_VERSION",
    "EXACT_AUTHORED_TASK_WORKPAPER_VERSION",
  ],
  review: ["RECORDED_WORKPAPER_REVIEW_LINK"],
  sample_execution: ["EXACT_RECORDED_ITEM_OR_AUTHORED_TASK_LINK"],
  finding: ["DIRECT_RECORDED_FINDING_EVIDENCE_ID"],
  remediation: ["DIRECT_RECORDED_REMEDIATION_EVIDENCE_ID"],
};
export function validAssessmentReference(r: AssessmentReference): boolean {
  return (
    !!r &&
    typeof r.id === "string" &&
    !!r.id &&
    typeof r.record_id === "string" &&
    !!r.record_id &&
    Object.hasOwn(assessmentRelations, r.kind) &&
    assessmentRelations[r.kind].includes(r.relation) &&
    (r.version === null ||
      (Number.isSafeInteger(r.version) && r.version >= 0)) &&
    debriefPin(r.inventory_sha256) &&
    (r.content_sha256 === null || debriefPin(r.content_sha256)) &&
    (![
      "artifact",
      "workpaper",
      "sample_execution",
      "finding",
      "remediation",
    ].includes(r.kind) ||
      debriefPin(r.content_sha256)) &&
    Array.isArray(r.expectation_ids) &&
    r.expectation_ids.length > 0 &&
    r.expectation_ids.every((id) => typeof id === "string" && !!id) &&
    new Set(r.expectation_ids).size === r.expectation_ids.length
  );
}
function validCatalogue(c: AssessmentReferenceCatalogue) {
  return (
    !!c &&
    c.schema === "ASSESSMENT_REFERENCE_CATALOGUE_V1" &&
    Number.isSafeInteger(c.count) &&
    c.count >= 0 &&
    debriefPin(c.sha256) &&
    debriefPin(c.context_sha256)
  );
}
export function assessmentReferencePageQuery(
  o: PinnedAssessmentOptions,
  offset: number,
  selector: AssessmentReferenceSelector,
) {
  if (!o.reference_catalogue)
    throw Error("No paginated reference catalogue selected.");
  return new URLSearchParams({
    revision: String(o.learner_revision),
    offset: String(offset),
    context_sha256: o.reference_catalogue.context_sha256,
    catalogue_sha256: o.reference_catalogue.sha256,
    query: selector.query,
    expectation_ids: JSON.stringify(selector.expectation_ids),
    reference_ids: JSON.stringify(selector.reference_ids),
  }).toString();
}
export function assertAssessmentReferencePage(
  page: AssessmentReferencePage,
  o: PinnedAssessmentOptions,
  offset: number,
  selector: AssessmentReferenceSelector,
) {
  const end =
    offset + (Array.isArray(page.references) ? page.references.length : 0);
  if (
    !o.reference_catalogue ||
    !validCatalogue(page.reference_catalogue) ||
    !sameDebriefValue(page.reference_catalogue, o.reference_catalogue) ||
    !sameDebriefValue(page.selector, selector) ||
    page.offset !== offset ||
    !Number.isSafeInteger(offset) ||
    offset < 0 ||
    !Number.isSafeInteger(page.total) ||
    (selector.reference_ids.length > 0 &&
      page.total > selector.reference_ids.length) ||
    page.total < end ||
    page.total > o.reference_catalogue.count ||
    page.next_offset !== (end < page.total ? end : null) ||
    !Array.isArray(page.references) ||
    page.references.length > 40 ||
    (end < page.total && !page.references.length) ||
    new Set(page.references.map((r) => r.id)).size !== page.references.length ||
    page.references.some(
      (r) =>
        !validAssessmentReference(r) ||
        r.expectation_ids.some(
          (id) => !o.expectations.some((e) => e.id === id),
        ) ||
        (selector.reference_ids.length > 0 &&
          !selector.reference_ids.includes(r.id)) ||
        (selector.expectation_ids.length > 0 &&
          !r.expectation_ids.some((id) =>
            selector.expectation_ids.includes(id),
          )),
    )
  )
    throw Error(
      "Reference page no longer matches the exact assessment catalogue.",
    );
  return page;
}
export function mergeAssessmentReferences(
  o: PinnedAssessmentOptions,
  rows: AssessmentReference[],
  keep: string[],
) {
  const references = o.references.filter((r) => keep.includes(r.id));
  for (const row of rows) {
    const prior = o.references.find((r) => r.id === row.id);
    if (prior && !sameDebriefValue(prior, row))
      throw Error("Historical reference changed between catalogue pages.");
    if (!references.some((r) => r.id === row.id)) references.push(row);
  }
  return { ...o, references };
}
export async function loadSelectedAssessmentReferences(
  o: PinnedAssessmentOptions,
  keep: string[],
  fetchPage: (
    offset: number,
    selector: AssessmentReferenceSelector,
  ) => Promise<AssessmentReferencePage>,
) {
  if (!o.reference_catalogue || !keep.length) return o;
  if (keep.length > 32 || new Set(keep).size !== keep.length)
    throw Error("Select no more than 32 distinct historical work references.");
  const selector = { query: "", expectation_ids: [], reference_ids: keep };
  let offset: number | null = 0;
  const rows: AssessmentReference[] = [];
  while (offset !== null) {
    const page = assertAssessmentReferencePage(
      await fetchPage(offset, selector),
      o,
      offset,
      selector,
    );
    rows.push(...page.references);
    offset = page.next_offset;
  }
  if (
    rows.length !== keep.length ||
    keep.some((id) => rows.filter((r) => r.id === id).length !== 1)
  )
    throw Error("Recorded references are unavailable in the selected history.");
  return mergeAssessmentReferences(o, rows, keep);
}
export function assertAssessmentOptions(
  o: PinnedAssessmentOptions,
  e: Engagement,
  key: string,
  actor: string,
  boundRevision: number,
  h: AssessmentHistoryPin,
) {
  if (
    o.engagement_id !== e.id ||
    o.current_engagement_revision !== e.revision ||
    o.learner_revision !== h.revision ||
    o.key_pin !== key ||
    o.audited_actor_id !== actor ||
    o.bound_revision !== boundRevision ||
    o.selected_state_sha256 !== h.state_sha256 ||
    !assessmentOptionsHistoryMatches(o, h) ||
    o.selected_history_tip_sha256 !== h.event_sha256 ||
    ![o.key_pin, o.rubric_sha256, o.inventory_sha256].every(debriefPin) ||
    (o.reference_catalogue !== undefined &&
      (!validCatalogue(o.reference_catalogue) ||
        !Array.isArray(o.references) ||
        o.references.length > o.reference_catalogue.count)) ||
    !Array.isArray(o.references) ||
    !Array.isArray(o.issues) ||
    !Array.isArray(o.expectations) ||
    new Set(o.references.map((r) => r.id)).size !== o.references.length ||
    o.references.some(
      (r) =>
        !validAssessmentReference(r) ||
        r.expectation_ids.some(
          (id) => !o.expectations.some((e) => e.id === id),
        ),
    )
  )
    throw Error(
      "Assessment choices no longer match the exact protected history and rubric.",
    );
  return o;
}
export function assertAssessmentRecord(
  r: AssessmentRecord,
  e: Engagement,
  key: string,
) {
  if (
    !r ||
    r.engagement_id !== e.id ||
    r.current_engagement_revision !== e.revision ||
    typeof r.id !== "string" ||
    !debriefPin(r.sha256) ||
    !Number.isSafeInteger(r.version) ||
    r.version < 1 ||
    !["CURRENT", "CONTEXT_CHANGED", "KEY_CHANGED", "KEY_UNAVAILABLE"].includes(
      r.context_status,
    ) ||
    typeof r.personal_content_visible !== "boolean" ||
    typeof r.correction_allowed !== "boolean"
  )
    throw Error("Assessment response belongs to a changed context.");
  if (!r.personal_content_visible) {
    if (
      r.title !== undefined ||
      r.document !== undefined ||
      r.correction_allowed
    )
      throw Error("Unavailable assessment contains protected judgment.");
    return r;
  }
  if (r.context_status !== "CURRENT" || typeof r.title !== "string")
    throw Error("Assessment visibility differs from current authority.");
  if (r.document) {
    const d = r.document;
    if (
      !Array.isArray(d.references) ||
      d.references.some((r) => !validAssessmentReference(r)) ||
      !["INSTRUCTOR_AUTHORED_ASSESSMENT_V1", "INSTRUCTOR_AUTHORED_ASSESSMENT_V2"].includes(d.schema) ||
      d.id !== r.id ||
      d.version !== r.version ||
      d.engagement_id !== e.id ||
      d.pins.key_pin !== key ||
      d.pins.learner_revision !== r.learner_revision ||
      d.authored.title !== r.title ||
      !sameDebriefValue(d.predecessor, r.predecessor) ||
      ![
        d.pins.rubric_sha256,
        d.pins.inventory_sha256,
        d.pins.selected_state_sha256,
        d.pins.selected_history_tip_sha256,
      ].every(debriefPin) ||
      !assessmentDocumentHistoryMatches(d, responseHistoryPin(d.pins,
        d.schema === "INSTRUCTOR_AUTHORED_ASSESSMENT_V2" ? "2.0" : "1.0",
        d.engagement_id, d.pins.learner_revision), e.id)
    )
      throw Error("Assessment document pins differ from the protected record.");
  }
  return r;
}
export function assessmentSavePayload(
  d: AssessmentDraft,
  o: PinnedAssessmentOptions,
  commandId: string,
) {
  return {
    ...validateAssessmentDraft(d, o),
    expected_engagement_revision: o.current_engagement_revision,
    learner_revision: o.learner_revision,
    key_pin: o.key_pin,
    rubric_sha256: o.rubric_sha256,
    inventory_sha256: o.inventory_sha256,
    command_id: commandId,
  };
}
