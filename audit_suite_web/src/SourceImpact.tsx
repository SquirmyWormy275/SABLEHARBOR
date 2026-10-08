import SourceImpactDisposition, {
  SourceImpactDispositionHistory,
} from "./SourceImpactDisposition";
import {
  impactContext,
  impactReference,
  impactTraceLinks,
  validateImpact,
  type ImpactReport,
} from "./sourceImpact";
import { useRef, useEffect, useState } from "react";
import { request, str, type Engagement, type Row } from "./api";
import {
  deferredPaper,
  deferredTrace,
  loadWorkspaceDetail,
  mergeWorkspaceRecord,
  workspaceContext,
} from "./workspaceDetail";
export default function SourceImpact({
  engagement: e,
  onPreview,
  viewerId = "",
  dispositionsEnabled = false,
  onState,
}: {
  engagement: Engagement;
  viewerId?: string;
  dispositionsEnabled?: boolean;
  onState?: (state: Engagement) => void;
  onPreview: (kind: string, row: Row, reference?: Row) => void;
}) {
  const [stored, setStored] = useState<{
    report: ImpactReport;
    context: string;
  } | null>(null);
  const context = impactContext(e);
  const result = stored?.context === context ? stored.report : null;
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const epoch = useRef(0);
  const readContext = workspaceContext(e, viewerId),
    liveRead = useRef(readContext);
  liveRead.current = readContext;
  const [readRows, setReadRows] = useState<{
      key: string;
      rows: Record<string, Row>;
    }>({ key: "", rows: {} }),
    [reading, setReading] = useState<Record<string, boolean>>({}),
    [readErrors, setReadErrors] = useState<Record<string, string>>({});
  const visible: Engagement =
    readRows.key === readContext
      ? {
          ...e,
          workpapers: e.workpapers.map(
            (row) => readRows.rows["workpapers:" + row.id] ?? row,
          ),
          sample_executions: Array.isArray(e.sample_executions)
            ? e.sample_executions.map(
                (row: Row) =>
                  readRows.rows["sample_executions:" + row.id] ?? row,
              )
            : e.sample_executions,
        }
      : e;
  async function readReference(
    collection: "workpapers" | "sample_executions",
    row: Row,
    version?: number,
  ) {
    const captured = readContext,
      id = collection + ":" + row.id;
    setReading((prior) => ({ ...prior, [id]: true }));
    setReadErrors((prior) => ({ ...prior, [id]: "" }));
    try {
      const full = await loadWorkspaceDetail(e, collection, row, version);
      if (liveRead.current !== captured) return;
      setReadRows((prior) => ({
        key: captured,
        rows: {
          ...(prior.key === captured ? prior.rows : {}),
          [id]: mergeWorkspaceRecord(
            prior.key === captured ? (prior.rows[id] ?? row) : row,
            full,
          ),
        },
      }));
    } catch (err) {
      if (liveRead.current === captured)
        setReadErrors((prior) => ({ ...prior, [id]: (err as Error).message }));
    } finally {
      if (liveRead.current === captured)
        setReading((prior) => ({ ...prior, [id]: false }));
    }
  }
  function openReference(ref: Row, artifactId = str(ref.id)) {
    let required: {
      collection: "workpapers" | "sample_executions";
      row: Row;
      version?: number;
    } | null = null;
    if (ref.collection === "sample_executions") {
      const matches = (
        Array.isArray(visible.sample_executions)
          ? (visible.sample_executions as Row[])
          : []
      ).filter((row) => row.id === ref.id);
      if (matches.length === 1 && deferredTrace(matches[0]))
        required = { collection: "sample_executions", row: matches[0] };
    } else if (ref.collection === "reviews" && ref.anchor) {
      const matches = visible.workpapers.filter(
        (row) => row.id === ref.workpaper_id,
      );
      if (
        matches.length === 1 &&
        typeof ref.version === "number" &&
        deferredPaper(matches[0], ref.version)
      )
        required = {
          collection: "workpapers",
          row: matches[0],
          version: ref.version,
        };
    }
    if (required) {
      const value = required,
        id = value.collection + ":" + value.row.id;
      return (
        <span>
          <p>
            Exact retained details have not been loaded; their absence is not
            inferred.
          </p>
          <button
            disabled={reading[id]}
            onClick={() =>
              void readReference(value.collection, value.row, value.version)
            }
          >
            {reading[id]
              ? "Loading exact details…"
              : "Load exact retained details"}
          </button>
          {readErrors[id] && <p role="alert">{readErrors[id]}</p>}
        </span>
      );
    }
    const target = impactReference(visible, ref, artifactId);
    if (target?.kind === "sample_execution")
      return (
        <details>
          <summary>
            Inspect exact item {str(ref.item_id)} in trace {str(ref.id)}
          </summary>
          <p>
            {str(ref.trace_status)} · {str(ref.context_status)}
          </p>
          <p>
            Execution revision {str(ref.version)} · predecessor{" "}
            {str(ref.predecessor_id) || "none"} · successor{" "}
            {str(ref.successor_id) || "none"}
          </p>
          <p>Recorded observation: {str(target.item?.observation)}</p>
          <p>
            Recorded result: {str(target.item?.status)}. This does not change
            the result.
          </p>
          <p>
            Evidence SHA256: <code>{str(ref.artifact_sha256)}</code>
          </p>
          <p>
            Author-supplied locators, not independently verified matches:{" "}
            {Array.isArray(ref.locators)
              ? ref.locators.map(str).join("; ")
              : "none"}
          </p>
          {impactTraceLinks(visible, target.row).map((link) => (
            <span key={str(link.collection)}>
              {openReference(link, artifactId)}
            </span>
          ))}
          <p>
            Related work opens only when its current server-provided digest
            matches the trace. Historical context is not replaced with newer
            work.
          </p>
        </details>
      );
    return target ? (
      <span>
        <button
          type="button"
          onClick={() => onPreview(target.kind, target.row, target.reference)}
        >
          Open {target.kind} {str(ref.id)}
        </button>
        {target.workpaper && (
          <button
            type="button"
            onClick={() =>
              onPreview("workpaper", target.workpaper!.row, {
                id: target.workpaper!.row.id,
                collection: "workpapers",
                version: target.workpaper!.version,
              })
            }
          >
            Open reviewed workpaper version {target.workpaper.version}
          </button>
        )}
      </span>
    ) : (
      <span>Linked record is unavailable in this workspace.</span>
    );
  }
  useEffect(() => {
    epoch.current++;
    setStored(null);
    setError("");
    setBusy(false);
    return () => {
      epoch.current++;
    };
  }, [impactContext(e)]);
  useEffect(() => {
    liveRead.current = readContext;
    setReading({});
    setReadErrors({});
    return () => {
      liveRead.current = "";
    };
  }, [readContext]);
  async function check() {
    const current = ++epoch.current;
    setBusy(true);
    setError("");
    setStored(null);
    try {
      const value = await request<ImpactReport>(
        `/api/engagements/${encodeURIComponent(e.id)}/company/impact`,
      );
      if (current === epoch.current)
        setStored({ report: validateImpact(value, e), context });
    } catch (err) {
      if (current === epoch.current) setError((err as Error).message);
    } finally {
      if (current === epoch.current) setBusy(false);
    }
  }
  return (
    <details className="panel">
      <summary>Check collected sources for changes</summary>
      <p>
        Compare retained company-source versions with currently available
        versions. Your evidence and conclusions remain unchanged.
      </p>
      <button disabled={busy} onClick={() => void check()}>
        {busy ? "Checking source versions…" : "Check source changes"}
      </button>
      {error && <p role="alert">{error}</p>}
      <SourceImpactDispositionHistory
        engagement={e}
        enabled={dispositionsEnabled}
      />
      {result && (
        <>
          <p>
            {result.compared_artifacts} retained artifacts compared ·{" "}
            {result.changes.length} later source versions observed ·{" "}
            {result.unavailable_comparisons} comparisons unavailable.
            Unavailable comparisons do not establish unchanged sources, a
            change, or a deficiency.
          </p>
          <p>
            Report read interval: {result.started_at} — {result.completed_at}.
          </p>
          <p>
            Simulation availability cutoff: {result.simulated_as_of}. Sources
            are read separately; this is not a synchronized portfolio snapshot.
            Later source appends can fall outside the comparison. No evidence or
            conclusion is automatically invalidated.
          </p>
          <ul>
            {result.changes.map((r) => (
              <li key={str(r.artifact_id)}>
                <strong>{str(r.artifact_id)}</strong>: collected version{" "}
                {str(r.collected_version)} → visible version{" "}
                {str(r.latest_visible_version)}
                {openReference({
                  collection: "artifacts",
                  id: str(r.artifact_id),
                  sha256: r.collected_sha256,
                })}
                {Boolean(r.source_identity) && (
                  <div>
                    <p>
                      Original source:{" "}
                      {["company", "branch", "system", "record"]
                        .map((k) => str((r.source_identity as Row)[k]))
                        .join(" / ")}
                    </p>
                    {Boolean(
                      (r.source_identity as Row).source_system_alias,
                    ) && (
                      <p>
                        Collection route:{" "}
                        {str((r.source_identity as Row).source_system_alias)} ·
                        Source store:{" "}
                        {str((r.source_identity as Row).source_store_id)} ·
                        Registry SHA256:{" "}
                        <code>
                          {str((r.source_identity as Row).registry_sha256)}
                        </code>
                      </p>
                    )}
                  </div>
                )}
                <p>
                  Source discovered: {str(r.discovered_at)} · Identity
                  rechecked: {str(r.rechecked_at)}
                </p>
                <p>
                  Collected SHA256: <code>{str(r.collected_sha256)}</code>
                </p>
                <p>
                  Observed SHA256: <code>{str(r.latest_visible_sha256)}</code>
                </p>
                {Boolean(r.latest_source_qualifiers) &&
                  Object.keys(r.latest_source_qualifiers as object).length >
                    0 && (
                    <div>
                      <p>
                        Labels recorded by the source for the later version; a
                        correction or withdrawal label does not automatically
                        invalidate retained evidence:
                      </p>
                      <ul>
                        {Object.entries(
                          r.latest_source_qualifiers as Record<string, unknown>,
                        ).map(([key, value]) => (
                          <li key={key}>
                            {key}: {str(value)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                {onState && (
                  <SourceImpactDisposition
                    engagement={e}
                    viewerId={viewerId}
                    artifactId={str(r.artifact_id)}
                    enabled={dispositionsEnabled}
                    onState={onState}
                  />
                )}
                <p>
                  Review these directly linked records before deciding whether
                  further work is needed:
                </p>
                <ul>
                  {(r.references as Row[]).map((ref, i) => (
                    <li key={i}>
                      {str(ref.collection)} · {str(ref.id)}
                      {ref.version !== undefined
                        ? ` · version ${str(ref.version)}`
                        : ""}
                      {Boolean(ref.version_status) && (
                        <p>
                          {str(ref.version_status)} retained workpaper version ·{" "}
                          {str(ref.review_scope)}
                        </p>
                      )}
                      {Boolean(ref.reference_scope) && (
                        <p>
                          {str(ref.reference_scope)}
                          {ref.remediation_id
                            ? ` · ${str(ref.remediation_id)}`
                            : ""}
                        </p>
                      )}
                      {Boolean(ref.anchor) && (
                        <blockquote>
                          {str((ref.anchor as Row).excerpt)}
                        </blockquote>
                      )}
                      {openReference(ref, str(r.artifact_id))}
                    </li>
                  ))}
                </ul>
                {(r.references as Row[]).length === 0 && (
                  <p>
                    No directly linked work is recorded. Review the retained
                    source before deciding what to collect or test next.
                  </p>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </details>
  );
}
