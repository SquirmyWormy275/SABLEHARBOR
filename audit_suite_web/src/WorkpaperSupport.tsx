import { useEffect, useId, useRef, useState } from "react";
import { artifactURL, type Engagement } from "./api";
import {
  acceptsPreview,
  availableArtifact,
  evidenceReference,
  loadTextPreview,
  previewKey,
  record,
  supportingTasks,
  textPreviewAllowed,
} from "./workpaperSupport";
import "./workpaperSupport.css";
type Props = {
  engagement: Engagement;
  viewerId: string;
  values: Readonly<Record<string, unknown>>;
  onTaskIds?: (ids: string[]) => void;
  onAppendEvidence?: (artifactId: string) => void;
};
export function WorkpaperSupport({
  engagement,
  viewerId,
  values,
  onAppendEvidence,
  onTaskIds,
}: Props) {
  const label = useId();
  const [controlId, setControl] = useState(
    String(
      values.control_id ??
        engagement.workpapers.find((row) => row.id === values.workpaper_id)
          ?.control_id ??
        "",
    ),
  );
  const [taskId, setTask] = useState("");
  const [artifactId, setArtifact] = useState("");
  const [preview, setPreview] = useState<{ key: string; text: string } | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const abort = useRef<AbortController | null>(null);
  const current = useRef({ engagement, viewerId, artifactId });
  current.current = { engagement, viewerId, artifactId };
  const artifact = availableArtifact(engagement, artifactId);
  const key = artifact ? previewKey(viewerId, engagement, artifact) : "";
  useEffect(() => {
    abort.current?.abort();
    setPreview(null);
    setMessage("");
    setBusy(false);
    return () => abort.current?.abort();
  }, [key]);
  useEffect(() => {
    setControl(
      String(
        values.control_id ??
          engagement.workpapers.find((row) => row.id === values.workpaper_id)
            ?.control_id ??
          "",
      ),
    );
    setTask("");
    setArtifact("");
  }, [viewerId, engagement.id]);
  useEffect(() => {
    setControl(
      String(
        values.control_id ??
          engagement.workpapers.find((row) => row.id === values.workpaper_id)
            ?.control_id ??
          "",
      ),
    );
    setTask("");
  }, [values.control_id]);
  const paperControl =
    values.control_id ??
    engagement.workpapers.find((row) => row.id === values.workpaper_id)
      ?.control_id;
  const linkedTasks = Array.isArray(values.task_ids)
    ? values.task_ids.filter((id): id is string => typeof id === "string")
    : [];
  const control = engagement.controls.find((row) => row.id === controlId);
  const tasks = supportingTasks(engagement, controlId);
  const task = tasks.find((row) => row.id === taskId);
  const source = record(record(record(artifact?.source).receipt).source);
  const coverage = record(artifact?.coverage);
  async function inspect() {
    if (!artifact) return;
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    const expected = key,
      selected = artifact;
    setBusy(true);
    setMessage("");
    setPreview(null);
    try {
      const text = await loadTextPreview(
        engagement.id,
        selected,
        controller.signal,
      );
      const latest = current.current;
      if (
        !controller.signal.aborted &&
        latest.artifactId === selected.id &&
        acceptsPreview(
          expected,
          latest.viewerId,
          latest.engagement,
          selected.id,
        )
      )
        setPreview({ key: expected, text });
    } catch (error) {
      const latest = current.current;
      if (
        !controller.signal.aborted &&
        latest.artifactId === selected.id &&
        acceptsPreview(
          expected,
          latest.viewerId,
          latest.engagement,
          selected.id,
        )
      )
        setMessage(
          error instanceof Error ? error.message : "Preview unavailable.",
        );
    } finally {
      if (abort.current === controller) setBusy(false);
    }
  }
  return (
    <aside className="workpaper-support" aria-labelledby={label}>
      <h3 id={label}>Inspect support while drafting</h3>
      <p>
        Selections do not change your draft or establish a conclusion. Add an
        evidence or procedure reference only when you choose.
      </p>
      <div className="support-columns">
        <section aria-label="Scoped control and procedure">
          <label>
            Support control
            <select
              aria-label="Support control"
              value={control?.id ?? ""}
              onChange={(e) => {
                setControl(e.target.value);
                setTask("");
              }}
            >
              <option value="">Choose scoped control</option>
              {engagement.controls.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.id} · {String(row.title ?? row.name ?? "")}
                </option>
              ))}
            </select>
          </label>
          {control && (
            <p>
              {String(
                control.description ??
                  control.statement ??
                  "No statement supplied.",
              )}
            </p>
          )}
          <label>
            Support procedure
            <select
              aria-label="Support procedure"
              value={task?.id ?? ""}
              disabled={!control}
              onChange={(e) => setTask(e.target.value)}
            >
              <option value="">Choose linked procedure</option>
              {tasks.map((row) => (
                <option key={row.id} value={row.id}>
                  {String(row.title ?? row.id)}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={
              !onTaskIds ||
              !task ||
              task.control_id !== paperControl ||
              linkedTasks.includes(task.id)
            }
            onClick={() => {
              if (task && task.control_id === paperControl)
                onTaskIds?.([...linkedTasks, task.id]);
            }}
          >
            Link selected procedure to this version
          </button>
          <p>
            Procedure links record what this version addresses; they do not
            complete tests.
          </p>
          <ul>
            {linkedTasks.map((id) => (
              <li key={id}>
                {id}
                <button
                  type="button"
                  disabled={!onTaskIds}
                  onClick={() =>
                    onTaskIds?.(linkedTasks.filter((value) => value !== id))
                  }
                >
                  Remove procedure {id}
                </button>
              </li>
            ))}
          </ul>
          {control && !tasks.length && (
            <p>No task explicitly references this control.</p>
          )}
          {task && (
            <div>
              <strong>{task.id}</strong>
              <p>
                {String(task.procedure ?? task.description ?? task.title ?? "")}
              </p>
              <p>Status: {String(task.status ?? "Not supplied")}</p>
              <p>{String(task.rationale ?? "")}</p>
            </div>
          )}
        </section>
        <section aria-label="Retained original evidence">
          <label>
            Support evidence
            <select
              aria-label="Support evidence"
              value={artifact?.id ?? ""}
              onChange={(e) => setArtifact(e.target.value)}
            >
              <option value="">Choose available original</option>
              {engagement.artifacts
                .filter((row) => row.status === "AVAILABLE")
                .map((row) => (
                  <option key={row.id} value={row.id}>
                    {String(row.name ?? row.id)} · {row.id}
                  </option>
                ))}
            </select>
          </label>
          {!engagement.artifacts.some((row) => row.status === "AVAILABLE") && (
            <p>No available originals retained.</p>
          )}
          {artifact && (
            <>
              <dl className="support-metadata">
                <dt>Artifact</dt>
                <dd>{artifact.id}</dd>
                <dt>Source / version</dt>
                <dd>
                  {source.record
                    ? `${String(source.system)}/${String(source.record)} v${String(source.version)}`
                    : "No company source-version receipt"}
                </dd>
                <dt>SHA-256</dt>
                <dd>{String(artifact.sha256)}</dd>
                <dt>Request</dt>
                <dd>
                  {String(
                    artifact.request_id ?? coverage.request_id ?? "Not linked",
                  )}
                </dd>
                <dt>Evidence coverage period</dt>
                <dd>
                  {coverage.period_start
                    ? `${String(coverage.period_start)} — ${String(coverage.period_end ?? "Not supplied")}`
                    : "Not supplied; audit period is not inferred as evidence coverage"}
                </dd>
                <dt>Available / imported</dt>
                <dd>
                  {String(source.available_at ?? "Not supplied")} /{" "}
                  {String(source.imported_at ?? "Not supplied")}
                </dd>
              </dl>
              <div className="support-actions">
                <a href={artifactURL(engagement.id, artifact.id)} download>
                  Download original
                </a>
                <button
                  type="button"
                  disabled={busy || !textPreviewAllowed(artifact)}
                  onClick={inspect}
                >
                  {busy ? "Loading…" : "Preview text"}
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(
                        evidenceReference(artifact),
                      );
                      setMessage("Reference copied.");
                    } catch {
                      setMessage(
                        "Copy unavailable. Select the reference text below.",
                      );
                    }
                  }}
                >
                  Copy exact reference
                </button>
                {onAppendEvidence && (
                  <button
                    type="button"
                    onClick={() => {
                      if (availableArtifact(engagement, artifact.id))
                        onAppendEvidence(artifact.id);
                    }}
                  >
                    Add evidence reference to draft
                  </button>
                )}
              </div>
              <p className="support-reference" tabIndex={0}>
                {evidenceReference(artifact)}
              </p>
              {!textPreviewAllowed(artifact) && (
                <p>
                  Inline preview unavailable for this file type. Download the
                  original for inspection.
                </p>
              )}
            </>
          )}
          <p role="status">{message}</p>
          {preview?.key === key && (
            <pre
              className="support-preview"
              tabIndex={0}
              aria-label="Verified original text"
            >
              {preview.text}
            </pre>
          )}
        </section>
      </div>
    </aside>
  );
}
