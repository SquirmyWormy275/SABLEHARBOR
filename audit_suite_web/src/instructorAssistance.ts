import type { Engagement } from "./api";
export type Pointer = { kind: "task" | "artifact"; id: string; sha256: string };
export type AssistanceDraft = {
  recipient_id: string;
  expected_revision: number;
  stage: "HINT" | "POINTER";
  text: string;
  pointers: Pointer[];
};
export type ReleasePreview = {
  preview: {
    id: string;
    engagement_id: string;
    instructor_id: string;
    recipient_id: string;
    revision: number;
    expires_at: string;
    content: { stage: string; text: string; pointers: Pointer[] };
  };
  preview_sha256: string;
  delivered: boolean;
};
export type AssistanceOptions = {
  engagement_id: string;
  revision: number;
  recipients: { id: string; name: string }[];
  tasks: { id: string; title: string; sha256: string }[];
  artifacts: { id: string; name: string; sha256: string }[];
};
export function assistanceContext(e: Engagement, actor: string) {
  return JSON.stringify([
    actor,
    e.id,
    e.revision,
    e.permissions,
    e.scope,
    e.company_source_binding,
    e.evidence_acquisition,
  ]);
}
export function previewMatches(
  result: ReleasePreview,
  draft: AssistanceDraft,
  e: Engagement,
  actor: string,
) {
  const p = result?.preview;
  return (
    !!p &&
    result.delivered === false &&
    /^[a-f0-9]{64}$/.test(result.preview_sha256) &&
    p.engagement_id === e.id &&
    p.instructor_id === actor &&
    p.revision === e.revision &&
    p.revision === draft.expected_revision &&
    p.recipient_id === draft.recipient_id &&
    p.content?.stage === draft.stage &&
    p.content.text === draft.text &&
    Array.isArray(p.content.pointers) &&
    p.content.pointers.length === draft.pointers.length &&
    p.content.pointers.every(
      (v, i) =>
        v.kind === draft.pointers[i].kind &&
        v.id === draft.pointers[i].id &&
        v.sha256 === draft.pointers[i].sha256,
    ) &&
    Number.isFinite(Date.parse(p.expires_at)) &&
    Date.parse(p.expires_at) > Date.now()
  );
}
export function validateAssistanceDraft(
  d: AssistanceDraft,
  o: AssistanceOptions,
) {
  if (
    d.expected_revision !== o.revision ||
    !o.recipients.some((r) => r.id === d.recipient_id) ||
    !d.text.trim() ||
    Array.from(d.text).length > 4000 ||
    !["HINT", "POINTER"].includes(d.stage) ||
    d.pointers.length > 4 ||
    (d.stage === "HINT" && d.pointers.length) ||
    (d.stage === "POINTER" && !d.pointers.length)
  )
    throw Error(
      "Choose a current recipient, explicit stage and bounded message with the appropriate pointers.",
    );
  const seen = new Set<string>();
  for (const p of d.pointers) {
    const rows =
      p.kind === "task" ? o.tasks : p.kind === "artifact" ? o.artifacts : [];
    const key = p.kind + ":" + p.id;
    if (
      seen.has(key) ||
      !rows.some((r) => r.id === p.id && r.sha256 === p.sha256)
    )
      throw Error("Choose distinct current pinned pointers.");
    seen.add(key);
  }
  return d;
}

/** Resolve an explicit released pointer against this authorized snapshot only. */
export function assistancePointer(e: Engagement, p: Pointer) {
  if (p.kind === "artifact") {
    const rows = e.artifacts.filter(
      (a) => a.id === p.id && a.status === "AVAILABLE" && a.sha256 === p.sha256,
    );
    return rows.length === 1
      ? { id: p.id, collection: "artifacts", sha256: p.sha256 }
      : null;
  }
  if (p.kind === "task") {
    const pins = e.sample_execution_inputs as
      | {
          engagement_id?: string;
          engagement_revision?: number;
          tasks?: { task_id: string; task_digest: string }[];
        }
      | undefined;
    const rows = e.tasks.filter((t) => t.id === p.id);
    if (
      rows.length === 1 &&
      pins?.engagement_id === e.id &&
      pins.engagement_revision === e.revision &&
      pins.tasks?.filter(
        (t) => t.task_id === p.id && t.task_digest === p.sha256,
      ).length === 1
    )
      return { id: p.id, collection: "tasks" };
  }
  return null;
}
