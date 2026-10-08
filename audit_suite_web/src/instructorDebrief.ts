import {
  assertSelectedHistoryIntegrityReference,
  type SelectedHistoryIntegrityReference,
} from "./instructorAssessments";
/** Compare JSON structure without recomputing server-owned canonical digests. */
export function sameDebriefValue(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (Array.isArray(a) || Array.isArray(b))
    return (
      Array.isArray(a) &&
      Array.isArray(b) &&
      a.length === b.length &&
      a.every((value, index) => sameDebriefValue(value, b[index]))
    );
  if (!a || !b || typeof a !== "object" || typeof b !== "object") return false;
  const left = a as Record<string, unknown>,
    right = b as Record<string, unknown>;
  const keys = Object.keys(left);
  return (
    keys.length === Object.keys(right).length &&
    keys.every(
      (key) =>
        Object.prototype.hasOwnProperty.call(right, key) &&
        sameDebriefValue(left[key], right[key]),
    )
  );
}
export function debriefPin(value: unknown): value is string {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}
/** Export names must be literal safe leaf names, never service-provided paths. */
export function safeDebriefFilename(value: unknown): value is string {
  return (
    typeof value === "string" &&
    value.length <= 160 &&
    /^[A-Za-z0-9][A-Za-z0-9_.-]*$/.test(value) &&
    value !== "." &&
    value !== ".."
  );
}

export type DebriefAnnotation = {
  artifact_id: string;
  sha256: string;
  note: string;
  locator: null | {
    kind: "PAGE" | "LINE" | "CELL" | "TIME" | "OTHER";
    value: string;
  };
  attach: boolean;
};
export type DebriefSection = {
  issue_ids: string[];
  expectation_ids: string[];
  explanation: string;
  limitations: string;
  prompts: string[];
  annotations: DebriefAnnotation[];
};
export type DebriefDraft = {
  recipient_id: string;
  expected_revision: number;
  learner_revision: number;
  title: string;
  sections: DebriefSection[];
  predecessor_release_id: string | null;
};
export type DebriefOptions = {
  engagement_id: string;
  revision: number;
  key_manifest_sha256: string;
  recipients: { id: string; name: string }[];
  issues: { id: string; title: string }[];
  expectations: { id: string; title: string; issue_ids: string[] }[];
  artifacts: { id: string; title: string; sha256: string; bytes: number }[];
};
export function emptyDebriefSection(): DebriefSection {
  return {
    issue_ids: [],
    expectation_ids: [],
    explanation: "",
    limitations: "",
    prompts: [""],
    annotations: [],
  };
}
export function validateDebriefDraft(
  d: DebriefDraft,
  o: DebriefOptions,
): DebriefDraft {
  const bounded = (v: string, n: number) =>
    typeof v === "string" && v.trim().length > 0 && Array.from(v).length <= n;
  const unique = (v: string[]) => new Set(v).size === v.length;
  if (
    d.expected_revision !== o.revision ||
    !Number.isSafeInteger(d.learner_revision) ||
    d.learner_revision < 0 ||
    d.learner_revision > o.revision ||
    o.recipients.filter((r) => r.id === d.recipient_id).length !== 1 ||
    !bounded(d.title, 200) ||
    (d.predecessor_release_id !== null &&
      !bounded(d.predecessor_release_id, 128)) ||
    d.sections.length < 1 ||
    d.sections.length > 10
  )
    throw Error(
      "Choose a current learner, exact historical revision and one to ten titled sections.",
    );
  const originals = new Set<string>();
  for (const s of d.sections) {
    if (
      !s.issue_ids.length ||
      s.issue_ids.length > 10 ||
      s.expectation_ids.length > 10 ||
      s.annotations.length > 8 ||
      !unique(s.issue_ids) ||
      !unique(s.expectation_ids) ||
      s.issue_ids.some(
        (id) => o.issues.filter((i) => i.id === id).length !== 1,
      ) ||
      s.expectation_ids.some((id) => {
        const matches = o.expectations.filter((x) => x.id === id);
        return (
          matches.length !== 1 ||
          matches[0].issue_ids.some((i) => !s.issue_ids.includes(i))
        );
      }) ||
      !bounded(s.explanation, 4000) ||
      !bounded(s.limitations, 4000) ||
      s.prompts.length < 1 ||
      s.prompts.length > 8 ||
      s.prompts.some((p) => !bounded(p, 1000))
    )
      throw Error(
        "Each section needs explicit current issues, related expectations, explanation and limitations, with bounded prompts.",
      );
    const local = new Set<string>();
    for (const a of s.annotations) {
      if (
        local.has(a.artifact_id) ||
        !debriefPin(a.sha256) ||
        o.artifacts.filter(
          (r) => r.id === a.artifact_id && r.sha256 === a.sha256,
        ).length !== 1 ||
        !bounded(a.note, 1000) ||
        typeof a.attach !== "boolean" ||
        (a.locator &&
          (!["PAGE", "LINE", "CELL", "TIME", "OTHER"].includes(
            a.locator.kind,
          ) ||
            !bounded(a.locator.value, 200)))
      )
        throw Error(
          "Annotations require distinct exact originals and explicit notes/locators.",
        );
      local.add(a.artifact_id);
      originals.add(a.artifact_id);
    }
  }
  if (originals.size > 8)
    throw Error("Select no more than eight distinct originals.");
  return structuredClone(d);
}

export type DebriefSourceReference = {
  artifact_id: string;
  artifact_sha256: string;
  status: "RECORDED_EXACT_NATIVE_IDENTITY" | "UNRECORDED";
  native: null | {
    company: string;
    branch: string;
    system: string;
    record: string;
    version: number;
    sha256: string;
    source_store_id?: string;
    source_system_alias?: string;
    registry_sha256?: string;
    portfolio_qualification?: string;
  };
};
export type SelectedDebrief = {
  source_references: DebriefSourceReference[];
  title: string;
  version: number;
  predecessor: null | { release_id: string; release_sha256: string };
  key_manifest_sha256: string;
  learner: {
    actor_id: string;
    revision: number;
    state_sha256: string;
    event_sha256: string;
    qualification: string;
    simulated_at?: string | null;
  };
  sections: {
    issues: {
      id: string;
      control_ids: string[];
      claim: string;
      uncertainty?: string;
    }[];
    expectations: {
      id: string;
      issue_ids: string[];
      procedure: string;
      acceptable_alternatives: string[];
    }[];
    explanation: string;
    limitations: string;
    prompts: string[];
    annotations: DebriefAnnotation[];
  }[];
  qualification: string;
} & (
  | { schema: "SELECTED_INSTRUCTOR_DEBRIEF_V1"; learner: { history_sha256: string; history_integrity_reference?: never } }
  | { schema: "SELECTED_INSTRUCTOR_DEBRIEF_V2"; learner: { history_sha256?: never; history_integrity_reference: SelectedHistoryIntegrityReference } }
);
export function validSelectedDebriefHistory(doc: SelectedDebrief, engagementId: string): boolean {
  const learner = doc?.learner;
  if (!learner || typeof engagementId !== "string" || !engagementId ||
      !Number.isSafeInteger(learner.revision) || learner.revision < 0 ||
      ![learner.state_sha256, learner.event_sha256].every(debriefPin)) return false;
  if (doc.schema === "SELECTED_INSTRUCTOR_DEBRIEF_V1")
    return debriefPin(learner.history_sha256) &&
      !Object.prototype.hasOwnProperty.call(learner, "history_integrity_reference");
  if (doc.schema !== "SELECTED_INSTRUCTOR_DEBRIEF_V2" ||
      Object.prototype.hasOwnProperty.call(learner, "history_sha256")) return false;
  try {
    assertSelectedHistoryIntegrityReference(learner.history_integrity_reference,
      engagementId, learner.revision, learner.state_sha256, learner.event_sha256);
    return true;
  } catch { return false; }
}
export type DebriefPreview = {
  preview: {
    id: string;
    engagement_id: string;
    instructor_id: string;
    recipient_id: string;
    revision: number;
    key_manifest_sha256: string;
    expires_at: string;
    content: {
      stage: "EXPLANATION";
      text: string;
      pointers: [];
      document: SelectedDebrief;
    };
  };
  preview_sha256: string;
  delivered: false;
};
export function debriefPreviewMatches(
  p: DebriefPreview,
  d: DebriefDraft,
  o: DebriefOptions,
  eid: string,
  actor: string,
) {
  const v = p?.preview,
    doc = v?.content?.document;
  return (
    !!doc &&
    p.delivered === false &&
    debriefPin(p.preview_sha256) &&
    v.engagement_id === eid &&
    v.instructor_id === actor &&
    v.recipient_id === d.recipient_id &&
    v.revision === d.expected_revision &&
    v.key_manifest_sha256 === o.key_manifest_sha256 &&
    v.content.stage === "EXPLANATION" &&
    v.content.text === d.title &&
    v.content.pointers.length === 0 &&
    Date.parse(v.expires_at) > Date.now() &&
    validSelectedDebriefHistory(doc, eid) &&
    doc.title === d.title &&
    doc.key_manifest_sha256 === o.key_manifest_sha256 &&
    doc.learner.actor_id === d.recipient_id &&
    doc.learner.revision === d.learner_revision &&
    (doc.predecessor?.release_id ?? null) === d.predecessor_release_id &&
    validDebriefSourceReferences(doc) &&
    doc.sections.length === d.sections.length &&
    doc.sections.every((s, i) =>
      sameDebriefValue(
        {
          issue_ids: s.issues.map((x) => x.id),
          expectation_ids: s.expectations.map((x) => x.id),
          explanation: s.explanation,
          limitations: s.limitations,
          prompts: s.prompts,
          annotations: s.annotations,
        },
        d.sections[i],
      ),
    )
  );
}
export type DebriefExportPreview = {
  preview: {
    id: string;
    actor_id: string;
    engagement_id: string;
    release_id: string;
    release_sha256: string;
    filename: string;
    sha256: string;
    bytes: number;
    members: { name: string; bytes: number; sha256: string }[];
    expires_at: string;
  };
  preview_sha256: string;
  exported: false;
};
export function exportPreviewMatches(
  v: DebriefExportPreview,
  eid: string,
  actor: string,
  rid: string,
  sha: string,
) {
  const p = v?.preview;
  return (
    !!p &&
    v.exported === false &&
    debriefPin(v.preview_sha256) &&
    p.actor_id === actor &&
    p.engagement_id === eid &&
    p.release_id === rid &&
    p.release_sha256 === sha &&
    safeDebriefFilename(p.filename) &&
    debriefPin(p.sha256) &&
    Number.isSafeInteger(p.bytes) &&
    p.bytes > 0 &&
    p.bytes <= 20 * 1024 * 1024 &&
    Date.parse(p.expires_at) > Date.now() &&
    Array.isArray(p.members) &&
    p.members.length <= 12 &&
    p.members.length > 0 &&
    new Set(p.members.map((m) => m.name)).size === p.members.length &&
    p.members.every(
      (m) =>
        typeof m.name === "string" &&
        !m.name.startsWith("/") &&
        !m.name.includes("\\") &&
        !m.name.split("/").some((x) => x === ".." || x === "" || x === ".") &&
        debriefPin(m.sha256) &&
        Number.isSafeInteger(m.bytes) &&
        m.bytes >= 0 &&
        m.bytes <= 20 * 1024 * 1024,
    )
  );
}

export function validDebriefSourceReferences(doc: SelectedDebrief) {
  const pins = new Map(
    doc.sections.flatMap((s) =>
      s.annotations.map((a) => [a.artifact_id, a.sha256] as const),
    ),
  );
  return (
    Array.isArray(doc.source_references) &&
    doc.source_references.length === pins.size &&
    new Set(doc.source_references.map((r) => r.artifact_id)).size ===
      pins.size &&
    doc.source_references.every(
      (r) =>
        pins.get(r.artifact_id) === r.artifact_sha256 &&
        (r.status === "UNRECORDED"
          ? r.native === null
          : r.status === "RECORDED_EXACT_NATIVE_IDENTITY" &&
            !!r.native &&
            r.native.sha256 === r.artifact_sha256),
    )
  );
}
