import { request, type Engagement, type Row } from "./api";

type Pin = {
  schema: string;
  engagement_id: string;
  engagement_revision: number;
  source_epoch_sha256: string;
  collection: string;
  object_id: string;
  object_sha256: string;
};
export const object = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
const hash = (v: unknown): v is string =>
  typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
export function workspaceContext(e: Engagement, viewer = "") {
  return JSON.stringify([
    viewer,
    e.id,
    e.revision,
    e.permissions,
    e.scope,
    e.simulated_at,
    e.company_source_binding,
    e.evidence_acquisition,
    object(e.workspace_transport).source_epoch_sha256,
  ]);
}
export function paperVersion(row: Row, selected?: number): Row | undefined {
  const versions = Array.isArray(row.versions) ? (row.versions as Row[]) : [];
  const number = selected ?? versions.at(-1)?.version;
  const matches = versions.filter((v) => v.version === number);
  return matches.length === 1 ? matches[0] : undefined;
}
export function deferredPaper(row: Row, selected?: number) {
  const version = paperVersion(row, selected);
  return (
    !!version &&
    Object.hasOwn(version, "_workspace_text") &&
    object(version._workspace_text).loaded !== true
  );
}
export function deferredTrace(row: Row) {
  return (
    Object.hasOwn(row, "_workspace_items") &&
    object(row._workspace_items).loaded !== true
  );
}
function pin(e: Engagement, row: Row, collection: string): Pin {
  const p = object(row._workspace_detail),
    transport = object(e.workspace_transport);
  if (
    p.schema !== "SH_WORKSPACE_SUMMARY_V1" ||
    p.engagement_id !== e.id ||
    p.engagement_revision !== e.revision ||
    p.collection !== collection ||
    p.object_id !== row.id ||
    !hash(p.object_sha256) ||
    !hash(p.source_epoch_sha256) ||
    transport.source_epoch_sha256 !== p.source_epoch_sha256
  )
    throw new Error(
      "Retained detail is not pinned to this current workspace. Reload it.",
    );
  return p as unknown as Pin;
}
const samePin = (left: Pin, right: unknown) => {
  const r = object(right);
  return Object.entries(left).every(([k, v]) => r[k] === v);
};
export function mergeWorkspaceRecord(prior: Row, next: Row): Row {
  if (
    prior.id !== next.id ||
    !hash(object(prior._workspace_detail).object_sha256) ||
    !samePin(
      object(prior._workspace_detail) as unknown as Pin,
      next._workspace_detail,
    )
  )
    return next;
  if (!Array.isArray(next.versions) || !Array.isArray(prior.versions))
    return next;
  return {
    ...next,
    versions: (next.versions as Row[]).map((v) => {
      const old = (prior.versions as Row[]).find(
        (p) => p.version === v.version,
      );
      return old &&
        object(old._workspace_text).loaded === true &&
        object(v._workspace_text).loaded === false &&
        old._workspace_version_sha256 === v._workspace_version_sha256
        ? old
        : v;
    }),
  };
}
export async function loadWorkspaceDetail(
  e: Engagement,
  collection: "workpapers" | "sample_executions",
  row: Row,
  version?: number,
): Promise<Row> {
  const p = pin(e, row, collection),
    query = new URLSearchParams({
      observed_revision: String(e.revision),
      source_epoch: p.source_epoch_sha256,
      object_sha256: p.object_sha256,
    });
  if (collection === "workpapers") {
    if (
      !Number.isSafeInteger(version) ||
      Number(version) < 1 ||
      !paperVersion(row, version)
    )
      throw new Error("Choose an exact retained workpaper version.");
    query.set("version", String(version));
  }
  const value = await request<{ context: Pin; row: Row }>(
    `/api/engagements/${encodeURIComponent(e.id)}/workspace/${collection}/${encodeURIComponent(row.id)}?${query}`,
  );
  if (
    !samePin(p, value.context) ||
    value.row?.id !== row.id ||
    !samePin(p, value.row._workspace_detail)
  )
    throw new Error("Retained detail changed its workspace or object pins.");
  if (collection === "workpapers") {
    const before = paperVersion(row, version),
      after = paperVersion(value.row, version);
    const expected = object(before?._workspace_text),
      actual = object(after?._workspace_text);
    if (
      !before ||
      !after ||
      before._workspace_version_sha256 !== after._workspace_version_sha256 ||
      actual.loaded !== true ||
      typeof after.text !== "string" ||
      expected.sha256 !== actual.sha256 ||
      expected.bytes !== actual.bytes ||
      expected.characters !== actual.characters
    )
      throw new Error("Exact retained workpaper text is unavailable.");
    const bytes = new TextEncoder().encode(after.text);
    const calculated = Array.from(
      new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)),
      (x) => x.toString(16).padStart(2, "0"),
    ).join("");
    if (
      calculated !== expected.sha256 ||
      bytes.length !== expected.bytes ||
      Array.from(after.text).length !== expected.characters
    )
      throw new Error("Retained workpaper text failed its exact byte check.");
  } else if (
    !Array.isArray(value.row.items) ||
    object(value.row._workspace_items).loaded !== true ||
    value.row.items.length !== object(row._workspace_items).count
  ) {
    throw new Error("Complete retained sample items are unavailable.");
  }
  return mergeWorkspaceRecord(row, value.row);
}
export async function loadSampleOriginalContext(
  e: Engagement,
  artifactId: string,
): Promise<Row[]> {
  const matches = e.artifacts.filter((a) => a.id === artifactId),
    transport = object(e.workspace_transport);
  if (
    matches.length !== 1 ||
    matches[0].status !== "AVAILABLE" ||
    !hash(matches[0].sha256) ||
    !hash(transport.source_epoch_sha256)
  )
    throw new Error("Exact original context is unavailable.");
  const query = new URLSearchParams({
    observed_revision: String(e.revision),
    source_epoch: transport.source_epoch_sha256,
    artifact_sha256: matches[0].sha256,
  });
  const value = await request<Record<string, unknown>>(
    `/api/engagements/${encodeURIComponent(e.id)}/workspace/sample-original-context/${encodeURIComponent(artifactId)}?${query}`,
  );
  if (
    value.engagement_id !== e.id ||
    value.engagement_revision !== e.revision ||
    value.source_epoch_sha256 !== transport.source_epoch_sha256 ||
    value.artifact_id !== artifactId ||
    value.artifact_sha256 !== matches[0].sha256 ||
    value.complete_exact_original_selection !== true ||
    value.retained_trace_count !==
      (Array.isArray(e.sample_executions) ? e.sample_executions.length : 0) ||
    !Array.isArray(value.traces)
  )
    throw new Error("Original observations changed their workspace pins.");
  const traces = value.traces as Row[],
    index = Array.isArray(e.sample_executions)
      ? (e.sample_executions as Row[])
      : [];
  if (
    new Set(traces.map((t) => t.id)).size !== traces.length ||
    traces.some((t) => {
      const candidates = index.filter((x) => x.id === t.id);
      return (
        candidates.length !== 1 ||
        !Array.isArray(t.items) ||
        candidates[0].revision !== t.revision ||
        candidates[0].workpaper_digest !== t.workpaper_digest
      );
    })
  )
    throw new Error("Exact retained observation membership is unavailable.");
  return traces;
}
