import { useEffect, useRef, useState } from "react";
import { ApiError, request, requestDownload, type Engagement } from "./api";
import {
  assistanceContext,
  assistancePointer,
  type Pointer,
} from "./instructorAssistance";
import {
  exportPreviewMatches,
  type SelectedDebrief,
  type DebriefExportPreview,
} from "./instructorDebrief";
export function DebriefDocument({
  document,
  engagement,
  onOpenPointer,
}: {
  document: SelectedDebrief;
  engagement?: Engagement;
  onOpenPointer?: (p: Pointer) => void;
}) {
  return (
    <article aria-label="Selected debrief document">
      <h3>{document.title}</h3>
      <p>
        Instructor-authored explanation · version {document.version}.
        Professional validation is not asserted.
      </p>
      <p>
        Selected learner history revision {document.learner.revision}. Shared
        engagement work is not an individual submission or proof of performance.
      </p>
      <p>
        The Key and selected support may postdate this learner history snapshot.
        Their inclusion does not establish availability at that time.
      </p>
      {document.sections.map((s, i) => (
        <section key={i}>
          <h4>Section {i + 1}</h4>
          {s.issues.map((issue) => (
            <div key={issue.id}>
              <h5>Selected issue {issue.id}</h5>
              <p>{issue.claim}</p>
              {issue.uncertainty && (
                <p>Authored uncertainty: {issue.uncertainty}</p>
              )}
              <p>Controls: {issue.control_ids.join(", ")}</p>
            </div>
          ))}
          {s.expectations.map((x) => (
            <div key={x.id}>
              <h5>Selected expectation {x.id}</h5>
              <p>{x.procedure}</p>
              {x.acceptable_alternatives.length > 0 && (
                <>
                  <p>Authored acceptable alternatives</p>
                  <ul>
                    {x.acceptable_alternatives.map((a, j) => (
                      <li key={j}>{a}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          ))}
          <h5>Explanation</h5>
          <p className="prewrap">{s.explanation}</p>
          <h5>Limitations</h5>
          <p className="prewrap">{s.limitations}</p>
          <h5>Discussion prompts</h5>
          <ol>
            {s.prompts.map((p, j) => (
              <li key={j}>{p}</li>
            ))}
          </ol>
          {s.annotations.map((a, j) => {
            const p: Pointer = {
              kind: "artifact",
              id: a.artifact_id,
              sha256: a.sha256,
            };
            return (
              <div key={j}>
                <h5>Annotated original {a.artifact_id}</h5>
                <p>{a.note}</p>
                {a.locator && (
                  <p>
                    Instructor-supplied locator: {a.locator.kind}{" "}
                    {a.locator.value} (not independently verified).
                  </p>
                )}
                <p>
                  {a.attach
                    ? "Selected for portable attachment"
                    : "Reference only; original bytes not selected for export"}
                </p>
                <details>
                  <summary>Exact original pin</summary>
                  <p>SHA256 {a.sha256}</p>
                </details>
                {engagement &&
                  onOpenPointer &&
                  assistancePointer(engagement, p) && (
                    <button
                      onClick={() => {
                        if (assistancePointer(engagement, p)) onOpenPointer(p);
                      }}
                    >
                      Open exact original {a.artifact_id}
                    </button>
                  )}
              </div>
            );
          })}
        </section>
      ))}
      <details>
        <summary>Debrief provenance</summary>
        <p>Key manifest SHA256 {document.key_manifest_sha256}</p>
        {document.learner.simulated_at && (
          <p>Historical snapshot time {document.learner.simulated_at}</p>
        )}
        {document.source_references.map((r) => (
          <section key={r.artifact_id}>
            <h5>Selected original provenance {r.artifact_id}</h5>
            <p>
              Retained SHA256 {r.artifact_sha256} · {r.status}
            </p>
            {r.native ? (
              <>
                <p>
                  {r.native.company} / {r.native.branch} / {r.native.system} /{" "}
                  {r.native.record} · version {r.native.version}
                </p>
                <p>Native SHA256 {r.native.sha256}</p>
                {r.native.source_store_id && (
                  <p>
                    Source store {r.native.source_store_id} · alias{" "}
                    {r.native.source_system_alias} · registry SHA256{" "}
                    {r.native.registry_sha256}
                  </p>
                )}
                {r.native.portfolio_qualification && (
                  <p>{r.native.portfolio_qualification}</p>
                )}
              </>
            ) : (
              <p>
                Exact native identity was not recorded for this retained
                original.
              </p>
            )}
          </section>
        ))}
        <p>
          Learner {document.learner.actor_id} · state SHA256{" "}
          {document.learner.state_sha256}
        </p>
        {document.schema === "SELECTED_INSTRUCTOR_DEBRIEF_V2" ? (
          <p>
            History integrity reference · {document.learner.history_integrity_reference.kind === "ROOT_ACCEPTED_BASE" ? "Verified baseline" : "Verified recorded update"}
            {" · checkpoint SHA256 "}{document.learner.history_integrity_reference.checkpoint_sha256}
            {" · event SHA256 "}{document.learner.event_sha256}
          </p>
        ) : (
          <p>
            History SHA256 {document.learner.history_sha256} · event SHA256{" "}
            {document.learner.event_sha256}
          </p>
        )}
        {document.predecessor && (
          <p>
            Predecessor {document.predecessor.release_id} · SHA256{" "}
            {document.predecessor.release_sha256}
          </p>
        )}
        <p>{document.qualification}</p>
        <p>{document.learner.qualification}</p>
      </details>
    </article>
  );
}
export function DebriefExport(props: {
  engagement: Engagement;
  viewerId: string;
  releaseId: string;
  releaseSha256: string;
}) {
  return (
    <ExportPanel
      key={
        assistanceContext(props.engagement, props.viewerId) +
        props.releaseId +
        props.releaseSha256
      }
      {...props}
    />
  );
}
function ExportPanel({
  engagement: e,
  viewerId,
  releaseId,
  releaseSha256,
}: {
  engagement: Engagement;
  viewerId: string;
  releaseId: string;
  releaseSha256: string;
}) {
  const base = `/api/engagements/${encodeURIComponent(e.id)}/assistance/${encodeURIComponent(releaseId)}`;
  const [preview, setPreview] = useState<DebriefExportPreview | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [retry, setRetry] = useState(false);
  const alive = useRef(true),
    pending = useRef<{
      preview_id: string;
      preview_sha256: string;
      command_id: string;
    } | null>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const valid = (p: DebriefExportPreview) =>
    exportPreviewMatches(p, e.id, viewerId, releaseId, releaseSha256);
  async function inspect() {
    setBusy(true);
    setError("");
    setPreview(null);
    pending.current = null;
    setRetry(false);
    try {
      const p = await request<DebriefExportPreview>(
        base + "/export-preview",
        "POST",
        { release_sha256: releaseSha256 },
      );
      if (!alive.current) return;
      if (!valid(p))
        throw Error("Export preview does not match this exact release.");
      setPreview(p);
    } catch (err) {
      if (alive.current) setError((err as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  async function download() {
    if (!preview || (!pending.current && !valid(preview))) return;
    setBusy(true);
    setError("");
    const body = pending.current ?? {
      preview_id: preview.preview.id,
      preview_sha256: preview.preview_sha256,
      command_id: crypto.randomUUID(),
    };
    pending.current = body;
    try {
      const blob = await requestDownload(base + "/export", body, {
        sha256: preview.preview.sha256,
        bytes: preview.preview.bytes,
        maxBytes: 20 * 1024 * 1024,
      });
      if (!alive.current) return;
      const url = URL.createObjectURL(blob),
        a = window.document.createElement("a");
      a.href = url;
      a.download = preview.preview.filename;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      pending.current = null;
      setRetry(false);
      setPreview(null);
      setNotice(
        "Verified portable debrief downloaded. Later revocation cannot recall this copy.",
      );
    } catch (err) {
      if (!alive.current) return;
      setError((err as Error).message);
      if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
        pending.current = null;
        setRetry(false);
        setPreview(null);
      } else setRetry(true);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <section aria-label="Portable debrief export">
      <button disabled={busy || retry} onClick={() => void inspect()}>
        Preview portable export
      </button>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      {preview && (
        <>
          <h4>Files in this export</h4>
          <p>
            {preview.preview.filename} · {preview.preview.bytes} bytes
          </p>
          <ul>
            {preview.preview.members.map((m) => (
              <li key={m.name}>
                {m.name} · {m.bytes} bytes
                <details>
                  <summary>File digest</summary>
                  {m.sha256}
                </details>
              </li>
            ))}
          </ul>
          <p>
            This copy includes only the listed files. Revocation cannot remove
            downloaded copies.
          </p>
          <button
            disabled={busy || (!retry && !valid(preview))}
            onClick={() => void download()}
          >
            {retry
              ? "Retry exact export request"
              : "Confirm and download this export"}
          </button>
          {retry && (
            <button
              disabled={busy}
              onClick={() => {
                pending.current = null;
                setRetry(false);
                setPreview(null);
              }}
            >
              Discard pending export request
            </button>
          )}
        </>
      )}
    </section>
  );
}
