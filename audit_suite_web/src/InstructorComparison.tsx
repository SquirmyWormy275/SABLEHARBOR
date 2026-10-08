import { InstructorAssessments } from "./InstructorAssessments";
import {
  comparisonHistoryPin, validComparisonHistory, historyIntegrityRows,
  type ComparisonHistoryFields, type AssessmentHistoryPin,
} from "./instructorAssessments";
import { Fragment, useEffect, useRef, useState } from "react";
import { request, str, type Engagement, type Row } from "./api";
import type { BoundResponse, BoundExpectation } from "./boundInstructorKey";
import {
  comparisonSummary, comparisonDescriptor, comparisonRowDeferred,
  comparisonInspectionPage, readComparisonPage,
  type ComparisonHeader, type DeferredComparison,
} from "./instructorComparisonTransport";
import { validExpectationTaskLinks } from "./expectationTaskLinks";
import {
  inspectionInventory,
  type InspectionInventory,
} from "./inspectionInventory";

export function SelectedHistoryIntegrityRows({history}: {history: AssessmentHistoryPin}) {
  return <>{historyIntegrityRows(history).map(({label, value}) => (
    <Fragment key={label}><dt>{label}</dt><dd><code>{value}</code></dd></Fragment>
  ))}</>;
}
type Inventory = ComparisonHeader & ComparisonHistoryFields & {
  status: "DETERMINISTIC_LINK_INVENTORY_ONLY" | "CONTEXT_MISMATCH";
  engagement_id: string;
  audited_actor_id: string;
  binding_manifest_sha256: string;
  bound_revision: number;
  selected_history_revision: number;
  current_revision: number;
  selected_state_sha256: string;
  selected_history_tip_sha256: string;
  grading: "NOT_PERFORMED";
  professional_validation: "UNVALIDATED";
  mismatches: string[];
  limits: string[];
  sources?: Row[];
  expectations?: Row[];
  audited_actor_activity?: Row[];
  shared_workspace_activity_count?: number;
  inspection?:
    | InspectionInventory
    | string
    | { status: "UNAVAILABLE_SELECTED_CONTEXT_MISMATCH" };
};
function DeferredRecords({header, descriptor, label, expected, expectationRow}: {
  header: ComparisonHeader; descriptor: DeferredComparison; label: string;
  expected?: BoundExpectation; expectationRow?: Row;
}) {
  const [page, setPage] = useState<Awaited<ReturnType<typeof readComparisonPage>> | null>(null);
  const [previous, setPrevious] = useState<number[]>([]);
  const [busy, setBusy] = useState(false), [error, setError] = useState("");
  const epoch = useRef(0);
  useEffect(() => () => { epoch.current++; }, []);
  async function load(offset: number, history: number[]) {
    const current = ++epoch.current;
    setBusy(true); setError(""); setPage(null);
    try {
      const value = await readComparisonPage(header, descriptor, offset);
      if (descriptor.family === "inspection.records") comparisonInspectionPage(value.rows as Row[], header);
      for (const row of value.rows) if (typeof row === "object") comparisonRowDeferred(row, descriptor);
      if (descriptor.family === "expectation") {
        if (!expected || value.rows.length !== 1 || !validExpectationTaskLinks({
          ...(value.rows[0] as Row), task_linked_workpaper_versions: [],
        }, expected)) throw Error("Authored procedure associations differ.");
      }
      if (descriptor.family === "expectation.task_linked_workpaper_versions" &&
          (!expected || !expectationRow || !validExpectationTaskLinks({
            ...expectationRow, task_linked_workpaper_versions: value.rows,
          }, expected))) throw Error("Recorded procedure associations differ.");
      if (current === epoch.current) { setPage(value); setPrevious(history); }
    } catch (err) { if (current === epoch.current) setError((err as Error).message); }
    finally { if (current === epoch.current) setBusy(false); }
  }
  return <details>
    <summary>{label} · {descriptor.count} recorded · details deferred</summary>
    <p>Ordered relationship SHA256 <code>{descriptor.sha256}</code>. Details are loaded separately from the same selected history.</p>
    {!page && <button type="button" disabled={busy} onClick={() => void load(0, [])}>
      {busy ? "Loading exact links…" : "Load exact links"}
    </button>}
    {busy && <p role="status">Verifying this bounded page…</p>}
    {error && <p role="alert">{error} No links were inferred. Select the history again if it changed.</p>}
    {page && <>
      <p>Records {page.rows.length ? page.offset + 1 : 0}–{page.offset + page.rows.length} of {page.total}. This page is not the complete inventory.</p>
      {!page.total && <p>The verified complete relationship list is empty.</p>}
      <ul>{page.rows.map((row, i) => <li key={page.offset + i}>
        {typeof row === "string" ? <code>{row}</code> : <>
          <dl>{Object.entries(row).filter(([key]) => key !== "_comparison_deferred").map(([key, value]) =>
            <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{typeof value === "object" ? JSON.stringify(value) : str(value)}</dd></div>)}</dl>
          {Object.entries(comparisonRowDeferred(row, descriptor)).map(([name, nested]) =>
            <DeferredRecords key={JSON.stringify(nested)} header={header} descriptor={nested} label={name.replaceAll("_", " ")}
              expected={expected} expectationRow={descriptor.family === "expectation" ? row : expectationRow} />)}
        </>}
      </li>)}</ul>
      <div className="actions">
        <button type="button" disabled={busy || !previous.length} onClick={() => void load(previous[previous.length - 1], previous.slice(0, -1))}>Previous exact links</button>
        <button type="button" disabled={busy || page.next_offset === null} onClick={() => void load(page.next_offset!, [...previous, page.offset])}>Next exact links</button>
      </div>
    </>}
  </details>;
}
function DeferredComparison({result, bound, selected, onSelect}: {
  result: Inventory; bound: BoundResponse; selected: string; onSelect: (id: string) => void;
}) {
  const expectation = result.expectations?.find((row) => row.expectation_id === selected);
  const expected = bound.snapshot.authored.expectations.find((row) => row.id === selected);
  const deferred = result.deferred as Record<string, DeferredComparison>;
  const inspected = result.inspection as unknown as Record<string, unknown>;
  return <>
    <p>{Number(result.audited_actor_activity_count)} recorded commands by the audited actor · {result.shared_workspace_activity_count} by other actors. Shared work is not automatically credited to the audited actor.</p>
    <p>Complete expectation and relationship counts are shown below. Recorded details are deferred, not absent. Testing, understanding and judgment are not assessed.</p>
    <label>Bound expectation<select aria-label="Bound expectation" value={selected} onChange={(event) => onSelect(event.target.value)}>
      <option value="">Choose an expectation</option>
      {result.expectations?.map((row) => <option key={str(row.expectation_id)} value={str(row.expectation_id)}>{str(row.expectation_id)}</option>)}
    </select></label>
    {expectation && expected && <section aria-label="Expectation links"><h3>{selected}</h3><p>{expected.procedure}</p>
      <p>{expectation.status === "EXPLICIT_SOURCE_LINK_PRESENT" ? "An explicit source link is recorded in at least one workpaper version." : "No explicit workpaper source link is recorded. This does not establish a missed issue."}</p>
      <DeferredRecords key={selected} header={result} descriptor={comparisonDescriptor(expectation.detail)} label="Selected expectation links" expected={expected} />
    </section>}
    <section aria-label="Recorded inspection links"><h3>Recorded inspections</h3>
      <p>{Number(inspected.audited_actor_count)} attributed to the audited actor · {Number(inspected.other_actor_count)} by other actors · {Number(inspected.unresolved_record_count)} unresolved links.</p>
      <p>These are authored inspection notes tied to exact originals and command history. They do not prove reading, understanding or adequate testing. Absence of a note does not establish that a file was never inspected.</p>
      <DeferredRecords header={result} descriptor={comparisonDescriptor(deferred["inspection.records"])} label="Exact original inspection records" />
    </section>
    <DeferredRecords header={result} descriptor={comparisonDescriptor(deferred.sources)} label="Exact retained source links" />
    <DeferredRecords header={result} descriptor={comparisonDescriptor(deferred.audited_actor_activity)} label="Audited actor command history" />
  </>;
}
export function InstructorComparison({
  engagement: e,
  bound,
  viewerId = "",
  assessmentsEnabled = false,
}: {
  engagement: Engagement;
  bound: BoundResponse;
  viewerId?: string;
  assessmentsEnabled?: boolean;
}) {
  const [revision, setRevision] = useState(String(e.revision));
  const [inspectionPage, setInspectionPage] = useState(0);
  const [result, setResult] = useState<Inventory | null>(null);
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const epoch = useRef(0);
  const allowed = e.permissions?.includes("instruct");
  useEffect(() => {
    epoch.current++;
    setResult(null);
    setError("");
    setBusy(false);
    return () => {
      epoch.current++;
    };
  }, [e.id, e.revision, allowed, bound.binding.manifest_sha256]);
  if (!allowed) return null;
  async function inspect() {
    const current = ++epoch.current;
    setResult(null);
    setError("");
    setBusy(true);
    try {
      if (
        !/^\d+$/.test(revision) ||
        !Number.isSafeInteger(Number(revision)) ||
        Number(revision) > e.revision
      )
        throw Error("Choose an existing nonnegative history revision.");
      const value = await request<Inventory>(
        `/api/engagements/${encodeURIComponent(e.id)}/instructor-comparison?revision=${revision}&view=summary-v1`,
      );
      if (current !== epoch.current) return;
      if (
        value.engagement_id !== e.id ||
        value.audited_actor_id !== bound.snapshot.audited_actor_id ||
        !validComparisonHistory(value) ||
        (!value.comparison_transport && (value.expectations ?? []).some(
          (item) =>
            !bound.snapshot.authored.expectations.some(
              (expected) =>
                expected.id === item.expectation_id &&
                validExpectationTaskLinks(item, expected),
            ),
        )) ||
        value.current_revision !== e.revision ||
        value.selected_history_revision !== Number(revision) ||
        value.binding_manifest_sha256 !== bound.binding.manifest_sha256 ||
        value.bound_revision !== bound.binding.bound_revision ||
        value.grading !== "NOT_PERFORMED" ||
        value.professional_validation !== "UNVALIDATED" ||
        !["DETERMINISTIC_LINK_INVENTORY_ONLY", "CONTEXT_MISMATCH"].includes(
          value.status,
        )
      )
        throw Error(
          "The protected history or binding changed. Refresh before comparing.",
        );
      comparisonSummary(value, bound.snapshot.authored.expectations.map((row) => row.id));
      if (!value.comparison_transport && value.status === "DETERMINISTIC_LINK_INVENTORY_ONLY")
        inspectionInventory(
          value.inspection,
          value.selected_history_revision,
          value.audited_actor_id,
        );
      setResult(value);
      setInspectionPage(0);
      setSelected("");
    } catch (err) {
      if (current === epoch.current) setError((err as Error).message);
    } finally {
      if (current === epoch.current) setBusy(false);
    }
  }
  const expectation = result?.expectations?.find(
    (x) => x.expectation_id === selected,
  );
  const inspected =
    result?.status === "DETERMINISTIC_LINK_INVENTORY_ONLY" &&
    typeof result.inspection === "object" &&
    result.inspection.status === "SELF_REPORTED_INSPECTION"
      ? result.inspection
      : null;
  function records(label: string, rows: Row[] = []) {
    return (
      <details>
        <summary>
          {label} · {rows.length}
        </summary>
        {rows.length === 0 ? (
          <p>No explicit link recorded.</p>
        ) : (
          <ul>
            {rows.map((row, i) => (
              <li key={i}>
                <code>{str(row.id)}</code>
                {row.version !== undefined && (
                  <> · version {str(row.version)}</>
                )}
                <dl>
                  {Object.entries(row)
                    .filter(([key]) => key !== "id" && key !== "version")
                    .map(([key, value]) => (
                      <div key={key}>
                        <dt>{key.replaceAll("_", " ")}</dt>
                        <dd>
                          {typeof value === "object"
                            ? JSON.stringify(value)
                            : str(value)}
                        </dd>
                      </div>
                    ))}
                </dl>
              </li>
            ))}
          </ul>
        )}
      </details>
    );
  }
  return (
    <details className="panel instructor-comparison">
      <summary>Trace recorded work against bound expectations</summary>
      <p>
        Choose a history revision to inspect exact recorded links. A revision is
        not a submission, and a source link does not prove adequate testing or
        understanding.
      </p>
      <label>
        History revision
        <input
          aria-label="History revision"
          type="number"
          min="0"
          max={e.revision}
          step="1"
          value={revision}
          disabled={busy}
          onChange={(ev) => {
            epoch.current++;
            setRevision(ev.target.value);
            setResult(null);
            setError("");
          }}
        />
      </label>
      <button type="button" disabled={busy} onClick={() => void inspect()}>
        {busy ? "Tracing recorded links…" : "Trace recorded links"}
      </button>
      {busy && (
        <p role="status">
          Reading and verifying the selected history. You can switch panels and
          return while this read continues.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      {result && (
        <>
          <p>
            Bound revision {result.bound_revision} · observed history revision{" "}
            {result.selected_history_revision} · current revision{" "}
            {result.current_revision}. Audited actor: {result.audited_actor_id}.
          </p>
          {result.status === "CONTEXT_MISMATCH" ? (
            <>
              <p>
                Scope or company context differs. Record comparison is withheld;
                the original binding remains unchanged.
              </p>
              <ul>
                {result.mismatches.map((x) => (
                  <li key={x}>{x.replaceAll("_", " ")}</li>
                ))}
              </ul>
            </>
          ) : result.comparison_transport ? (
            <DeferredComparison key={result.comparison_transport.inventory_sha256} result={result} bound={bound} selected={selected} onSelect={setSelected} />
          ) : (
            <>
              <p>
                {result.audited_actor_activity?.length ?? 0} recorded commands
                by the audited actor · {result.shared_workspace_activity_count}{" "}
                by other actors. Shared work is not automatically credited to
                the audited actor.
              </p>
              <label>
                Bound expectation
                <select
                  aria-label="Bound expectation"
                  value={selected}
                  onChange={(ev) => setSelected(ev.target.value)}
                >
                  <option value="">Choose an expectation</option>
                  {result.expectations?.map((x) => (
                    <option
                      key={str(x.expectation_id)}
                      value={str(x.expectation_id)}
                    >
                      {str(x.expectation_id)}
                    </option>
                  ))}
                </select>
              </label>
              {inspected && (
                <section aria-label="Recorded inspection links">
                  <h3>Recorded inspections</h3>
                  <p>
                    {inspected.audited_actor_count} attributed to the audited
                    actor · {inspected.other_actor_count} by other actors ·{" "}
                    {inspected.unresolved_record_count} unresolved links.
                  </p>
                  <p>
                    These are authored inspection notes tied to exact originals
                    and command history. They do not prove reading,
                    understanding or adequate testing. No record does not
                    establish that a file was never inspected.
                  </p>
                  {records(
                    "Exact original inspection records",
                    inspected.records.slice(
                      inspectionPage * 100,
                      (inspectionPage + 1) * 100,
                    ),
                  )}
                  {inspected.records.length > 100 && (
                    <div className="actions">
                      <button
                        type="button"
                        disabled={inspectionPage === 0}
                        onClick={() => setInspectionPage((p) => p - 1)}
                      >
                        Previous inspection links
                      </button>
                      <span>
                        Page {inspectionPage + 1} of{" "}
                        {Math.ceil(inspected.records.length / 100)}
                      </span>
                      <button
                        type="button"
                        disabled={
                          (inspectionPage + 1) * 100 >= inspected.records.length
                        }
                        onClick={() => setInspectionPage((p) => p + 1)}
                      >
                        Next inspection links
                      </button>
                    </div>
                  )}
                </section>
              )}
              {expectation && (
                <section aria-label="Expectation links">
                  <h3>{selected}</h3>
                  <p>
                    {
                      bound.snapshot.authored.expectations.find(
                        (x) => x.id === selected,
                      )?.procedure
                    }
                  </p>
                  <p>
                    {expectation.status === "EXPLICIT_SOURCE_LINK_PRESENT"
                      ? "An explicit source link is recorded in at least one workpaper version."
                      : "No explicit workpaper source link is recorded. This does not establish a missed issue."}
                  </p>
                  <p>Testing, understanding and judgment are not assessed.</p>
                  <p>
                    {expectation.task_mapping_status ===
                    "EXPLICIT_AUTHORED_LINKS"
                      ? "The author explicitly linked this expectation to the listed procedures."
                      : expectation.task_mapping_status ===
                          "UNRESOLVED_IN_SELECTED_SCOPE"
                        ? "The authored procedure IDs do not all resolve in this selected historical scope."
                        : "This expectation has no explicit procedure mapping in this report."}
                    {Array.isArray(expectation.authored_task_ids) &&
                      expectation.authored_task_ids.length > 0 &&
                      ` Procedure IDs: ${expectation.authored_task_ids.join(", ")}.`}
                  </p>
                  {records(
                    "Workpaper versions with explicit procedure links",
                    expectation.task_linked_workpaper_versions as Row[],
                  )}
                  {records(
                    "Source-linked workpaper versions",
                    expectation.source_linked_workpaper_versions as Row[],
                  )}
                  {records(
                    "Reviews of those workpaper versions",
                    expectation.workpaper_version_reviews as Row[],
                  )}
                  {records(
                    "Source-linked populations",
                    expectation.source_linked_populations as Row[],
                  )}
                  {records(
                    "Selections linked to those populations",
                    expectation.population_linked_selections as Row[],
                  )}
                  {records(
                    "Control-associated requests",
                    (
                      expectation.control_associated_records_only as {
                        requests: Row[];
                      }
                    ).requests,
                  )}
                  {records(
                    "Control-associated procedures",
                    (
                      expectation.control_associated_records_only as {
                        tasks: Row[];
                      }
                    ).tasks,
                  )}
                </section>
              )}
              <details>
                <summary>Exact retained source links</summary>
                {result.sources?.map((source) => (
                  <section key={str(source.source_id)}>
                    <h4>{str(source.source_id)}</h4>
                    <p>
                      SHA256 <code>{str(source.source_sha256)}</code>
                    </p>
                    {records(
                      "Retained artifacts",
                      source.exact_retained_artifacts as Row[],
                    )}
                    <p>
                      Other versions or digests:{" "}
                      {(
                        source.different_version_or_digest_artifact_ids as string[]
                      ).join(", ") || "None recorded"}
                      .
                    </p>
                  </section>
                ))}
              </details>
            </>
          )}
          {result.status === "DETERMINISTIC_LINK_INVENTORY_ONLY" && (
            <InstructorAssessments
              engagement={e}
              viewerId={viewerId}
              enabled={assessmentsEnabled}
              bound={bound}
              history={comparisonHistoryPin(result)}
            />
          )}
          <details>
            <summary>Selected history pins and limits</summary>
            <dl>
              <dt>State</dt>
              <dd>
                <code>{result.selected_state_sha256}</code>
              </dd>
              <SelectedHistoryIntegrityRows history={comparisonHistoryPin(result)} />
              <dt>History tip</dt>
              <dd>
                <code>{result.selected_history_tip_sha256}</code>
              </dd>
            </dl>
            <ul>
              {result.limits.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </details>
  );
}
