import { useEffect, useRef, useState } from "react";
import { ApiError, request, type Engagement, type Row } from "./api";
type Pin = { kind: string; id: string; version: number | null; sha256: string };
type Candidate = {
  id: string;
  sha256: string;
  code: string;
  title: string;
  reason: string;
  context_ref: Pin;
  references: {
    kind: string;
    id: string;
    status: string;
    reference: Pin | null;
  }[];
  decision?: { action: string; rationale: string };
};
type Status = {
  engagement_id: string;
  current_engagement_revision: number;
  version: number;
  policy_version: number;
  status: string;
  opted_in: boolean;
  policy_allowed: boolean;
  personal_content_visible: boolean;
  contexts: { reference: Pin; title: string }[];
  candidates?: Candidate[];
};
type Props = {
  engagement: Engagement;
  viewerId: string;
  busy: boolean;
  onCommand: (
    kind: string,
    payload: Record<string, unknown>,
  ) => Promise<Engagement | undefined>;
  onPreview: (kind: string, row: Row, pin: Pin) => void;
};
export function WorkGuidance(props: Props) {
  const e = props.engagement;
  return (
    <Guidance
      key={JSON.stringify([
        props.viewerId,
        e.id,
        e.revision,
        e.scope,
        e.permissions,
        e.company_source_binding,
        e.evidence_acquisition,
        e.work_guidance_policy,
      ])}
      {...props}
    />
  );
}
function Guidance({
  engagement: e,
  busy: parentBusy,
  onCommand,
  onPreview,
}: Props) {
  const [state, setState] = useState<Status | null>(null),
    [context, setContext] = useState(""),
    [rationale, setRationale] = useState(""),
    [policyReason, setPolicyReason] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [reasons, setReasons] = useState<Record<string, string>>({}),
    [pending, setPending] = useState<{
      operation: string;
      body: Record<string, unknown>;
    } | null>(null);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const policy = e.work_guidance_policy as
    { allowed?: boolean; version?: number } | undefined;
  const path = `/api/engagements/${encodeURIComponent(e.id)}/work-guidance`;
  function accept(result: Status) {
    if (
      result.engagement_id !== e.id ||
      result.current_engagement_revision !== e.revision ||
      result.policy_version !== (policy?.version ?? 0) ||
      !Number.isSafeInteger(result.version) ||
      result.version < 0 ||
      !Array.isArray(result.contexts) ||
      result.policy_allowed !== Boolean(policy?.allowed) ||
      (result.status === "AVAILABLE" &&
        (!result.opted_in || !result.personal_content_visible)) ||
      (result.candidates !== undefined &&
        (result.status !== "AVAILABLE" ||
          !result.opted_in ||
          !result.personal_content_visible))
    ) {
      setState(null);
      throw Error(
        "Work or assistance policy changed. Refresh this engagement before continuing.",
      );
    }
    setState(result);
  }
  async function load() {
    setBusy(true);
    setError("");
    try {
      const result = await request<Status>(path);
      if (alive.current) accept(result);
    } catch (err) {
      if (alive.current) {
        setState(null);
        setError((err as Error).message);
      }
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  async function send(
    operation: string,
    body: Record<string, unknown>,
    retry = false,
  ) {
    if (pending && !retry) return;
    const envelope =
      retry && pending
        ? pending
        : {
            operation,
            body: {
              ...body,
              command_id: crypto.randomUUID(),
              expected_engagement_revision: e.revision,
            },
          };
    setPending(envelope);
    setBusy(true);
    setError("");
    try {
      const result = await request<Status>(
        path + "/" + envelope.operation,
        "POST",
        envelope.body,
      );
      if (!alive.current) return;
      accept(result);
      setPending(null);
      if (envelope.operation !== "reveal")
        setState({ ...result, candidates: undefined });
    } catch (err) {
      if (!alive.current) return;
      if (err instanceof ApiError && err.status >= 400 && err.status < 500)
        setPending(null);
      if (err instanceof ApiError && [401, 403, 409].includes(err.status))
        setState(null);
      setError((err as Error).message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  function open(pin: Pin) {
    const names: Record<string, keyof Engagement> = {
      control: "controls",
      task: "tasks",
      request: "requests",
      artifact: "artifacts",
      population: "populations",
      selection: "selections",
      workpaper: "workpapers",
      review: "reviews",
    };
    if (!/^[a-f0-9]{64}$/.test(pin.sha256)) return;
    const rows = e[names[pin.kind]];
    if (!Array.isArray(rows)) return;
    const matches = (rows as Row[]).filter((r) => r.id === pin.id);
    if (matches.length !== 1) return;
    const row = matches[0];
    if (pin.kind === "artifact" && row.sha256 !== pin.sha256) return;
    if (
      pin.kind === "workpaper" &&
      !(
        Array.isArray(row.versions) &&
        Number.isSafeInteger(pin.version) &&
        (row.versions as Row[]).filter((v) => v.version === pin.version)
          .length === 1
      )
    )
      return;
    if (pin.kind !== "workpaper" && (row.version ?? null) !== pin.version)
      return;
    onPreview(pin.kind, row, pin);
  }
  const disabled = busy || parentBusy || !!pending;
  return (
    <details className="panel">
      <summary>Optional guidance for recorded work</summary>
      <p>
        Explanations use your visible audit records. They identify
        administrative next steps, not control effectiveness or hidden scenario
        answers. Guidance is off until the instructor allows it and you choose
        to use it.
      </p>
      {e.permissions?.includes("instruct") && (
        <fieldset disabled={disabled}>
          <legend>Instructor assistance policy</legend>
          <p>
            Current setting:{" "}
            {policy?.allowed
              ? "Guidance permitted; individual opt-in required"
              : "Unassisted: guidance unavailable"}
            .
          </p>
          <label>
            Reason for policy change
            <textarea
              maxLength={2000}
              value={policyReason}
              onChange={(ev) => setPolicyReason(ev.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={!policyReason.trim()}
            onClick={() =>
              void onCommand("assistance.configure", {
                work_guidance_allowed: !policy?.allowed,
                rationale: policyReason,
              })
            }
          >
            {policy?.allowed
              ? "Disable work guidance"
              : "Allow optional work guidance"}
          </button>
          <p>
            This records an instructor decision. Changing policy requires fresh
            personal opt-in.
          </p>
        </fieldset>
      )}
      {!policy?.allowed ? (
        <p>
          Work guidance is disabled for this engagement. Normal record
          navigation remains available.
        </p>
      ) : (
        <>
          <button
            type="button"
            disabled={busy || parentBusy || !!pending}
            onClick={() => void load()}
          >
            Check my guidance preference
          </button>
          {state && (
            <>
              <p role="status">{state.status.replaceAll("_", " ")}</p>
              <label>
                Reason for my preference
                <textarea
                  maxLength={2000}
                  value={rationale}
                  onChange={(ev) => setRationale(ev.target.value)}
                />
              </label>
              <button
                type="button"
                disabled={disabled || !rationale.trim()}
                onClick={() =>
                  void send("preference", {
                    enabled: !state.opted_in,
                    rationale,
                    expected_version: state.version,
                  })
                }
              >
                {state.opted_in
                  ? "Turn off my guidance"
                  : "Opt in to administrative guidance"}
              </button>
              {state.status === "AVAILABLE" && (
                <>
                  <label>
                    Control to investigate
                    <select
                      aria-label="Guidance control"
                      disabled={disabled}
                      value={context}
                      onChange={(ev) => {
                        setContext(ev.target.value);
                        setState((old) =>
                          old ? { ...old, candidates: undefined } : old,
                        );
                      }}
                    >
                      <option value="">Choose a control</option>
                      {state.contexts.map((c) => (
                        <option key={c.reference.id} value={c.reference.id}>
                          {c.reference.id} · {c.title}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    disabled={
                      disabled ||
                      !state.contexts.some((c) => c.reference.id === context)
                    }
                    onClick={() => {
                      const chosen = state.contexts.find(
                        (c) => c.reference.id === context,
                      );
                      if (chosen)
                        void send("reveal", { context_ref: chosen.reference });
                    }}
                  >
                    Show and record guidance for this control
                  </button>
                  {state.candidates && !state.candidates.length && (
                    <p>
                      No administrative suggestions are recorded for this
                      context. This does not establish audit completion.
                    </p>
                  )}
                  {state.candidates?.map((c) => (
                    <section key={c.id + ":" + c.sha256}>
                      <h4>{c.title}</h4>
                      <p>{c.reason}</p>
                      <small>Administrative observation · {c.code}</small>
                      <details>
                        <summary>Exact context and references</summary>
                        <p>
                          Control {c.context_ref.id} · {c.context_ref.sha256}
                        </p>
                        <p>
                          Suggestion {c.id} · {c.sha256}
                        </p>
                        <ul>
                          {c.references.map((r, i) => (
                            <li key={i}>
                              {r.kind} {r.id}: {r.status}
                              {r.status === "CURRENT" && r.reference && (
                                <button
                                  type="button"
                                  onClick={() => open(r.reference!)}
                                >
                                  Open exact reference
                                </button>
                              )}
                            </li>
                          ))}
                        </ul>
                      </details>
                      {c.decision && (
                        <p>
                          Your recorded decision: {c.decision.action} —{" "}
                          {c.decision.rationale}
                        </p>
                      )}
                      <label>
                        My review or dismissal reason
                        <textarea
                          maxLength={2000}
                          value={reasons[c.id] ?? ""}
                          onChange={(ev) =>
                            setReasons((old) => ({
                              ...old,
                              [c.id]: ev.target.value,
                            }))
                          }
                        />
                      </label>
                      {(["REVIEW", "DISMISS"] as const).map((action) => (
                        <button
                          type="button"
                          key={action}
                          disabled={disabled || !reasons[c.id]?.trim()}
                          onClick={() =>
                            void send("decision", {
                              candidate_id: c.id,
                              candidate_sha256: c.sha256,
                              action,
                              rationale: reasons[c.id],
                            })
                          }
                        >
                          {action === "REVIEW"
                            ? "Record my review"
                            : "Dismiss this exact suggestion"}
                        </button>
                      ))}
                      <p>
                        These personal decisions do not update audit work.
                        Changed source, scope or work references require fresh
                        inspection.
                      </p>
                    </section>
                  ))}
                </>
              )}
            </>
          )}
        </>
      )}
      {pending && !busy && (
        <p>
          The outcome is unconfirmed.{" "}
          <button
            type="button"
            onClick={() => void send(pending.operation, pending.body, true)}
          >
            Retry the exact guidance request
          </button>
        </p>
      )}
      {error && <p role="alert">{error}</p>}
      <small>
        Your preference, disclosure and decision history is private. Companion
        recovery retains an inactive archive; it does not restore an active
        opt-in.
      </small>
    </details>
  );
}
