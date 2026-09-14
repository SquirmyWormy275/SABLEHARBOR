import {
  impactContext,
  validateImpact,
  type ImpactReport,
} from "./sourceImpact";
import { useRef, useEffect, useState } from "react";
import { request, str, type Engagement, type Row } from "./api";
import { sourceReference } from "./sourceReferences";
export default function SourceImpact({
  engagement: e,
  onPreview,
}: {
  engagement: Engagement;
  onPreview: (kind: string, row: Row) => void;
}) {
  const [result, setResult] = useState<ImpactReport | null>(null);
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const epoch = useRef(0);
  function openReference(ref: Row) {
    const target = sourceReference(e, ref);
    return target ? (
      <button type="button" onClick={() => onPreview(target.kind, target.row)}>
        Open {target.kind} {str(ref.id)}
      </button>
    ) : (
      <span>Linked record is unavailable in this workspace.</span>
    );
  }
  useEffect(() => {
    epoch.current++;
    setResult(null);
    setError("");
    setBusy(false);
    return () => {
      epoch.current++;
    };
  }, [impactContext(e)]);
  async function check() {
    const current = ++epoch.current;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const value = await request<ImpactReport>(
        `/api/engagements/${encodeURIComponent(e.id)}/company/impact`,
      );
      if (current === epoch.current) setResult(validateImpact(value, e));
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
                      {openReference(ref)}
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
