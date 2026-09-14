import { useEffect, useRef, useState } from "react";
import { request, str, type Engagement, type Row } from "./api";
import type { BoundResponse } from "./boundInstructorKey";

type Inventory = {
  status: "DETERMINISTIC_LINK_INVENTORY_ONLY" | "CONTEXT_MISMATCH";
  engagement_id: string;
  audited_actor_id: string;
  binding_manifest_sha256: string;
  bound_revision: number;
  selected_history_revision: number;
  current_revision: number;
  selected_state_sha256: string;
  selected_history_sha256: string;
  selected_history_tip_sha256: string;
  grading: "NOT_PERFORMED";
  professional_validation: "UNVALIDATED";
  mismatches: string[];
  limits: string[];
  sources?: Row[];
  expectations?: Row[];
  audited_actor_activity?: Row[];
  shared_workspace_activity_count?: number;
};
export function InstructorComparison({
  engagement: e,
  bound,
}: {
  engagement: Engagement;
  bound: BoundResponse;
}) {
  const [revision, setRevision] = useState(String(e.revision));
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
        `/api/engagements/${encodeURIComponent(e.id)}/instructor-comparison?revision=${revision}`,
      );
      if (current !== epoch.current) return;
      if (
        value.engagement_id !== e.id ||
        value.audited_actor_id !== bound.snapshot.audited_actor_id ||
        ![
          value.selected_state_sha256,
          value.selected_history_sha256,
          value.selected_history_tip_sha256,
        ].every(
          (pin) => typeof pin === "string" && /^[a-f0-9]{64}$/.test(pin),
        ) ||
        (value.expectations ?? []).some(
          (item) =>
            !bound.snapshot.authored.expectations.some(
              (expected) => expected.id === item.expectation_id,
            ),
        ) ||
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
      setResult(value);
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
          <details>
            <summary>Selected history pins and limits</summary>
            <dl>
              <dt>State</dt>
              <dd>
                <code>{result.selected_state_sha256}</code>
              </dd>
              <dt>History prefix</dt>
              <dd>
                <code>{result.selected_history_sha256}</code>
              </dd>
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
