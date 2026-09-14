import { useEffect, useState } from "react";
import { request, type Engagement } from "./api";
import {
  validateBoundResponse,
  sourceTimeline,
  authoredRelationships,
  type BoundResponse,
} from "./boundInstructorKey";
export default function BoundInstructorKey(props: {
  engagement: Engagement;
  viewerId: string;
}) {
  return (
    <BoundExplorer
      key={JSON.stringify([
        props.viewerId,
        props.engagement.id,
        props.engagement.permissions,
        props.engagement.revision,
      ])}
      {...props}
    />
  );
}
function BoundExplorer({
  engagement: e,
}: {
  engagement: Engagement;
  viewerId: string;
}) {
  const [response, setResponse] = useState<BoundResponse | null>(null),
    [error, setError] = useState(""),
    [selected, setSelected] = useState(""),
    [query, setQuery] = useState("");
  const allowed = e.permissions?.includes("instruct");
  useEffect(() => {
    let cancelled = false;
    if (!allowed) return;
    void request<BoundResponse>(
      `/api/engagements/${encodeURIComponent(e.id)}/instructor-binding`,
    )
      .then((value) => {
        if (cancelled) return;
        validateBoundResponse(value, e.id);
        setResponse(value);
      })
      .catch((err) => {
        if (!cancelled) {
          setResponse(null);
          setError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [e.id, allowed]);
  if (!allowed) return <p>Instructor access is required.</p>;
  if (error)
    return (
      <section aria-label="Bound instructor explanation">
        <h2>Engagement-bound explanation</h2>
        <p role="alert">{error}</p>
      </section>
    );
  if (!response)
    return <p role="status">Loading protected engagement binding…</p>;
  const s = response.snapshot,
    b = response.binding,
    source = s.sources.find((row) => row.id === selected),
    q = query.trim().toLowerCase();
  const filtered = s.sources.filter((row) =>
    [
      row.id,
      row.company,
      row.branch,
      row.system,
      row.record,
      row.actor_visibility_at_binding,
    ]
      .join(" ")
      .toLowerCase()
      .includes(q),
  );
  return (
    <section aria-label="Bound instructor explanation">
      <h2>Engagement-bound explanation</h2>
      <p>
        <strong>
          Instructor-authored interpretation · UNVALIDATED · no grades.
        </strong>{" "}
        Exact source identity and captured access state do not establish the
        correctness of these interpretations.
      </p>
      <p>
        {b.status === "HISTORICAL_REVISION"
          ? "Historical snapshot; current work has changed."
          : "Snapshot matches the recorded engagement revision."}{" "}
        Bound revision {b.bound_revision}; current revision {b.current_revision}
        . No automatic rebinding occurs.
      </p>
      <p>
        Scope: {s.engagement.scope.boundaries.join(" · ")} ·{" "}
        {s.engagement.scope.period_start} — {s.engagement.scope.period_end}.
        Audit simulation: {s.engagement.simulated_at}. Operator source as-of:{" "}
        {s.operator_source_as_of}. Audited actor: {s.audited_actor_id}.
      </p>
      <details>
        <summary>Exact binding and history pins</summary>
        <dl>
          <dt>Manifest</dt>
          <dd>
            <code>{b.manifest_sha256}</code>
          </dd>
          <dt>Engagement state</dt>
          <dd>
            <code>{s.engagement.state_sha256}</code>
          </dd>
          <dt>History</dt>
          <dd>
            <code>{s.engagement.history_sha256}</code>
          </dd>
        </dl>
      </details>
      <details>
        <summary>Software checks and interpretation limits</summary>
        <ul>
          {s.software_verified.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
        <ul>
          {s.limits.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      </details>
      <label>
        Find bound source
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      <p>
        {filtered.length} of {s.sources.length} bound sources match.
        Availability is captured at binding, not a current access promise.
      </p>
      <ul>
        {filtered.map((row) => (
          <li key={row.id}>
            <button
              type="button"
              aria-pressed={selected === row.id}
              onClick={() => setSelected(row.id)}
            >
              {row.id} · {row.record} · v{row.version}
            </button>{" "}
            · {row.actor_visibility_at_binding}
          </li>
        ))}
      </ul>
      {source && (
        <article aria-label="Selected bound source">
          <h3>
            {source.id} · {source.record}
          </h3>
          <p>
            {source.company} / {source.branch} / {source.system} · version{" "}
            {source.version}
          </p>
          <p>
            Exact SHA256: <code>{source.sha256}</code>
          </p>
          <p>
            Actor grant at binding:{" "}
            {source.actor_granted_at_binding ? "Granted" : "Not granted"}.
            Captured visibility: {source.actor_visibility_at_binding}.
          </p>
          <p>
            Retained audit copies:{" "}
            {source.retained_audit_artifact_ids.join(", ") || "None recorded"}.
            A retained copy does not imply current source-system access.
          </p>
          <p>{source.fact_verification}</p>
        </article>
      )}
      <details>
        <summary>
          Source timeline: event, availability and import are distinct
        </summary>
        <ol>
          {sourceTimeline(s.sources).map((row, i) => (
            <li key={`${row.sourceId}-${row.field}-${i}`}>
              <time>{row.at}</time> · {row.field.replaceAll("_", " ")} ·{" "}
              <button type="button" onClick={() => setSelected(row.sourceId)}>
                {row.sourceId}
              </button>{" "}
              · {row.record}
            </li>
          ))}
        </ol>
      </details>
      <h3>Authored issues and linked sources</h3>
      {s.authored.issues.map((issue) => (
        <article key={issue.id}>
          <h4>{issue.id}</h4>
          <p>{issue.claim}</p>
          <p>Uncertainty: {issue.uncertainty}</p>
          <p>Referenced controls: {issue.control_ids.join(", ")}</p>
          <div>
            {issue.source_ids.map((id) => (
              <button key={id} type="button" onClick={() => setSelected(id)}>
                Inspect {id}
              </button>
            ))}
          </div>
        </article>
      ))}
      <h3>Authored expectations and acceptable alternatives</h3>
      {s.authored.expectations.map((row) => (
        <article key={row.id}>
          <h4>{row.id}</h4>
          <p>Referenced issues: {row.issue_ids.join(", ")}</p>
          <p>{row.procedure}</p>
          <ul>
            {row.acceptable_alternatives.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ul>
        </article>
      ))}
      <details>
        <summary>Explicit authored relationships (not causal proof)</summary>
        <ul>
          {authoredRelationships(s).map((edge, i) => (
            <li key={i}>
              {edge.from} → {edge.to} · {edge.relation}
            </li>
          ))}
        </ul>
      </details>
      <h3>Unresolved interpretation limits</h3>
      <ul>
        {s.authored.uncertainty.map((text, i) => (
          <li key={i}>{text}</li>
        ))}
      </ul>
    </section>
  );
}
