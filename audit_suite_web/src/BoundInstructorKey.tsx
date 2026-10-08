import { InstructorKeyViews } from "./InstructorKeyViews";
import {
  validateBoundFilters,
  type BoundKeyFilters,
} from "./instructorKeyViews";
import "./boundKeyNavigation.css";
import {
  boundIssuePage,
  BOUND_ISSUE_PAGE_SIZE,
  defaultIssueIndex,
  type BoundIssueIndex,
  boundSourcePage,
  issueControlLabel,
  selectedIssueExpectations,
  scopedTimelineSources,
  defaultSourceFilters,
  type BoundSourceFilters,
  boundRelationshipPage,
} from "./boundKeyNavigation";
import { boundRetainedArtifacts } from "./boundRetainedSources";
import { InstructorComparison } from "./InstructorComparison";
import { ReferenceCrosswalk } from "./ReferenceCrosswalk";
import { useEffect, useState } from "react";
import { request, type Engagement, type Row } from "./api";
import {
  validateBoundResponse,
  sourceTimeline,
  type BoundResponse,
} from "./boundInstructorKey";
export default function BoundInstructorKey(props: {
  engagement: Engagement;
  viewerId: string;
  savedViewsEnabled?: boolean;
  assessmentsEnabled?: boolean;
  onPreview?: (artifact: Row) => void;
  referenceCurrent?: string;
  onReferenceLegacy?: (id: string) => void;
}) {
  return (
    <BoundExplorer
      key={JSON.stringify([
        props.viewerId,
        props.engagement.id,
        props.engagement.permissions,
        props.engagement.revision,
        props.engagement.scope,
        props.engagement.company_source_binding,
        props.engagement.evidence_acquisition,
      ])}
      {...props}
    />
  );
}
function BoundExplorer({
  engagement: e,
  viewerId,
  savedViewsEnabled = false,
  assessmentsEnabled = false,
  onPreview,
  referenceCurrent,
  onReferenceLegacy,
}: {
  engagement: Engagement;
  viewerId: string;
  savedViewsEnabled?: boolean;
  assessmentsEnabled?: boolean;
  onPreview?: (artifact: Row) => void;
  referenceCurrent?: string;
  onReferenceLegacy?: (id: string) => void;
}) {
  const [response, setResponse] = useState<BoundResponse | null>(null),
    [error, setError] = useState("");
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
      <section className="bound-key" aria-label="Bound instructor explanation">
        <h2>Engagement-bound explanation</h2>
        <p role="alert">{error}</p>
      </section>
    );
  if (!response)
    return <p role="status">Loading protected engagement binding…</p>;
  return (
    <BoundWorkspace
      key={response.binding.manifest_sha256}
      response={response}
      engagement={e}
      viewerId={viewerId}
      savedViewsEnabled={savedViewsEnabled}
      assessmentsEnabled={assessmentsEnabled}
      onPreview={onPreview}
      referenceCurrent={referenceCurrent}
      onReferenceLegacy={onReferenceLegacy}
    />
  );
}
function BoundWorkspace({
  response,
  engagement: e,
  viewerId,
  savedViewsEnabled,
  assessmentsEnabled,
  onPreview,
  referenceCurrent,
  onReferenceLegacy,
}: {
  response: BoundResponse;
  engagement: Engagement;
  viewerId: string;
  savedViewsEnabled: boolean;
  assessmentsEnabled: boolean;
  onPreview?: (artifact: Row) => void;
  referenceCurrent?: string;
  onReferenceLegacy?: (id: string) => void;
}) {
  const [selected, setSelected] = useState(""),
    [query, setQuery] = useState(""),
    [issueId, setIssueId] = useState(""),
    [scopeToIssue, setScopeToIssue] = useState(false),
    [page, setPage] = useState(0),
    [sourceFilters, setSourceFilters] =
      useState<BoundSourceFilters>(defaultSourceFilters),
    [relationshipPage, setRelationshipPage] = useState(0),
    [relationshipExpectation, setRelationshipExpectation] = useState(""),
    [issueIndex, setIssueIndex] = useState<BoundIssueIndex>(defaultIssueIndex);
  useEffect(() => {
    setRelationshipPage(0);
  }, [issueId, selected, relationshipExpectation]);
  useEffect(() => {
    if (
      referenceCurrent &&
      response.snapshot.authored.issues.some((i) => i.id === referenceCurrent)
    ) {
      selectReferenceIssue(referenceCurrent);
    }
  }, [referenceCurrent, response]);
  const s = response.snapshot,
    b = response.binding,
    issueRows = boundIssuePage(s, issueIndex),
    source = s.sources.find((row) => row.id === selected),
    issue = s.authored.issues.find((row) => row.id === issueId),
    expectations = selectedIssueExpectations(s, issueId),
    sources = boundSourcePage(s, {
      issueId: scopeToIssue ? issueId : "",
      query,
      page,
      sourceFilters,
    }),
    relationships = boundRelationshipPage(
      s,
      issueId,
      selected,
      relationshipPage,
      relationshipExpectation,
    ),
    selectedExpectation = s.authored.expectations.find(
      (row) => row.id === relationshipExpectation,
    );
  function selectEndpoint(
    kind: "issue" | "source" | "expectation",
    id: string,
  ) {
    const rows =
      kind === "issue"
        ? s.authored.issues
        : kind === "source"
          ? s.sources
          : s.authored.expectations;
    if (rows.filter((row) => row.id === id).length !== 1) return;
    if (kind === "issue") {
      setIssueId(id);
      setScopeToIssue(true);
    }
    if (kind === "source") setSelected(id);
    if (kind === "expectation") setRelationshipExpectation(id);
    setRelationshipPage(0);
  }
  function revealIssue(id: string) {
    const position = s.authored.issues.findIndex((row) => row.id === id);
    if (position >= 0)
      setIssueIndex({
        ...defaultIssueIndex(),
        page: Math.floor(position / BOUND_ISSUE_PAGE_SIZE),
      });
  }
  function selectReferenceIssue(id: string) {
    setIssueId(id);
    setScopeToIssue(true);
    setPage(0);
    revealIssue(id);
  }
  function chooseIssue(id: string) {
    setIssueId(id);
    setScopeToIssue(true);
    setQuery("");
    setPage(0);
    setSelected("");
  }
  return (
    <section className="bound-key" aria-label="Bound instructor explanation">
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
      <InstructorKeyViews
        engagement={e}
        viewerId={viewerId}
        enabled={savedViewsEnabled}
        kind="BOUND"
        keyPin={b.manifest_sha256}
        filters={{
          query,
          issue_id: issueId || null,
          scope_to_issue: scopeToIssue,
          source: source
            ? { id: source.id, version: source.version, sha256: source.sha256 }
            : null,
          page: sources.page,
          issue_index: { ...issueIndex, page: issueRows.page },
          source_filters: sourceFilters,
        }}
        validate={(value) => validateBoundFilters(value as BoundKeyFilters, s)}
        onRestore={(value) => {
          const v = validateBoundFilters(value as BoundKeyFilters, s);
          setQuery(v.query);
          setIssueId(v.issue_id ?? "");
          setScopeToIssue(v.scope_to_issue);
          setSelected(v.source?.id ?? "");
          setPage(v.page);
          setIssueIndex(v.issue_index ?? defaultIssueIndex());
          setSourceFilters(v.source_filters ?? defaultSourceFilters());
          setRelationshipExpectation("");
        }}
      />
      {response.reference_crosswalk && (
        <ReferenceCrosswalk
          key={response.reference_crosswalk.sha256 + ":" + issueId}
          value={response.reference_crosswalk}
          mode="CURRENT"
          selected={issueId}
          onLegacy={onReferenceLegacy}
          onCurrent={(id) => {
            selectReferenceIssue(id);
          }}
        />
      )}
      <InstructorComparison
        engagement={e}
        bound={response}
        viewerId={viewerId}
        assessmentsEnabled={assessmentsEnabled}
      />
      <section aria-label="Authored issue index" className="bound-key-index">
        <h3>Authored issues</h3>
        <p>
          {s.authored.issues.length} issues · {s.authored.expectations.length}{" "}
          expectations · {s.sources.length} unique bound originals. Select an
          issue to read its interpretation and linked expectations.
        </p>
        <p>
          Search literal issue/control text, explicitly linked procedure and
          alternative text, task IDs, and bound source identities. Owner and
          severity facets are unsupported because this bound schema does not
          supply them; no classification is inferred.
        </p>
        <label>
          Find authored issue
          <input
            type="search"
            value={issueIndex.query}
            maxLength={1000}
            onChange={(event) =>
              setIssueIndex({
                ...issueIndex,
                query: event.target.value,
                page: 0,
              })
            }
          />
        </label>
        <label>
          Issue control
          <select
            aria-label="Issue control"
            value={issueIndex.control_id ?? ""}
            onChange={(event) =>
              setIssueIndex({
                ...issueIndex,
                control_id: event.target.value || null,
                page: 0,
              })
            }
          >
            <option value="">All bound issue controls</option>
            {issueRows.controls.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => setIssueIndex(defaultIssueIndex())}
        >
          Clear issue filters
        </button>
        <p role="status">
          {issueRows.filtered.length} of {issueRows.total} authored issues
          match. Showing {issueRows.rows.length} on this page.
        </p>
        <ul aria-label="Matching authored issues">
          {issueRows.rows.map((row) => (
            <li key={row.id}>
              <button
                type="button"
                aria-pressed={issueId === row.id}
                onClick={() => chooseIssue(row.id)}
              >
                <strong>{issueControlLabel(row, e.controls)}</strong>
                <span>{row.id}</span>
                <small>
                  {row.source_ids.length} linked originals ·{" "}
                  {selectedIssueExpectations(s, row.id).length} expectations
                </small>
              </button>
            </li>
          ))}
        </ul>
        {!issueRows.filtered.length && s.authored.issues.length > 0 && (
          <p role="status">
            No authored issues match. Clear the search or control filter.
          </p>
        )}
        <nav aria-label="Authored issue pages">
          <button
            type="button"
            disabled={issueRows.page === 0}
            onClick={() =>
              setIssueIndex({ ...issueIndex, page: issueRows.page - 1 })
            }
          >
            Previous issues
          </button>
          <span role="status">
            Issue page {issueRows.page + 1} of {issueRows.pages}
          </span>
          <button
            type="button"
            disabled={issueRows.page + 1 === issueRows.pages}
            onClick={() =>
              setIssueIndex({ ...issueIndex, page: issueRows.page + 1 })
            }
          >
            Next issues
          </button>
        </nav>
        {issue && !issueRows.rows.some((row) => row.id === issue.id) && (
          <p>
            Selected issue {issue.id} is outside this index page or filter; its
            exact interpretation remains below.
            <button type="button" onClick={() => revealIssue(issue.id)}>
              Show selected issue {issue.id} in index
            </button>
          </p>
        )}
        {!s.authored.issues.length && (
          <p>No authored issues are bound. Sources remain available below.</p>
        )}
      </section>
      <div className="bound-key-workspace">
        <section aria-label="Selected authored issue">
          {issue ? (
            <>
              <h3>{issue.id}</h3>
              <p>{issueControlLabel(issue, e.controls)}</p>
              <p>{issue.claim}</p>
              <p>Uncertainty: {issue.uncertainty}</p>
              <h4>
                Linked expectations ({expectations.length} of{" "}
                {s.authored.expectations.length})
              </h4>
              <p>
                Other expectations remain under their linked issues in the
                index. These authored links do not establish completed testing.
              </p>
              {expectations.map((row) => (
                <details key={row.id}>
                  <summary>{row.id}</summary>
                  <p>{row.procedure}</p>
                  <p>
                    Explicit authored procedure IDs:{" "}
                    {row.task_ids?.join(", ") || "Unmapped"}.
                  </p>
                  <p>Referenced issues: {row.issue_ids.join(", ")}</p>
                  <ul>
                    {row.acceptable_alternatives.map((text, i) => (
                      <li key={i}>{text}</li>
                    ))}
                  </ul>
                </details>
              ))}
              {!expectations.length && (
                <p>No expectation is explicitly linked to this issue.</p>
              )}
            </>
          ) : (
            <p>
              Select an authored issue above. Sources can also be inspected
              independently; no issue is selected automatically.
            </p>
          )}
        </section>
        <section aria-label="Bound source browser">
          <h3>Bound originals</h3>
          <label>
            Source scope
            <select
              value={scopeToIssue && issue ? "issue" : "all"}
              onChange={(event) => {
                setScopeToIssue(event.target.value === "issue");
                setPage(0);
              }}
            >
              <option value="all">All bound originals</option>
              {issue && (
                <option value="issue">
                  Originals linked to selected issue
                </option>
              )}
            </select>
          </label>
          {(["system", "visibility"] as const).map((field) => (
            <label key={field}>
              {field === "system"
                ? "Physical source system"
                : "Captured source visibility"}
              <select
                value={sourceFilters[field] ?? ""}
                onChange={(event) => {
                  setSourceFilters({
                    ...sourceFilters,
                    [field]: event.target.value || null,
                  });
                  setPage(0);
                }}
              >
                <option value="">All captured values</option>
                {[
                  ...new Set(
                    s.sources.map((row) =>
                      field === "system"
                        ? row.system
                        : row.actor_visibility_at_binding,
                    ),
                  ),
                ]
                  .sort()
                  .map((value) => (
                    <option key={value}>{value}</option>
                  ))}
              </select>
            </label>
          ))}
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setSourceFilters(defaultSourceFilters());
              setPage(0);
            }}
          >
            Clear source filters
          </button>
          <label>
            Find bound source
            <input
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(0);
              }}
            />
          </label>
          <p>
            {sources.filtered.length} of {sources.scopeCount} originals match
            this scope and search ({sources.total} total bound originals).
            Availability is captured at binding, not a current access promise.
          </p>
          <ul
            className="bound-source-list"
            aria-label="Matching bound originals"
          >
            {sources.rows.map((row) => (
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
          {!sources.filtered.length && (
            <p role="status">
              No bound originals match. Clear the search or choose all bound
              originals.
            </p>
          )}
          <nav aria-label="Bound source pages">
            <button
              type="button"
              disabled={sources.page === 0}
              onClick={() => setPage(sources.page - 1)}
            >
              Previous sources
            </button>
            <span role="status">
              Page {sources.page + 1} of {sources.pages}
            </span>
            <button
              type="button"
              disabled={sources.page + 1 === sources.pages}
              onClick={() => setPage(sources.page + 1)}
            >
              Next sources
            </button>
          </nav>
          {source && !sources.filtered.some((row) => row.id === source.id) && (
            <p>
              The selected original is outside the current filter. Its exact
              pinned details remain below.
            </p>
          )}
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
              {source.source_store_id && (
                <p>
                  Physical source store: <code>{source.source_store_id}</code> ·
                  alias <code>{source.source_system_alias}</code>. Registry
                  SHA256: <code>{source.registry_sha256}</code>. Capture is per
                  component; there is no shared transaction across the
                  portfolio.
                </p>
              )}
              <p>
                Actor grant at binding:{" "}
                {source.actor_granted_at_binding ? "Granted" : "Not granted"}.
                Captured visibility: {source.actor_visibility_at_binding}.
              </p>
              <p>
                Retained audit copies:{" "}
                {source.retained_audit_artifact_ids.join(", ") ||
                  "None recorded"}
                . A retained copy does not imply current source-system access.
              </p>
              {onPreview && (
                <div aria-label="Retained bound originals">
                  {boundRetainedArtifacts(e, source).map((artifact) => (
                    <button
                      key={artifact.id}
                      type="button"
                      onClick={() => {
                        const exact = boundRetainedArtifacts(e, source).find(
                          (row) => row.id === artifact.id,
                        );
                        if (exact) onPreview(exact);
                      }}
                    >
                      Inspect retained original {artifact.id}
                    </button>
                  ))}
                  {boundRetainedArtifacts(e, source).length === 0 && (
                    <p>
                      No exact retained original is currently available for
                      inspection. No newer source version is substituted.
                    </p>
                  )}
                  <p>
                    These links open current authorized audit copies. Captured
                    source-system access does not grant access now.
                  </p>
                </div>
              )}
              <p>{source.fact_verification}</p>
            </article>
          )}
          <details>
            <summary>
              Source timeline: event, availability and import are distinct
            </summary>
            <p>
              {source
                ? "Selected original only."
                : "Originals on this page only."}{" "}
              Other originals remain available through the source pages.
            </p>
            <ol>
              {sourceTimeline(scopedTimelineSources(source, sources.rows)).map(
                (row, i) => (
                  <li key={`${row.sourceId}-${row.field}-${i}`}>
                    <time>{row.at}</time> · {row.field.replaceAll("_", " ")} ·{" "}
                    <button
                      type="button"
                      onClick={() => setSelected(row.sourceId)}
                    >
                      {row.sourceId}
                    </button>{" "}
                    · {row.record}
                  </li>
                ),
              )}
            </ol>
          </details>
        </section>
      </div>
      <details>
        <summary>Explicit authored relationships (not causal proof)</summary>
        <p role="status">
          {relationships.filtered} of {relationships.total} literal links relate
          to the selected issue, original or expectation;{" "}
          {relationships.rows.length} shown on this page. Selection never opens
          hidden originals or changes formal work.
        </p>
        <ul>
          {relationships.rows.map((edge, i) => (
            <li key={i}>
              <button
                type="button"
                onClick={() =>
                  selectEndpoint(
                    edge.relation === "AUTHORED_SOURCE_REFERENCE"
                      ? "issue"
                      : "expectation",
                    edge.from,
                  )
                }
              >
                {edge.relation === "AUTHORED_SOURCE_REFERENCE"
                  ? "Select issue "
                  : "Inspect expectation "}
                {edge.from}
              </button>
              {" → "}
              <button
                type="button"
                onClick={() =>
                  selectEndpoint(
                    edge.relation === "AUTHORED_SOURCE_REFERENCE"
                      ? "source"
                      : "issue",
                    edge.to,
                  )
                }
              >
                {edge.relation === "AUTHORED_SOURCE_REFERENCE"
                  ? "Select source "
                  : "Select issue "}
                {edge.to}
              </button>
              {" · "}
              {edge.relation}
            </li>
          ))}
        </ul>
        {!relationships.rows.length && (
          <p>No literal relationship matches this selection.</p>
        )}
        <nav aria-label="Authored relationship pages">
          <button
            type="button"
            disabled={relationships.page === 0}
            onClick={() => setRelationshipPage(relationships.page - 1)}
          >
            Previous relationships
          </button>
          <span>
            Page {relationships.page + 1} of {relationships.pages}
          </span>
          <button
            type="button"
            disabled={relationships.page + 1 === relationships.pages}
            onClick={() => setRelationshipPage(relationships.page + 1)}
          >
            Next relationships
          </button>
        </nav>
        <button
          type="button"
          onClick={() => {
            setIssueId("");
            setSelected("");
            setRelationshipExpectation("");
            setScopeToIssue(false);
          }}
        >
          Clear relationship selection
        </button>
        {selectedExpectation && (
          <article aria-label="Selected authored expectation">
            <h4>{selectedExpectation.id}</h4>
            <p>{selectedExpectation.procedure}</p>
            <p>
              Exact task IDs:{" "}
              {selectedExpectation.task_ids?.join(", ") || "Unmapped"}
            </p>
            <ul>
              {selectedExpectation.acceptable_alternatives.map((text, i) => (
                <li key={i}>{text}</li>
              ))}
            </ul>
            {selectedExpectation.issue_ids.map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => selectEndpoint("issue", id)}
              >
                Select linked issue {id}
              </button>
            ))}
          </article>
        )}
      </details>
      <details>
        <summary>Unresolved interpretation limits</summary>
        <ul>
          {s.authored.uncertainty.map((text, i) => (
            <li key={i}>{text}</li>
          ))}
        </ul>
      </details>
    </section>
  );
}
