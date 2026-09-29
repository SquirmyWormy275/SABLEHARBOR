import { useEffect, useRef, useState } from "react";
import { ApiError, request, type Engagement } from "./api";
import {
  acceptedDisposition,
  dispositionRecords,
  dispositions,
  dispositionContext,
  dispositionLabel,
  dispositionCommand,
  validateDispositionInputs,
  type DispositionInputs,
  type DispositionDraft,
  type DispositionCommand,
} from "./sourceImpactDisposition";
const empty = (): DispositionDraft => ({
  target_sha256: "",
  disposition: "ACKNOWLEDGED",
  rationale: "",
  intended_action: "",
  retest_sha256: null,
  predecessor: null,
});
export default function SourceImpactDisposition(props: {
  engagement: Engagement;
  viewerId: string;
  artifactId: string;
  enabled: boolean;
  onState: (e: Engagement) => void;
}) {
  if (
    !props.enabled ||
    !props.viewerId ||
    !props.engagement.permissions?.some(
      (p) => p === "learn" || p === "instruct",
    )
  )
    return null;
  return (
    <Editor
      key={
        dispositionContext(props.engagement, props.viewerId) + props.artifactId
      }
      {...props}
    />
  );
}
function Editor({
  engagement: e,
  viewerId,
  artifactId,
  onState,
}: {
  engagement: Engagement;
  viewerId: string;
  artifactId: string;
  onState: (e: Engagement) => void;
}) {
  const [input, setInput] = useState<DispositionInputs | null>(null),
    [draft, setDraft] = useState(empty),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [pending, setPending] = useState<DispositionCommand | null>(null);
  const epoch = useRef(0);
  useEffect(() => {
    epoch.current++;
    return () => {
      epoch.current++;
    };
  }, []);
  async function load() {
    const n = ++epoch.current;
    setBusy(true);
    setError("");
    setInput(null);
    try {
      const v = await request<DispositionInputs>(
        `/api/engagements/${encodeURIComponent(e.id)}/company/impact/disposition-inputs?artifact_id=${encodeURIComponent(artifactId)}`,
      );
      if (n === epoch.current)
        setInput(validateDispositionInputs(v, e, artifactId));
    } catch (x) {
      if (n === epoch.current) setError((x as Error).message);
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  async function save(retry?: DispositionCommand) {
    if (!input) return;
    let command: DispositionCommand;
    try {
      command =
        retry ?? dispositionCommand(e, input, draft, crypto.randomUUID());
    } catch (x) {
      setError((x as Error).message);
      return;
    }
    const n = ++epoch.current;
    setBusy(true);
    setError("");
    setPending(command);
    try {
      const state = await request<Engagement>(
        `/api/engagements/${encodeURIComponent(e.id)}/commands`,
        "POST",
        command,
      );
      if (n !== epoch.current) return;
      if (!acceptedDisposition(e, state, viewerId, command))
        throw Error(
          "Command response cannot be matched safely. Inspect history or retry this exact command.",
        );
      setPending(null);
      setDraft(empty());
      setInput(null);
      onState(state);
    } catch (x) {
      if (n !== epoch.current) return;
      setError((x as Error).message);
      if (x instanceof ApiError && x.status >= 400 && x.status < 500) {
        setPending(null);
        setInput(null);
        if (x.status === 401 || x.status === 403) setDraft(empty());
      }
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  return (
    <details>
      <summary>Record reassessment disposition</summary>
      <p>
        Record your decision about one exact linked record. Linked work does not
        establish a passed retest, professional clearance or review completion.
      </p>
      <button
        type="button"
        disabled={busy || !!pending}
        onClick={() => void load()}
      >
        Load current exact choices
      </button>
      {error && <p role="alert">{error}</p>}
      {input && (
        <>
          <p>
            Current comparison for this decision: retained version{" "}
            {String(input.comparison.collected_version)} → observed source
            version {String(input.comparison.latest_visible_version)}. These
            freshly loaded choices may be newer than the earlier report.
          </p>
          <p>
            Observed {input.observed.discovered_at}; rechecked{" "}
            {input.observed.rechecked_at}.
          </p>
          <details>
            <summary>Exact comparison pin</summary>
            <code>{input.comparison.sha256}</code>
            <pre>{JSON.stringify(input.comparison, null, 2)}</pre>
          </details>
          <fieldset disabled={busy || !!pending}>
            <legend>Explicit reassessment decision for {artifactId}</legend>
            <label>
              Affected work
              <select
                aria-label="Affected work"
                value={draft.target_sha256}
                onChange={(ev) =>
                  setDraft({
                    ...draft,
                    target_sha256: ev.target.value,
                    predecessor: null,
                  })
                }
              >
                <option value="">Choose an exact record</option>
                {input.targets.map((c) => (
                  <option key={c.sha256} value={c.sha256}>
                    {dispositionLabel(c)}
                  </option>
                ))}
              </select>
            </label>
            {input.targets
              .filter((c) => c.sha256 === draft.target_sha256)
              .map((c) => (
                <details key={c.sha256}>
                  <summary>Exact selected work identity</summary>
                  <p>{dispositionLabel(c)}</p>
                  <p>
                    Reference SHA256: <code>{c.sha256}</code>
                  </p>
                  <p>
                    Recorded work SHA256: <code>{c.record_sha256}</code>
                  </p>
                  <pre>{JSON.stringify(c.reference, null, 2)}</pre>
                </details>
              ))}
            <label>
              Disposition
              <select
                aria-label="Disposition"
                value={draft.disposition}
                onChange={(ev) =>
                  setDraft({
                    ...draft,
                    disposition: ev.target
                      .value as DispositionDraft["disposition"],
                    retest_sha256: null,
                  })
                }
              >
                {Object.entries(dispositions).map(([v, label]) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            {draft.disposition === "NOT_APPLICABLE_TO_SELECTED_WORK" && (
              <p>
                This describes the relevance to this selected work only; it does
                not change framework or control applicability.
              </p>
            )}
            <label>
              Rationale
              <textarea
                aria-label="Reassessment rationale"
                maxLength={4000}
                value={draft.rationale}
                onChange={(ev) =>
                  setDraft({ ...draft, rationale: ev.target.value })
                }
              />
            </label>
            <label>
              Intended reassessment action
              <textarea
                aria-label="Intended reassessment action"
                maxLength={2000}
                value={draft.intended_action}
                onChange={(ev) =>
                  setDraft({ ...draft, intended_action: ev.target.value })
                }
              />
            </label>
            {draft.disposition === "RETEST_LINKED" && (
              <label>
                Existing reassessment work
                <select
                  aria-label="Existing reassessment work"
                  value={draft.retest_sha256 ?? ""}
                  onChange={(ev) =>
                    setDraft({
                      ...draft,
                      retest_sha256: ev.target.value || null,
                    })
                  }
                >
                  <option value="">Choose an exact retained version</option>
                  {input.retests.map((c) => (
                    <option key={c.sha256} value={c.sha256}>
                      {dispositionLabel(c)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              Prior disposition
              <select
                aria-label="Prior disposition"
                value={draft.predecessor?.id ?? ""}
                onChange={(ev) => {
                  const p = input.predecessors.find(
                    (p) => p.id === ev.target.value,
                  );
                  setDraft({
                    ...draft,
                    predecessor: p ? { id: p.id, sha256: p.sha256 } : null,
                  });
                }}
              >
                <option value="">
                  {input.predecessors.some(
                    (p) => p.target_sha256 === draft.target_sha256,
                  )
                    ? "Choose prior disposition to correct"
                    : "New initial disposition"}
                </option>
                {input.predecessors
                  .filter((p) => p.target_sha256 === draft.target_sha256)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      Append correction to {p.id}
                    </option>
                  ))}
              </select>
            </label>
            <p>
              Prior records remain unchanged. Saving records this disposition
              only.
            </p>
            <button type="button" onClick={() => void save()}>
              Save disposition
            </button>
          </fieldset>
        </>
      )}
      {pending && (
        <div role="status">
          <p>
            The command may already have been accepted. No different command
            will be sent automatically.
          </p>
          <code>{pending.command_id}</code>
          <button
            type="button"
            disabled={busy}
            onClick={() => void save(pending)}
          >
            Retry exact disposition command
          </button>
        </div>
      )}
    </details>
  );
}
export function SourceImpactDispositionHistory({
  engagement: e,
  enabled,
}: {
  engagement: Engagement;
  enabled: boolean;
}) {
  if (!enabled) return null;
  const records = dispositionRecords(e);
  return (
    <details>
      <summary>Recorded reassessment dispositions ({records.length})</summary>
      <p>
        Recorded decisions and linked work are not professional clearance or
        completed review. Prior records remain part of the history. These are
        recorded comparisons; opening history does not recheck company sources.
      </p>
      {!records.length && <p>No reassessment dispositions recorded.</p>}
      {records.map((r) => (
        <article key={r.id}>
          <h4>
            {r.id} · disposition version {r.version} · workspace revision{" "}
            {r.revision}
          </h4>
          <p>
            Recorded by {r.actor} at {r.recorded_at}
          </p>
          {r.context_status !== "CURRENT" ||
          r.personal_content_visible !== true ? (
            <p>Disposition details unavailable in this current context.</p>
          ) : (
            <>
              <p>{r.disposition && dispositions[r.disposition]}</p>
              <p>{r.rationale}</p>
              <p>Intended action: {r.intended_action}</p>
              {r.target && <p>Affected work: {dispositionLabel(r.target)}</p>}
              {r.retest && (
                <p>
                  Linked work: {dispositionLabel(r.retest)}. Its outcome is not
                  inferred.
                </p>
              )}
              <p>Predecessor: {r.predecessor?.id ?? "none"}</p>
              <details>
                <summary>Exact recorded source and work pins</summary>
                <p>Retained original: {r.artifact_id}</p>
                <pre>{JSON.stringify(r.comparison, null, 2)}</pre>
                <p>
                  Target record SHA256: <code>{r.target?.record_sha256}</code>
                </p>
                <p>
                  Target reference SHA256: <code>{r.target?.sha256}</code>
                </p>
                {r.retest && (
                  <p>
                    Linked record SHA256: <code>{r.retest.record_sha256}</code>
                  </p>
                )}
                <p>
                  Discovered {r.observed?.discovered_at}; rechecked{" "}
                  {r.observed?.rechecked_at}
                </p>
              </details>
            </>
          )}
        </article>
      ))}
    </details>
  );
}
