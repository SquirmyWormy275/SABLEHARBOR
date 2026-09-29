import { useEffect, useRef, useState } from "react";
import { ApiError, request, type Engagement } from "./api";
import {
  acceptedTaskGap,
  canRecordTaskGap,
  currentTaskGaps,
  gapCauses,
  gapDispositions,
  retestKey,
  taskGapCommand,
  taskGapRows,
  taskEligibleForGap,
  taskRetests,
  type TaskGapCommand,
  type TaskGapDraft,
  type TaskGapRow,
} from "./taskGap";

type Props = {
  engagement: Engagement;
  taskId: string;
  viewerId: string;
  onState: (state: Engagement) => void;
  onClose: () => void;
};
const initialDraft = (viewerId: string): TaskGapDraft => ({
  cause: "MISSING_OPERATION",
  owner_id: viewerId,
  disposition: "OPEN",
  narrative: "",
  artifact_id: "",
  retest_key: "",
  predecessor_id: "",
});

function GapReference({ row }: { row: TaskGapRow }) {
  const artifact = row.artifact_pin;
  const retest = row.retest;
  return (
    <li>
      <strong>{row.id}</strong> · {gapCauses[row.cause] ?? row.cause} ·{" "}
      {gapDispositions[row.disposition] ?? row.disposition}
      <p>{row.narrative}</p>
      <small>
        Assigned owner {row.owner_id} · Recorded by {row.actor} · {row.recorded_at}
        {row.revision != null ? ` · revision ${row.revision}` : ""}
      </small>
      <p>
        Retained artifact:{" "}
        {artifact ? (
          <>
            <code>{artifact.id}</code> · SHA-256 <code>{artifact.sha256}</code>
          </>
        ) : (
          "none linked"
        )}
      </p>
      <p>
        Retest:{" "}
        {retest ? (
          <>
            <code>{retest.workpaper_id}</code> version {retest.version}
            {retest.version_sha256 ? (
              <>
                {" "}
                · version SHA-256 <code>{retest.version_sha256}</code>
              </>
            ) : null}
          </>
        ) : (
          "none linked"
        )}
      </p>
      {row.predecessor_id && (
        <p>
          Follows gap <code>{row.predecessor_id}</code>
          {row.predecessor_sha256 ? (
            <>
              {" "}
              · SHA-256 <code>{row.predecessor_sha256}</code>
            </>
          ) : null}
        </p>
      )}
      <small>
        Author-recorded observation; no audit conclusion follows automatically.
      </small>
    </li>
  );
}

export function TaskGapPreview({ command }: { command: TaskGapCommand }) {
  const payload = command.payload;
  return (
    <div className="panel" aria-label="Task gap preview">
      <h4>Preview before recording</h4>
      <p>
        {gapCauses[payload.cause]} · {gapDispositions[payload.disposition]} ·
        assigned owner {payload.owner_id}
      </p>
      <p>{payload.narrative}</p>
      <p>
        Artifact:{" "}
        {payload.artifact_pin ? (
          <>
            <code>{payload.artifact_pin.id}</code> · SHA-256{" "}
            <code>{payload.artifact_pin.sha256}</code>
          </>
        ) : (
          "none linked"
        )}
      </p>
      <p>
        Retest:{" "}
        {payload.retest
          ? `${payload.retest.workpaper_id} version ${payload.retest.version}`
          : "none linked"}
      </p>
      <p>Predecessor: {payload.predecessor_id ?? "none"}</p>
      <small>
        Author-recorded gap only. No status, conclusion, or retest result is
        inferred.
      </small>
    </div>
  );
}

export function TaskGapPanel({
  engagement: e,
  taskId,
  viewerId,
  onState,
  onClose,
}: Props) {
  const [draft, setDraft] = useState(() => initialDraft(viewerId));
  const [preview, setPreview] = useState<TaskGapCommand | null>(null);
  const [pending, setPending] = useState<TaskGapCommand | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const epoch = useRef(0);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    epoch.current++;
    heading.current?.focus();
    return () => {
      epoch.current++;
    };
  }, []);
  const task = e.tasks.find((row) => row.id === taskId);
  if (!task) return null;
  const history = taskGapRows(e, taskId);
  const current = currentTaskGaps(history);
  const artifacts = e.artifacts.filter(
    (a) =>
      a.status === "AVAILABLE" &&
      typeof a.sha256 === "string" &&
      /^[a-f0-9]{64}$/.test(a.sha256),
  );
  const retests = taskRetests(e, taskId);
  const editable = canRecordTaskGap(e) && taskEligibleForGap(task);
  function change(patch: Partial<TaskGapDraft>) {
    setDraft((old) => ({ ...old, ...patch }));
    setPreview(null);
    setError("");
  }
  function prepare() {
    try {
      setPreview(
        taskGapCommand(e, viewerId, taskId, draft, crypto.randomUUID()),
      );
      setError("");
    } catch (x) {
      setPreview(null);
      setError((x as Error).message);
    }
  }
  async function submit(exact: TaskGapCommand) {
    const n = ++epoch.current;
    setBusy(true);
    setError("");
    setPending(exact);
    try {
      const state = await request<Engagement>(
        `/api/engagements/${encodeURIComponent(e.id)}/commands`,
        "POST",
        exact,
      );
      if (n !== epoch.current) return;
      if (!acceptedTaskGap(e, state, viewerId, exact))
        throw Error(
          "The command response did not contain this exact gap. Inspect history or retry the same command.",
        );
      setPending(null);
      setPreview(null);
      setDraft(initialDraft(viewerId));
      onState(state);
    } catch (x) {
      if (n !== epoch.current) return;
      setError((x as Error).message);
      if (x instanceof ApiError && [401, 403, 409].includes(x.status)) {
        setPending(null);
        setPreview(null);
      }
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  return (
    <section className="panel" aria-label={`Task gap record for ${taskId}`}>
      <div className="actions">
        <h3 tabIndex={-1} ref={heading}>Task gap · {taskId}</h3>
        <button type="button" onClick={onClose}>
          Close gap panel
        </button>
      </div>
      <p>{String(task.title ?? "Procedure")}</p>
      <p>
        Record a specific obstacle and its source or follow-up. This does not
        change the task status, test conclusion, finding, or assurance result.
      </p>
      <h4>Current gaps</h4>
      {current.length ? (
        <ul>
          {current.map((row) => (
            <GapReference key={row.id} row={row} />
          ))}
        </ul>
      ) : (
        <p>No recorded gap for this task.</p>
      )}
      {history.length > current.length && (
        <details>
          <summary>
            Earlier gap history ({history.length - current.length})
          </summary>
          <ul>
            {history
              .filter((row) => !current.some((c) => c.id === row.id))
              .map((row) => (
                <GapReference key={row.id} row={row} />
              ))}
          </ul>
        </details>
      )}
      {!editable ? (
        <p>
          Gap recording requires an active, applicable task and an auditor role.
          History remains read-only here.
        </p>
      ) : (
        <form
          onSubmit={(ev) => {
            ev.preventDefault();
            if (preview && !pending) void submit(preview);
          }}
        >
          <fieldset disabled={busy || !!pending}>
            <legend>Record a task gap</legend>
            <label>
              Cause
              <select
                value={draft.cause}
                onChange={(ev) =>
                  change({ cause: ev.target.value as TaskGapDraft["cause"] })
                }
              >
                {Object.entries(gapCauses).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <p>Assigned gap owner: {viewerId} (your current auditor identity)</p>
            <label>
              Disposition
              <select
                value={draft.disposition}
                onChange={(ev) =>
                  change({
                    disposition: ev.target.value as TaskGapDraft["disposition"],
                    retest_key: "",
                  })
                }
              >
                {Object.entries(gapDispositions).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Observed gap and next step
              <textarea
                value={draft.narrative}
                onChange={(ev) => change({ narrative: ev.target.value })}
                minLength={20}
                maxLength={4000}
                required
              />
            </label>
            <label>
              Retained artifact (optional)
              <select
                value={draft.artifact_id}
                onChange={(ev) => change({ artifact_id: ev.target.value })}
              >
                <option value="">No retained artifact linked</option>
                {artifacts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.id} · {String(a.title ?? a.name ?? "retained original")}{" "}
                    · {String(a.sha256).slice(0, 12)}…
                  </option>
                ))}
              </select>
            </label>
            {draft.disposition === "RETEST_LINKED" && (
              <label>
                Exact task-associated retest workpaper version
                <select
                  value={draft.retest_key}
                  onChange={(ev) => change({ retest_key: ev.target.value })}
                  required
                >
                  <option value="">Choose a workpaper version</option>
                  {retests.map((r) => (
                    <option key={retestKey(r)} value={retestKey(r)}>
                      {r.workpaper_id} · version {r.version}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Follow-up to current gap (optional)
              <select
                value={draft.predecessor_id}
                onChange={(ev) => change({ predecessor_id: ev.target.value })}
              >
                <option value="">New gap, no predecessor</option>
                {current.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.id} · {gapCauses[row.cause]}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" onClick={prepare}>
              Preview exact record
            </button>
          </fieldset>
          {preview && !pending && (
            <>
              <TaskGapPreview command={preview} />
              <button type="submit">Record gap</button>
            </>
          )}
          {pending && !busy && (
            <button type="button" onClick={() => void submit(pending)}>
              Retry exact command
            </button>
          )}
          {busy && <p>Recording gap…</p>}
          {error && <p role="alert">{error}</p>}
        </form>
      )}
    </section>
  );
}
