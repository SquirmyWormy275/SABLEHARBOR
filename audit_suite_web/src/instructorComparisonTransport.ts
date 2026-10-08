import { request, type Row } from "./api";
import { sameComparisonHistory } from "./instructorAssessments";

export type DeferredComparison = {
  family: string;
  count: number;
  sha256: string;
  expectation_id?: string;
  source_id?: string;
  record_id?: string;
  item_id?: string;
};
export type ComparisonHeader = Record<string, unknown> & {
  comparison_transport?: {
    schema: "SH_INSTRUCTOR_COMPARISON_TRANSPORT_V1";
    inventory_sha256: string;
    complete_inventory_changed: false;
    response_max_bytes: number;
    view: "SUMMARY" | "DETAIL";
  };
};
const hash = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const relationNames = [
  "task_linked_workpaper_versions", "source_linked_workpaper_versions",
  "workpaper_version_reviews", "source_linked_populations", "population_linked_selections",
  "recorded_sample_executions", "recorded_findings", "recorded_remediations",
  "control_associated_records_only.requests", "control_associated_records_only.tasks",
];
function selectorKeys(family: string): string[] | null {
  if (["sources", "inspection.records", "audited_actor_activity"].includes(family)) return [];
  if (["sources.exact_retained_artifacts", "sources.different_version_or_digest_artifact_ids"].includes(family)) return ["source_id"];
  if (family === "expectation" || relationNames.some((name) => family === "expectation." + name)) return ["expectation_id"];
  if (family === "expectation.recorded_sample_executions.matched_items") return ["expectation_id", "record_id"];
  if (family === "expectation.recorded_sample_executions.matched_items.evidence") return ["expectation_id", "record_id", "item_id"];
  return null;
}
export function comparisonDescriptor(value: unknown): DeferredComparison {
  const v = value as DeferredComparison;
  const selectors = v && typeof v.family === "string" ? selectorKeys(v.family) : null;
  if (!selectors || !Number.isSafeInteger(v.count) || v.count < 0 || !hash(v.sha256) ||
      Object.keys(v).sort().join("|") !== ["family", "count", "sha256", ...selectors].sort().join("|") ||
      selectors.some((key) => typeof (v as unknown as Row)[key] !== "string" ||
        !String((v as unknown as Row)[key]).length || String((v as unknown as Row)[key]).length > 256))
    throw Error("Exact deferred comparison relationship required.");
  return v;
}
export function comparisonSummary(header: ComparisonHeader, expectedIds: string[]): void {
  const t = header.comparison_transport;
  if (!t) return; // Older complete views keep their original validation path.
  if (t.schema !== "SH_INSTRUCTOR_COMPARISON_TRANSPORT_V1" || t.view !== "SUMMARY" ||
      t.complete_inventory_changed !== false || !hash(t.inventory_sha256) || t.response_max_bytes !== 4 * 1024 * 1024)
    throw Error("Comparison transport context unavailable.");
  const rows = header.expectations as Row[];
  if (!Array.isArray(rows)) throw Error("Complete comparison expectation index required.");
  if (header.status === "CONTEXT_MISMATCH") {
    if (rows.length || Object.keys(header.deferred as object).length) throw Error("Mismatched context must withhold relationships.");
    return;
  }
  if (rows.length !== expectedIds.length || new Set(rows.map((r) => r.expectation_id)).size !== rows.length ||
      rows.some((r) => !expectedIds.includes(String(r.expectation_id)) ||
        !["EXPLICIT_SOURCE_LINK_PRESENT", "NO_EXPLICIT_WORKPAPER_SOURCE_LINK_RECORDED"].includes(String(r.status))))
    throw Error("Comparison must retain every authored expectation.");
  for (const row of rows) {
    const d = comparisonDescriptor(row.detail);
    if (d.family !== "expectation" || d.expectation_id !== row.expectation_id || d.count !== 1)
      throw Error("Comparison expectation selector differs.");
  }
  const deferred = header.deferred as Record<string, unknown>;
  if (!deferred || Object.keys(deferred).sort().join("|") !== ["sources", "inspection.records", "audited_actor_activity"].sort().join("|"))
    throw Error("Complete comparison families required.");
  for (const [family, value] of Object.entries(deferred)) {
    if (comparisonDescriptor(value).family !== family) throw Error("Comparison family differs.");
  }
  const inspection = header.inspection as Row;
  if (!inspection || inspection.status !== "SELF_REPORTED_INSPECTION" ||
      inspection.qualification !== "AUTHOR_ASSERTION_NOT_VERIFIED_READING_UNDERSTANDING_TESTING_OR_GRADE" ||
      inspection.absence !== "NO_RECORDED_ASSERTION_DOES_NOT_ESTABLISH_NO_INSPECTION" ||
      [inspection.audited_actor_count, inspection.other_actor_count, inspection.unresolved_record_count].some(
        (v) => !Number.isSafeInteger(v) || Number(v) < 0) ||
      Number(inspection.audited_actor_count) + Number(inspection.other_actor_count) !== comparisonDescriptor(deferred["inspection.records"]).count ||
      comparisonDescriptor(deferred["inspection.records"]).count > 10000 ||
      header.audited_actor_activity_count !== comparisonDescriptor(deferred.audited_actor_activity).count)
    throw Error("Complete inspection counts differ from the selected comparison.");
}
export function comparisonPage(value: ComparisonHeader, header: ComparisonHeader, descriptor: DeferredComparison, offset: number) {
  const d = comparisonDescriptor(descriptor), t = value.comparison_transport, expected = header.comparison_transport;
  const page = value.page as {family: string; target_sha256: string; total: number; offset: number; next_offset: number | null; rows: Array<Row | string>};
  const fields = ["status", "engagement_id", "audited_actor_id", "binding_manifest_sha256", "bound_revision",
    "selected_history_revision", "selected_state_sha256", "selected_history_tip_sha256",
    "current_revision", "grading", "professional_validation"];
  if (!expected || !t || t.schema !== expected.schema || t.view !== "DETAIL" ||
      t.inventory_sha256 !== expected.inventory_sha256 || t.complete_inventory_changed !== false ||
      t.response_max_bytes !== expected.response_max_bytes || fields.some((k) => value[k] !== header[k]) ||
      !sameComparisonHistory(value, header) ||
      !page || page.family !== d.family || page.target_sha256 !== d.sha256 || page.total !== d.count ||
      page.offset !== offset || !Array.isArray(page.rows) || page.rows.length > 20 ||
      offset + page.rows.length > d.count || (offset < d.count && !page.rows.length) ||
      page.next_offset !== (offset + page.rows.length < d.count ? offset + page.rows.length : null))
    throw Error("Comparison page changed; select the history again.");
  return page;
}
/** Validate each bounded inspection page as a page, never as the full inventory. */
export function comparisonInspectionPage(rows: Row[], header: ComparisonHeader): void {
  const ids = new Set<string>();
  for (const row of rows) {
    if (!row || typeof row.id !== "string" || !row.id || ids.has(row.id) ||
        row.classification !== "SELF_REPORTED_INSPECTION" || typeof row.artifact_id !== "string" ||
        typeof row.actor !== "string" || !row.actor || typeof row.locator !== "string" ||
        typeof row.observation !== "string" || ![row.sha256, row.history_sha256].every(hash) ||
        !Number.isSafeInteger(row.recorded_revision) || Number(row.recorded_revision) < 0 ||
        Number(row.recorded_revision) > Number(header.selected_history_revision) ||
        (row.version !== null && (!Number.isSafeInteger(row.version) || Number(row.version) < 0)) ||
        row.attribution !== (row.actor === header.audited_actor_id ? "AUDITED_ACTOR" : "OTHER_ACTOR"))
      throw Error("Inspection page does not match the selected history.");
    ids.add(row.id);
  }
}
export function comparisonRowDeferred(row: Row, parent: DeferredComparison): Record<string, DeferredComparison> {
  let names: string[] = [], prefix = "", selectors: Record<string, unknown> = {};
  if (parent.family === "expectation") {
    names = relationNames; prefix = "expectation."; selectors = {expectation_id: parent.expectation_id};
    if (row.expectation_id !== parent.expectation_id) throw Error("Selected expectation differs.");
  } else if (parent.family === "sources") {
    names = ["exact_retained_artifacts", "different_version_or_digest_artifact_ids"];
    prefix = "sources."; selectors = {source_id: row.source_id};
  } else if (parent.family === "expectation.recorded_sample_executions") {
    names = ["matched_items"]; prefix = parent.family + ".";
    selectors = {expectation_id: parent.expectation_id, record_id: row.id};
  } else if (parent.family === "expectation.recorded_sample_executions.matched_items") {
    names = ["evidence"]; prefix = parent.family + ".";
    selectors = {expectation_id: parent.expectation_id, record_id: parent.record_id, item_id: row.item_id};
  }
  const values = row._comparison_deferred as Record<string, unknown> | undefined;
  if (!names.length) {
    if (values) throw Error("Unexpected deferred comparison fields.");
    return {};
  }
  if (!values || Object.keys(values).sort().join("|") !== [...names].sort().join("|"))
    throw Error("Complete deferred relationship selectors required.");
  const checked: Record<string, DeferredComparison> = {};
  for (const name of names) {
    const d = comparisonDescriptor(values[name]);
    if (d.family !== prefix + name || Object.entries(selectors).some(([k, v]) => (d as unknown as Row)[k] !== v))
      throw Error("Deferred relationship identity differs.");
    checked[name] = d;
  }
  return checked;
}
export async function readComparisonPage(header: ComparisonHeader, descriptor: DeferredComparison, offset = 0) {
  const d = comparisonDescriptor(descriptor);
  if (!header.comparison_transport || !Number.isSafeInteger(offset) || offset < 0 || offset > d.count)
    throw Error("Selected comparison context required.");
  const q = new URLSearchParams({revision: String(header.selected_history_revision), view: "detail-v1",
    inventory_sha256: header.comparison_transport.inventory_sha256, target_sha256: d.sha256,
    family: d.family, offset: String(offset), limit: "20"});
  for (const key of selectorKeys(d.family)!) q.set(key, String((d as unknown as Row)[key]));
  const response = await request<ComparisonHeader>(`/api/engagements/${encodeURIComponent(String(header.engagement_id))}/instructor-comparison?${q}`);
  return comparisonPage(response, header, d, offset);
}
