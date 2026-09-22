import { useEffect, useRef, useState } from "react";
import { request, type Engagement, type Row } from "./api";
import type { ContextLink } from "./investigationContext";
import { savedViewContext } from "./savedViews";
import {
  checkpointPath,
  checkpointRecord,
  verifyCheckpoint,
  type VisitCheckpoint as Checkpoint,
} from "./visitCheckpoint";

type Props = {
  engagement: Engagement;
  viewerId: string;
  onPreview: (reference: ContextLink, row: Row) => void;
};
export function VisitCheckpoint(props: Props) {
  if (
    !props.engagement.permissions?.some((p) =>
      ["learn", "review", "instruct"].includes(p),
    )
  )
    return null;
  return (
    <details className="panel">
      <summary>Changes since my checkpoint</summary>
      <CheckpointPanel
        key={savedViewContext(props.engagement, props.viewerId)}
        {...props}
      />
    </details>
  );
}
function CheckpointPanel({ engagement: e, onPreview }: Props) {
  const [page, setPage] = useState(0);
  const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(null);
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [pending, setPending] = useState<{
    command_id: string;
    expected_version: number;
    expected_engagement_revision: number;
  } | null>(null);
  const active = useRef(true),
    sequence = useRef(0);
  const base = checkpointPath(e.id);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      ++sequence.current;
    };
  }, []);
  async function load() {
    const token = ++sequence.current;
    setBusy(true);
    setError("");
    setCheckpoint(null);
    setPage(0);
    try {
      const result = verifyCheckpoint(await request<Checkpoint>(base), e);
      if (active.current && token === sequence.current) setCheckpoint(result);
    } catch (ex) {
      if (active.current && token === sequence.current)
        setError((ex as Error).message);
    } finally {
      if (active.current && token === sequence.current) setBusy(false);
    }
  }
  async function compare() {
    if (!checkpoint) return;
    const token = ++sequence.current;
    setBusy(true);
    setError("");
    setPage(0);
    setCheckpoint({ ...checkpoint, changes: undefined, counts: undefined });
    try {
      const result = verifyCheckpoint(
        await request<Checkpoint>(base + "/compare", "POST", {
          expected_version: checkpoint.version,
          expected_engagement_revision: e.revision,
        }),
        e,
        true,
      );
      if (result.version !== checkpoint.version)
        throw Error("Checkpoint changed. Refresh before comparing.");
      if (active.current && token === sequence.current) setCheckpoint(result);
    } catch (ex) {
      if (active.current && token === sequence.current)
        setError((ex as Error).message);
    } finally {
      if (active.current && token === sequence.current) setBusy(false);
    }
  }
  async function capture() {
    if (!checkpoint) return;
    const body = pending ?? {
      command_id: crypto.randomUUID(),
      expected_version: checkpoint.version,
      expected_engagement_revision: e.revision,
    };
    setPending(body);
    setBusy(true);
    setError("");
    const token = ++sequence.current;
    try {
      const result = verifyCheckpoint(
        await request<Checkpoint>(base, "POST", body),
        e,
      );
      if (
        result.status !== "CURRENT" ||
        result.version !== body.expected_version + 1
      )
        throw Error("Checkpoint changed. Refresh to inspect the saved result.");
      if (active.current && token === sequence.current) {
        setCheckpoint(result);
        setPending(null);
        setPage(0);
      }
    } catch (ex) {
      if (active.current && token === sequence.current)
        setError((ex as Error).message);
    } finally {
      if (active.current && token === sequence.current) setBusy(false);
    }
  }
  return (
    <section aria-label="Personal change checkpoint">
      <p>
        Explicitly save a personal comparison point for controls, procedures,
        evidence originals, populations, selections and workpaper versions. This
        does not mark anything read, inspected, tested or accepted.
      </p>
      <button disabled={busy || !!pending} onClick={() => void load()}>
        Refresh my checkpoint
      </button>
      {error && <p role="alert">{error}</p>}
      {busy && <p role="status">Checking the current authorized workspace…</p>}
      {checkpoint && (
        <>
          <p>
            {checkpoint.version
              ? `Saved checkpoint ${checkpoint.version} · workspace revision ${checkpoint.checkpoint_engagement_revision} · ${checkpoint.saved_at}`
              : "No checkpoint saved yet."}
          </p>
          {checkpoint.status !== "CURRENT" &&
            checkpoint.status !== "NO_CHECKPOINT" && (
              <p role="status">
                Comparison unavailable under the current access, scope or source
                context. Details and counts are withheld. You can explicitly
                save a new checkpoint.
              </p>
            )}
          <button
            disabled={busy || !!pending || checkpoint.status !== "CURRENT"}
            onClick={() => void compare()}
          >
            Compare with current records
          </button>{" "}
          <button disabled={busy} onClick={() => void capture()}>
            {pending
              ? "Retry exact checkpoint save"
              : checkpoint.version
                ? "Replace my checkpoint with current records"
                : "Save current checkpoint"}
          </button>
          {pending && !busy && (
            <p>
              The save result is unresolved. Retry the same request, or{" "}
              <button
                onClick={() => {
                  setPending(null);
                  void load();
                }}
              >
                reload before starting another save
              </button>
              . A previous save may already have completed.
            </p>
          )}
          {checkpoint.counts && (
            <>
              <p>
                {checkpoint.counts.added} added · {checkpoint.counts.changed}{" "}
                changed · {checkpoint.counts.unchanged} unchanged supported
                record versions. Differences do not establish an exception or a
                required conclusion.
              </p>
              {checkpoint.changes?.length === 0 && (
                <p>No differences among these supported records.</p>
              )}
              <ul>
                {checkpoint.changes
                  ?.slice(page * 100, (page + 1) * 100)
                  .map((change) => {
                    const ref = change.current.reference,
                row = checkpointRecord(e, ref);
                    return (
                      <li key={JSON.stringify([ref.kind, ref.id, ref.version])}>
                        {change.change === "ADDED" ? "Added" : "Changed"}:{" "}
                        {ref.kind} {ref.id}
                        {ref.version !== null
                          ? ` · version ${ref.version}`
                          : ""}{" "}
                        <button
                          disabled={!row || busy}
                          onClick={() => {
                            if (row) onPreview(ref, row);
                          }}
                        >
                          Inspect {ref.id}
                        </button>
                        <details>
                          <summary>Exact comparison references</summary>
                          <pre>
                            {JSON.stringify(
                              { prior: change.prior, current: change.current },
                              null,
                              2,
                            )}
                          </pre>
                        </details>
                      </li>
                    );
                  })}
              </ul>
              {(checkpoint.changes?.length ?? 0) > 100 && (
                <div>
                  <p>
                    Page {page + 1} of{" "}
                    {Math.ceil(checkpoint.changes!.length / 100)} ·{" "}
                    {checkpoint.changes!.length} differences total.
                  </p>
                  <button
                    disabled={page === 0}
                    onClick={() => setPage(page - 1)}
                  >
                    Previous changes
                  </button>
                  <button
                    disabled={(page + 1) * 100 >= checkpoint.changes!.length}
                    onClick={() => setPage(page + 1)}
                  >
                    Next changes
                  </button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
