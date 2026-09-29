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
};
export type AssessmentHistoryPin = {
  revision: number;
  state_sha256: string;
  history_sha256: string;
  event_sha256: string;
};
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
  schema: "INSTRUCTOR_AUTHORED_ASSESSMENT_V1";
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
    selected_history_sha256: string;
    selected_history_tip_sha256: string;
    bound_revision: number;
  };
  authored: Omit<AssessmentDraft, "predecessor">;
  selected_issues: AssessmentOptions["issues"];
  selected_expectations: AssessmentOptions["expectations"];
  references: AssessmentReference[];
  qualification: string;
};
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
  selected_history_sha256: string;
  selected_history_tip_sha256: string;
  audited_actor_id: string;
  bound_revision: number;
};
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
    o.selected_history_sha256 !== h.history_sha256 ||
    o.selected_history_tip_sha256 !== h.event_sha256 ||
    ![o.key_pin, o.rubric_sha256, o.inventory_sha256].every(debriefPin) ||
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
      d.schema !== "INSTRUCTOR_AUTHORED_ASSESSMENT_V1" ||
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
        d.pins.selected_history_sha256,
        d.pins.selected_history_tip_sha256,
      ].every(debriefPin)
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
