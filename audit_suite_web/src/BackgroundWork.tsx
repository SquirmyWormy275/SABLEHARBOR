import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "./api";
import type { Engagement } from "./api";
import { jobAction, jobsPath } from "./backgroundWork";
import type { BackgroundJob } from "./backgroundWork";

export function BackgroundWork(props: {
  engagement: Engagement;
  viewerId: string;
  onInspect: () => void;
  onCompleted: () => void;
}) {
  const context = JSON.stringify([
    props.viewerId,
    props.engagement.id,
    props.engagement.permissions,
    props.engagement.scope,
  ]);
  return <WorkList key={context} {...props} />;
}
function WorkList({
  engagement,
  onInspect,
  onCompleted,
}: {
  engagement: Engagement;
  viewerId: string;
  onInspect: () => void;
  onCompleted: () => void;
}) {
  const [jobs, setJobs] = useState<BackgroundJob[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [inspected, setInspected] = useState<Record<string, number>>({});
  const [inputs, setInputs] = useState<
    Record<
      string,
      {
        command_id: string;
        expected_revision: number;
        payload: { meeting_id: string; content: string };
      }
    >
  >({});
  const alive = useRef(true);
  const completed = useRef(new Set<string>());
  const callback = useRef(onCompleted);
  callback.current = onCompleted;
  const allowed = engagement.permissions?.some(
    (p) => p === "learn" || p === "instruct",
  );
  useEffect(() => {
    alive.current = true;
    if (!allowed)
      return () => {
        alive.current = false;
      };
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const data = await request<{ jobs: BackgroundJob[] }>(
          jobsPath(engagement.id),
        );
        if (stopped) return;
        setJobs(data.jobs);
        setError("");
        for (const job of data.jobs)
          if (job.status === "COMPLETED" && !completed.current.has(job.id)) {
            completed.current.add(job.id);
            callback.current();
          }
      } catch (e) {
        if (
          !stopped &&
          e instanceof ApiError &&
          [401, 403, 404].includes(e.status)
        ) {
          setJobs([]);
          setInputs({});
          setInspected({});
        }
        if (!stopped)
          setError(
            e instanceof Error ? e.message : "Background status unavailable",
          );
      }
      if (!stopped) timer = setTimeout(poll, 2500);
    };
    void poll();
    return () => {
      stopped = true;
      alive.current = false;
      clearTimeout(timer);
    };
  }, [engagement.id, allowed]);
  if (!allowed) return null;
  async function inspectInput(job: BackgroundJob) {
    setError("");
    try {
      const input = await request<{
        command_id: string;
        expected_revision: number;
        payload: { meeting_id: string; content: string };
      }>(`${jobsPath(engagement.id)}/${encodeURIComponent(job.id)}/input`);
      if (alive.current) setInputs((old) => ({ ...old, [job.id]: input }));
    } catch (e) {
      if (alive.current)
        setError(
          e instanceof Error ? e.message : "Queued question unavailable",
        );
    }
  }
  async function act(job: BackgroundJob) {
    const action = jobAction(job);
    if (!action) return;
    setBusy(true);
    setError("");
    try {
      const value = await request<BackgroundJob>(
        `${jobsPath(engagement.id)}/${encodeURIComponent(job.id)}/${action}`,
        "POST",
        action === "retry" ? { observed_job_revision: job.job_revision } : {},
      );
      if (alive.current)
        setJobs((old) => old.map((j) => (j.id === value.id ? value : j)));
    } catch (e) {
      if (alive.current)
        setError(e instanceof Error ? e.message : "Action unavailable");
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <section aria-label="Background work">
      <h2>Background work</h2>
      <p>
        Meeting responses continue while you navigate. This list belongs to your
        current engagement and account. Reloading does not submit another
        message.
      </p>
      {error && <p role="alert">{error}</p>}
      {!jobs.length && <p>No background meeting work.</p>}
      <ul>
        {jobs.map((job) => (
          <li key={job.id}>
            <strong>{job.status}</strong> · {job.id} · Original engagement
            revision {job.expected_revision} · Attempts {job.attempts}
            {job.result_revision !== null && (
              <span> · Result revision {job.result_revision}</span>
            )}
            {job.error_message && <p>{job.error_message}</p>}
            <button onClick={onInspect}>
              Inspect meetings and current engagement
            </button>
            <button onClick={() => void inspectInput(job)}>
              Inspect queued question
            </button>
            {inputs[job.id] && (
              <div>
                <p>
                  Meeting {inputs[job.id].payload.meeting_id} · Command{" "}
                  {inputs[job.id].command_id} · Original revision{" "}
                  {inputs[job.id].expected_revision}
                </p>
                <blockquote>{inputs[job.id].payload.content}</blockquote>
              </div>
            )}
            {jobAction(job) === "retry" && (
              <label>
                <input
                  type="checkbox"
                  disabled={!inputs[job.id]}
                  checked={inspected[job.id] === job.job_revision}
                  onChange={(e) =>
                    setInspected((old) => ({
                      ...old,
                      [job.id]: e.target.checked ? job.job_revision : -1,
                    }))
                  }
                />
                I inspected the engagement. Retry the original command without
                changing its base revision; model computation may repeat.
              </label>
            )}
            {jobAction(job) && (
              <button
                disabled={
                  busy ||
                  (jobAction(job) === "retry" &&
                    (!inputs[job.id] || inspected[job.id] !== job.job_revision))
                }
                onClick={() => void act(job)}
              >
                {jobAction(job) === "start"
                  ? "Start pending work"
                  : "Retry original command"}
              </button>
            )}
            {job.status === "CONFLICTED" && (
              <p>
                This command cannot be retried or rebased. Inspect the current
                engagement before composing a new message.
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
