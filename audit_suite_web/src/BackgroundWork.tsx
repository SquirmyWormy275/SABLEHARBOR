import { QueuedConsultation } from "./ConsultationProvenance";
import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "./api";
import type { Engagement } from "./api";
import { jobAction, jobsPath } from "./backgroundWork";
import type { BackgroundJob, BackgroundInput } from "./backgroundWork";

export function BackgroundWork(props: {
  engagement: Engagement;
  viewerId: string;
  onInspect: (kind?: string) => void;
  onCompleted: () => void;
}) {
  const context = JSON.stringify([
    props.viewerId,
    props.engagement.id,
    props.engagement.permissions,
    props.engagement.scope,
    props.engagement.company_source_binding,
    props.engagement.evidence_acquisition,
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
  onInspect: (kind?: string) => void;
  onCompleted: () => void;
}) {
  const [jobs, setJobs] = useState<BackgroundJob[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [inspected, setInspected] = useState<Record<string, number>>({});
  const [inputs, setInputs] = useState<Record<string, BackgroundInput>>({});
  const alive = useRef(true);
  const section = useRef<HTMLElement>(null);
  const active = useRef(false);
  const refresh = useRef<() => void>(() => {});
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
    let running = false;
    let generation = 0, refreshPending = false;
    const panel = section.current?.closest("details.background-work-panel") as HTMLDetailsElement | null;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      if (stopped || running) return;
      running = true;
      const observedGeneration = generation;
      try {
        const data = await request<{ jobs: BackgroundJob[] }>(
          jobsPath(engagement.id),
        );
        if (stopped || observedGeneration !== generation) return;
        setJobs(data.jobs);
        active.current = data.jobs.some((job) => job.status === "PENDING" || job.status === "RUNNING");
        setError("");
        for (const job of data.jobs)
          if (job.status === "COMPLETED" && !completed.current.has(job.id)) {
            completed.current.add(job.id);
            callback.current();
          }
      } catch (e) {
        if (stopped || observedGeneration !== generation) return;
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
      } finally {
        running = false;
        if (!stopped && refreshPending) {
          refreshPending = false;
          void poll();
        } else if (!stopped && (!panel || panel.open || active.current)) timer = setTimeout(poll, 2500);
      }
    };
    const toggle = () => {
      clearTimeout(timer);
      if (panel?.open) void poll();
      else if (active.current && !running) timer = setTimeout(poll, 2500);
    };
    refresh.current = () => {
      generation++;
      clearTimeout(timer);
      if (running) refreshPending = true;
      else void poll();
    };
    panel?.addEventListener("toggle", toggle);
    void poll();
    return () => {
      stopped = true;
      alive.current = false;
      clearTimeout(timer);
      panel?.removeEventListener("toggle", toggle);
      refresh.current = () => {};
    };
  }, [engagement.id, allowed]);
  if (!allowed) return null;
  async function inspectInput(job: BackgroundJob) {
    setError("");
    try {
      const input = await request<BackgroundInput>(
        `${jobsPath(engagement.id)}/${encodeURIComponent(job.id)}/input`,
      );
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
      if (alive.current) {
        active.current = [value, ...jobs.filter((job) => job.id !== value.id)].some(
          (job) => job.status === "PENDING" || job.status === "RUNNING",
        );
        setJobs((old) => old.map((j) => (j.id === value.id ? value : j)));
        refresh.current();
      }
    } catch (e) {
      if (alive.current)
        setError(e instanceof Error ? e.message : "Action unavailable");
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <section ref={section} aria-label="Background work">
      <h2>Background work</h2>
      <p>
        Company responses and source census collections continue while you
        navigate. This list belongs to your current engagement and account.
        Reloading does not submit another message.
      </p>
      {error && <p role="alert">{error}</p>}
      {!jobs.length && <p>No background work.</p>}
      <ul>
        {jobs.map((job) => (
          <li key={job.id}>
            <strong>{job.status}</strong> ·{" "}
            {job.kind === "company.census.collect"
              ? "Source-record census"
              : "Meeting reply"}{" "}
            · {job.id} · Original engagement revision {job.expected_revision} ·
            Attempts {job.attempts}
            {job.result_revision !== null && (
              <span> · Result revision {job.result_revision}</span>
            )}
            {job.error_message && <p>{job.error_message}</p>}
            <button onClick={() => onInspect(job.kind)}>
              {job.kind === "company.census.collect"
                ? "Inspect populations and current engagement"
                : "Inspect meetings and current engagement"}
            </button>
            <button onClick={() => void inspectInput(job)}>
              {job.kind === "company.census.collect"
                ? "Inspect queued census query"
                : "Inspect queued question"}
            </button>
            {inputs[job.id] && (
              <div>
                {inputs[job.id].kind === "company.census.collect" ? (
                  <div>
                    <p>
                      Source-record census · System{" "}
                      {inputs[job.id].payload.system_id} · Request{" "}
                      {inputs[job.id].payload.request_id}
                    </p>
                    <p>
                      Command {inputs[job.id].command_id} · Original revision{" "}
                      {inputs[job.id].expected_revision}
                    </p>
                    <pre>
                      {JSON.stringify(inputs[job.id].payload.query, null, 2)}
                    </pre>
                    <p>
                      This query is the original queued input; retries do not
                      replace it with current form values.
                    </p>
                  </div>
                ) : (
                  <>
                    <p>
                      Meeting {inputs[job.id].payload.meeting_id} · Command{" "}
                      {inputs[job.id].command_id} · Original revision{" "}
                      {inputs[job.id].expected_revision}
                    </p>
                    <blockquote>{inputs[job.id].payload.content}</blockquote>
                    {inputs[job.id].payload.consultation && (
                      <QueuedConsultation
                        value={inputs[job.id].payload.consultation!}
                      />
                    )}
                    {inputs[job.id].payload.source_records?.length ? (
                      <>
                        <p>Explicit source pins retained with this question:</p>
                        <ul>
                          {inputs[job.id].payload.source_records!.map((pin) => (
                            <li key={`${pin.system_id}:${pin.record_id}`}>
                              {pin.system_id} / {pin.record_id} · Version{" "}
                              {pin.version} · SHA256 <code>{pin.sha256}</code>
                            </li>
                          ))}
                        </ul>
                      </>
                    ) : (
                      <p>
                        {inputs[job.id].payload.consultation
                          ? "No original source records were selected for this consultation."
                          : "No explicit source pins; the original command uses automatic bounded source sampling."}
                      </p>
                    )}
                  </>
                )}
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
                changing its base revision; execution may repeat.
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
