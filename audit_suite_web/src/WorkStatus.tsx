import { useEffect, useRef, useState } from "react";
import { request, str, type Engagement, type Row } from "./api";
import { sourceReference } from "./sourceReferences";
import { ProcedureTraceReadiness } from "./ProcedureTraceReadiness";
import { resolveTraceReference, type TraceReadiness } from "./traceReadiness";
import type { ContextLink } from "./investigationContext";
import {
  currentIntegrity,
  integrityStatusLabels,
  type OriginalIntegrity,
} from "./procedureIntegrity";
const explanations: Record<string, string> = {
  NO_ISSUED_REQUEST: "No issued request is linked to this control.",
  OUTSTANDING_RESPONSE:
    "An issued request is awaiting a response or clarification.",
  RETAINED_ARTIFACT_WITHOUT_WORKPAPER_LINK:
    "Retained evidence has no recorded link in this control’s workpapers.",
  PROVISIONAL_POPULATION: "A linked population is still provisional.",
  NO_CURRENT_DISTINCT_CONTRIBUTOR_REVIEW_RECORD:
    "No current review by a different contributor is recorded. This does not assess professional independence.",
  RECORDED_SOURCE_OR_ARTIFACT_WARNING:
    "A retained source pin or artifact status needs inspection.",
  WORKPAPER_REFERENCES_MISSING_ARTIFACT:
    "A workpaper references an artifact absent from this workspace.",
};
const collections: Record<string, string> = {
  control: "controls",
  task: "tasks",
  request: "requests",
  artifact: "artifacts",
  population: "populations",
  selection: "selections",
  workpaper: "workpapers",
  review: "reviews",
};
type Report = {
  engagement_id: string;
  engagement_revision: number;
  controls: Row[];
  denominators: Record<string, number>;
  limits: string[];
};
export function WorkStatus({
  engagement: e,
  onPreview,
}: {
  engagement: Engagement;
  onPreview: (kind: string, row: Row, reference?: ContextLink) => void;
}) {
  const [report, setReport] = useState<Report | null>(null),
    [integrity, setIntegrity] = useState<OriginalIntegrity | null>(null),
    [selected, setSelected] = useState(""),
    [error, setError] = useState(""),
    [integrityError, setIntegrityError] = useState(""),
    [busy, setBusy] = useState(false),
    [integrityBusy, setIntegrityBusy] = useState(false);
  const epoch = useRef(0);
  const allowed = e.permissions?.some((permission) =>
    ["learn", "review", "instruct"].includes(permission),
  );
  const visibleIntegrity =
    integrity && currentIntegrity(integrity, e) ? integrity : null;
  useEffect(() => {
    epoch.current++;
    setReport(null);
    setIntegrity(null);
    setSelected("");
    setError("");
    setIntegrityError("");
    setBusy(false);
    setIntegrityBusy(false);
    return () => {
      epoch.current++;
    };
  }, [
    e.id,
    e.revision,
    JSON.stringify(e.permissions),
    JSON.stringify(e.scope),
    JSON.stringify(e.company_source_binding),
    JSON.stringify(e.evidence_acquisition),
  ]);
  async function check() {
    if (!allowed) return;
    setReport(null);
    setIntegrity(null);
    setIntegrityError("");
    setIntegrityBusy(false);
    const current = ++epoch.current;
    setBusy(true);
    setError("");
    try {
      const result = await request<Report>(
        `/api/engagements/${encodeURIComponent(e.id)}/work-status`,
      );
      if (current === epoch.current) {
        if (
          result.engagement_id !== e.id ||
          result.engagement_revision !== e.revision
        )
          throw Error(
            "Work changed. Refresh this engagement before checking its status.",
          );
        setReport(result);
      }
    } catch (err) {
      if (current === epoch.current) setError((err as Error).message);
    } finally {
      if (current === epoch.current) setBusy(false);
    }
  }
  async function checkIntegrity() {
    if (!allowed) return;
    const current = ++epoch.current;
    setIntegrity(null);
    setIntegrityError("");
    setIntegrityBusy(true);
    try {
      const result = await request<OriginalIntegrity>(
        `/api/engagements/${encodeURIComponent(e.id)}/procedure-original-integrity`,
      );
      if (current === epoch.current) {
        if (!currentIntegrity(result, e))
          throw Error(
            "Work changed. Refresh this engagement before rechecking originals.",
          );
        setIntegrity(result);
      }
    } catch (err) {
      if (current === epoch.current) setIntegrityError((err as Error).message);
    } finally {
      if (current === epoch.current) setIntegrityBusy(false);
    }
  }
  const control = report?.controls.find(
    (c) =>
      str(c.control_id) === selected ||
      str((c.control as Row)?.id) === selected,
  );
  function reference(ref: Row) {
    const exact: ContextLink | undefined =
      ref.kind === "workpaper" &&
      typeof ref.version === "number" &&
      typeof ref.version_digest === "string"
        ? {
            kind: "workpaper",
            id: ref.id,
            version: ref.version,
            sha256: ref.version_digest,
          }
        : undefined;
    const exactRow = exact ? resolveTraceReference(e, exact) : null;
    const target = exact
      ? exactRow
        ? { kind: exact.kind, row: exactRow }
        : null
      : sourceReference(e, {
          ...ref,
          collection: collections[str(ref.kind)],
        });
    return target ? (
      <button
        type="button"
        onClick={() => onPreview(target.kind, target.row, exact)}
      >
        Open {target.kind} {ref.id}
        {ref.version !== undefined
          ? ` · linked version ${str(ref.version)}`
          : ""}
      </button>
    ) : (
      <span>Linked record is unavailable in this workspace.</span>
    );
  }
  if (!allowed) return null;
  return (
    <details className="panel work-status">
      <summary>Recorded work and open dependencies</summary>
      <p>
        See what is recorded for each scoped control. Collected files and
        completed tasks do not establish effectiveness.
      </p>
      <button disabled={busy} onClick={() => void check()}>
        {busy ? "Checking recorded work…" : "Check work status"}
      </button>
      {error && <p role="alert">{error}</p>}
      {report && (
        <>
          <div className="actions">
            <button
              type="button"
              disabled={integrityBusy || busy}
              onClick={() => void checkIntegrity()}
            >
              {integrityBusy
                ? "Rechecking retained originals…"
                : "Recheck cited retained originals"}
            </button>
          </div>
          {integrityError && <p role="alert">{integrityError}</p>}
          {visibleIntegrity && (
            <section aria-label="Retained original byte check">
              <p role="status">
                {integrityStatusLabels[visibleIntegrity.status]}
              </p>
              {visibleIntegrity.counts ? (
                <p>
                  {visibleIntegrity.counts.verified} verified ·{" "}
                  {visibleIntegrity.counts.missing} missing ·{" "}
                  {visibleIntegrity.counts.integrity_failure} changed ·{" "}
                  {visibleIntegrity.counts.read_unavailable} unreadable of{" "}
                  {visibleIntegrity.counts.referenced} cited retained originals.
                </p>
              ) : (
                <p>
                  Byte counts unavailable; no zero count or success is implied.
                </p>
              )}
              <p>
                This checks retained copy bytes at this engagement revision. It
                does not check company source freshness, population
                completeness, procedure sufficiency or audit credit.
              </p>
            </section>
          )}
          <p>
            {report.denominators.scoped_controls} scoped controls ·{" "}
            {report.denominators.scoped_procedures} assigned procedures ·{" "}
            {report.denominators.unassigned_or_out_of_scope_tasks} unassigned or
            outside-scope tasks. The procedure count includes{" "}
            {report.denominators.known_not_applicable_tasks} recorded
            exclusions.
          </p>
          <label>
            Inspect control status
            <select
              aria-label="Inspect control status"
              value={selected}
              onChange={(ev) => setSelected(ev.target.value)}
            >
              <option value="">Choose a scoped control</option>
              {e.controls.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} · {str(c.title)}
                </option>
              ))}
            </select>
          </label>
          {control && (
            <>
              <h3>{selected}</h3>
              <p>
                {str(control.procedure_denominator)} assigned procedures.
                Control effectiveness has not been assessed by this view.
              </p>
              {(control.reasons as Row[]).length === 0 && (
                <p>
                  No listed administrative dependency was identified. Review the
                  underlying work; this is not an assurance conclusion.
                </p>
              )}
              <ul>
                {(control.reasons as Row[]).map((reason, index) => (
                  <li key={index}>
                    <p>
                      {explanations[str(reason.code)] ??
                        "Inspect the linked work and its recorded status."}
                    </p>
                    {(reason.references as Row[]).map((ref, i) => (
                      <span className="actions" key={i}>
                        {reference(ref)}
                      </span>
                    ))}
                  </li>
                ))}
              </ul>
              <details>
                <summary>Exact procedure and source records</summary>
                <ul>
                  {(control.procedures as Row[]).map((p, i) => (
                    <li key={i}>
                      {reference(p.task as Row)} · Recorded state:{" "}
                      {str(p.recorded_status)} · Conclusion:{" "}
                      {str(p.recorded_conclusion)}
                      <ul>
                        {((p.workpaper_links as Row[]) ?? []).map(
                          (link, index) => (
                            <li key={index}>
                              {reference(link)} ·{" "}
                              {link.current_version
                                ? "Current version link"
                                : "Historical version link; absent from latest unless separately listed"}
                            </li>
                          ),
                        )}
                      </ul>
                      {Array.isArray(p.legacy_unversioned_workpaper_links) &&
                        p.legacy_unversioned_workpaper_links.length > 0 && (
                          <p>
                            Legacy links have no workpaper version provenance.
                          </p>
                        )}
                      <ProcedureTraceReadiness
                        engagement={e}
                        data={
                          p.sample_trace_readiness as TraceReadiness | undefined
                        }
                        integrity={visibleIntegrity ?? undefined}
                        onPreview={onPreview}
                      />
                    </li>
                  ))}
                </ul>
                {(control.sources as Row[]).map((s, i) => (
                  <section key={i}>
                    {reference(s.artifact as Row)}
                    <ul>
                      {(s.qualifiers as Row[]).map((q, j) => (
                        <li key={j}>
                          {str(q.field)}: {str(q.value)}
                        </li>
                      ))}
                    </ul>
                    <p>
                      Source freshness and original bytes were not rechecked by
                      this status report.
                    </p>
                  </section>
                ))}
              </details>
            </>
          )}
          <details>
            <summary>What this check covers</summary>
            <ul>
              {report.limits.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </details>
  );
}
