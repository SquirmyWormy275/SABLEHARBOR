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
  const [result, setResult] = useState<{
    changes: Row[];
    unavailable_comparisons: number;
  } | null>(null);
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
  }, [e.id, e.revision]);
  async function check() {
    const current = ++epoch.current;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const value = await request<{
        changes: Row[];
        unavailable_comparisons: number;
      }>(`/api/engagements/${encodeURIComponent(e.id)}/company/impact`);
      if (current === epoch.current) setResult(value);
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
            {result.changes.length} source changes found ·{" "}
            {result.unavailable_comparisons} comparisons unavailable. This
            checks observable versions, not evidence sufficiency.
          </p>
          <ul>
            {result.changes.map((r) => (
              <li key={str(r.artifact_id)}>
                <strong>{str(r.artifact_id)}</strong>: collected version{" "}
                {str(r.collected_version)} → visible version{" "}
                {str(r.latest_visible_version)}
                {openReference({ collection: "artifacts", id: str(r.artifact_id) })}
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
