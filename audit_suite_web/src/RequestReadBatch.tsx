import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "./api";
import type { Engagement } from "./api";
import {
  acceptedReadResponse,
  matchingRequests,
  planRequestReads,
  requestReadAuthority,
} from "./requestReadBatch";
import type { ReadEnvelope, ReadOutcome, ReadPlan } from "./requestReadBatch";
type Props = {
  engagement: Engagement;
  viewerId: string;
  onState: (state: Engagement) => void;
};
export function RequestReadBatch(props: Props) {
  return (
    <details className="panel">
      <summary>Mark received requests read</summary>
      <Batch
        key={requestReadAuthority(props.engagement, props.viewerId)}
        {...props}
      />
    </details>
  );
}
function Batch({ engagement: e, viewerId, onState }: Props) {
  const [query, setQuery] = useState(""),
    [selected, setSelected] = useState<string[]>([]),
    [mode, setMode] = useState<ReadPlan["mode"]>("SELECTED"),
    [plan, setPlan] = useState<ReadPlan | null>(null),
    [outcomes, setOutcomes] = useState<ReadOutcome[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [pending, setPending] = useState<ReadEnvelope | null>(null),
    [stopped, setStopped] = useState(false);
  const live = useRef(true),
    latest = useRef(e),
    running = useRef(false),
    halt = useRef(false),
    accepted = useRef(new Set<number>()),
    working = useRef(e),
    activePlan = useRef<ReadPlan | null>(null),
    result = useRef<ReadOutcome[]>([]),
    basis = useRef(requestReadAuthority(e, viewerId));
  latest.current = e;
  useEffect(() => {
    live.current = true;
    return () => {
      live.current = false;
      halt.current = true;
    };
  }, []);
  useEffect(() => {
    if (running.current && !accepted.current.has(e.revision)) {
      halt.current = true;
      setStopped(true);
      setError(
        "Workspace revision changed outside this batch. Remaining items were not attempted.",
      );
    }
  }, [e.revision]);
  const allowed =
    e.phase === "ACTIVE" &&
    e.permissions?.some((p) => p === "learn" || p === "instruct");
  function update(id: string, status: ReadOutcome["status"], message?: string) {
    result.current = result.current.map((row) =>
      row.id === id ? { id, status, message } : row,
    );
    if (live.current) setOutcomes([...result.current]);
  }
  async function execute(command: ReadEnvelope): Promise<boolean> {
    try {
      const value = await request<Engagement>(
        `/api/engagements/${encodeURIComponent(e.id)}/commands`,
        "POST",
        command,
      );
      if (!live.current) return false;
      if (
        !acceptedReadResponse(working.current, command, value) ||
        requestReadAuthority(value, viewerId) !== basis.current
      ) {
        update(
          command.payload.request_id,
          "AMBIGUOUS",
          "Unexpected result; inspect the workspace before any further action.",
        );
        setPending(command);
        setError(
          "The command result could not be safely matched. Exact retry or inspect the workspace.",
        );
        halt.current = true;
        return false;
      }
      update(command.payload.request_id, "SUCCEEDED");
      accepted.current.add(value.revision);
      working.current = value;
      onState(value);
      setPending(null);
      return !halt.current;
    } catch (x) {
      if (!live.current) return false;
      const ambiguous =
        !(x instanceof ApiError) || x.status >= 500 || x.status === 200;
      update(
        command.payload.request_id,
        ambiguous ? "AMBIGUOUS" : "FAILED",
        (x as Error).message,
      );
      setError((x as Error).message);
      setPending(ambiguous ? command : null);
      return false;
    }
  }
  async function run(retry?: ReadEnvelope) {
    if (
      !activePlan.current ||
      !allowed ||
      requestReadAuthority(latest.current, viewerId) !== basis.current
    )
      return;
    if (
      retry &&
      (!accepted.current.has(latest.current.revision) || halt.current)
    ) {
      setError(
        "Workspace changed. Inspect the command history; this batch cannot continue.",
      );
      return;
    }
    setBusy(true);
    setError("");
    running.current = true;
    try {
      if (retry) {
        const okay = await execute(retry);
        if (!okay) return;
        setStopped(true);
        setError(
          "Exact retry confirmed. Remaining items are not attempted; create a new preview to continue.",
        );
        return;
      }
      for (const id of activePlan.current.eligible) {
        if (
          halt.current ||
          !live.current ||
          !accepted.current.has(latest.current.revision)
        )
          break;
        const command: ReadEnvelope = {
          command_id: crypto.randomUUID(),
          expected_revision: working.current.revision,
          kind: "pbc.read",
          payload: { request_id: id },
        };
        if (!(await execute(command))) break;
      }
    } finally {
      running.current = false;
      if (live.current) {
        setBusy(false);
        setStopped(true);
      }
    }
  }
  function confirm() {
    if (!plan || plan.overLimit || plan.revision !== e.revision || !allowed)
      return;
    activePlan.current = structuredClone(plan);
    working.current = e;
    accepted.current = new Set([e.revision]);
    halt.current = false;
    basis.current = requestReadAuthority(e, viewerId);
    result.current = plan.eligible.map((id) => ({
      id,
      status: "NOT_ATTEMPTED",
    }));
    setOutcomes(result.current);
    setStopped(false);
    void run();
  }
  const [previewChoice, setPreviewChoice] = useState("");
  const choice = JSON.stringify([query, mode, selected]);
  const rows = matchingRequests(e, query);
  return (
    <div>
      <p>
        Marks the unread notification only. It does not assess evidence, accept
        a response or complete testing.
      </p>
      {!allowed && (
        <p role="status">
          An active engagement and preparer or instructor permission are
          required.
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      <fieldset disabled={busy || Boolean(pending)}>
        <legend>Choose requests</legend>
        <label>
          Filter received requests
          <input
            aria-label="Batch request filter"
            value={query}
            onChange={(ev) => setQuery(ev.target.value)}
          />
        </label>
        <p>{rows.length} matched; showing up to 50 for individual selection.</p>
        <ul>
          {rows.slice(0, 50).map((row) => (
            <li key={row.id}>
              <label>
                <input
                  type="checkbox"
                  aria-label={`Select request ${row.id}`}
                  checked={selected.includes(row.id)}
                  onChange={(ev) =>
                    setSelected((ids) =>
                      ev.target.checked
                        ? [...ids, row.id]
                        : ids.filter((id) => id !== row.id),
                    )
                  }
                />
                {row.id} · {String(row.title ?? "")} ·{" "}
                {row.unread === true ? "Unread" : "No unread marker"}
              </label>
            </li>
          ))}
        </ul>
        <label>
          <input
            type="radio"
            name="read-batch-mode"
            checked={mode === "SELECTED"}
            onChange={() => setMode("SELECTED")}
          />
          Selected rows
        </label>
        <label>
          <input
            type="radio"
            name="read-batch-mode"
            checked={mode === "FILTERED"}
            onChange={() => setMode("FILTERED")}
          />
          All currently filtered requests
        </label>
        <button
          type="button"
          onClick={() => {
            setPlan(planRequestReads(e, query, selected, mode));
            setPreviewChoice(choice);
            setOutcomes([]);
            setStopped(false);
            setError("");
          }}
        >
          Preview read changes
        </button>
      </fieldset>
      {plan && (
        <section aria-label="Request read batch preview">
          <p>
            Preview mode:{" "}
            {plan.mode === "FILTERED"
              ? "All currently filtered snapshot"
              : "Explicit selected rows"}
            . IDs below are the frozen preview.
          </p>
          {previewChoice !== choice && (
            <p>
              Selection or filter changed. Make a new preview before confirming.
            </p>
          )}
          <p>
            Selected: {plan.selected} · Matched: {plan.matched} · Eligible:{" "}
            {plan.eligible.length} · Excluded: {plan.excluded.length}
          </p>
          <p>Exact eligible IDs: {plan.eligible.join(", ") || "None"}</p>
          <ul>
            {plan.excluded.map((row) => (
              <li key={row.id}>
                {row.id}: {row.reason}
              </li>
            ))}
          </ul>
          {plan.overLimit && (
            <p role="alert">
              Choose at most 20 requests. Nothing will be truncated.
            </p>
          )}
          {plan.revision !== e.revision && !outcomes.length && (
            <p>Preview is outdated. Make a new preview.</p>
          )}
          <button
            type="button"
            disabled={
              busy ||
              stopped ||
              Boolean(pending) ||
              !allowed ||
              !plan.eligible.length ||
              plan.overLimit ||
              plan.revision !== e.revision ||
              previewChoice !== choice
            }
            onClick={confirm}
          >
            Confirm mark {plan.eligible.length} requests read
          </button>
        </section>
      )}
      {pending && (
        <div>
          <p>
            The last command may have been accepted. Inspect its ordinary
            command history before choosing an exact retry; no following item
            will run automatically.
          </p>
          <code>{pending.command_id}</code>
          <button
            type="button"
            disabled={busy || halt.current || !accepted.current.has(e.revision)}
            onClick={() => void run(pending)}
          >
            Retry exact read command
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => {
              setPending(null);
              halt.current = true;
              setStopped(true);
              setError(
                "Local retry cleared after inspection. Existing command history is unchanged.",
              );
            }}
          >
            Clear local retry after inspection
          </button>
        </div>
      )}
      {outcomes.length > 0 && (
        <section aria-label="Request read batch results">
          <p>
            {outcomes.filter((r) => r.status === "SUCCEEDED").length} succeeded;{" "}
            {outcomes.filter((r) => r.status === "FAILED").length} failed;{" "}
            {outcomes.filter((r) => r.status === "AMBIGUOUS").length}{" "}
            unconfirmed;{" "}
            {outcomes.filter((r) => r.status === "NOT_ATTEMPTED").length} not
            attempted.
          </p>
          <ul>
            {outcomes.map((row) => (
              <li key={row.id}>
                {row.id}: {row.status}
                {row.message ? ` · ${row.message}` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
