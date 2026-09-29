import { useEffect, useRef, useState } from "react";
import { artifactURL, request, str, type Engagement, type Row } from "./api";
import { censusQuery } from "./sourceCensus";
import { submitCensusJob, type CensusCommand } from "./backgroundWork";
export default function SourceRecordCensus({
  engagement: e,
  viewerId,
  busy,
  backgroundKinds,
  onCommand,
}: {
  engagement: Engagement;
  viewerId: string;
  busy: boolean;
  backgroundKinds: string[];
  onCommand: (kind: string, payload: Record<string, unknown>) => void;
}) {
  const context = JSON.stringify([
    viewerId,
    e.id,
    e.scope,
    e.permissions,
    e.company_source_binding,
    e.evidence_acquisition,
    e.simulated_at,
  ]);
  return (
    <CensusForm
      key={context}
      engagement={e}
      busy={busy}
      backgroundKinds={backgroundKinds}
      onCommand={onCommand}
    />
  );
}
function CensusForm({
  engagement: e,
  busy,
  backgroundKinds,
  onCommand,
}: {
  engagement: Engagement;
  busy: boolean;
  backgroundKinds: string[];
  onCommand: (kind: string, payload: Record<string, unknown>) => void;
}) {
  const [systems, setSystems] = useState<Row[]>([]),
    [system, setSystem] = useState(""),
    [requestId, setRequestId] = useState(""),
    [versionPolicy, setVersionPolicy] = useState("ALL_VISIBLE_VERSIONS"),
    [start, setStart] = useState(""),
    [end, setEnd] = useState(""),
    [unknownPolicy, setUnknownPolicy] = useState("EXCLUDE"),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [loading, setLoading] = useState(false),
    [submitting, setSubmitting] = useState(false),
    [reviewed, setReviewed] = useState<Record<string, boolean>>({});
  const alive = useRef(true),
    pending = useRef<CensusCommand | null>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const permitted =
    e.phase === "ACTIVE" &&
    e.permissions?.some((p) => p === "learn" || p === "instruct");
  const eligible = e.requests.filter(
    (r) =>
      [
        "ISSUED",
        "ACKNOWLEDGED",
        "IN_PROGRESS",
        "CLARIFICATION",
        "SUBMITTED",
      ].includes(str(r.status)) &&
      e.scope.boundaries.includes(str(r.boundary_id)),
  );
  async function loadSystems() {
    setLoading(true);
    setError("");
    try {
      const result = await request<{ systems: Row[] }>(
        `/api/engagements/${encodeURIComponent(e.id)}/company/systems`,
      );
      if (alive.current) {
        setSystems(result.systems);
        if (!result.systems.some((s) => s.system === system)) setSystem("");
      }
    } catch (err) {
      if (alive.current) setError((err as Error).message);
    } finally {
      if (alive.current) setLoading(false);
    }
  }
  async function submit() {
    setError("");
    setNotice("");
    try {
      const query = censusQuery(versionPolicy, start, end, unknownPolicy);
      if (
        !systems.some((s) => s.system === system) ||
        !eligible.some((r) => r.id === requestId)
      )
        throw Error(
          "Choose a granted system and an issued request with a scoped boundary.",
        );
      const payload = { request_id: requestId, system_id: system, query };
      if (backgroundKinds.includes("company.census.collect")) {
        if (
          pending.current &&
          JSON.stringify(pending.current.payload) !== JSON.stringify(payload)
        )
          throw Error(
            "An earlier submission is unconfirmed. Inspect background work or restore its exact query before another submission.",
          );
        const envelope = pending.current ?? {
          command_id: crypto.randomUUID(),
          expected_revision: e.revision,
          kind: "company.census.collect" as const,
          payload,
        };
        pending.current = envelope;
        setSubmitting(true);
        const job = await submitCensusJob(e.id, envelope);
        if (!alive.current) return;
        pending.current = null;
        setNotice(
          `Census submission accepted (initial status: ${job.status.toLowerCase()}). Check background work for current status and the retained collection history below for completed results. Acceptance alone does not create or approve a population.`,
        );
      } else onCommand("company.census.collect", payload);
    } catch (err) {
      if (alive.current) setError((err as Error).message);
    } finally {
      if (alive.current) setSubmitting(false);
    }
  }
  const frozen = busy || loading || submitting;
  return (
    <details className="panel">
      <summary>Collect a source-record census</summary>
      <p>
        Sampling unit: one source record version, not an employee, transaction,
        or independently complete business population. Select one granted source
        system. Its versions and qualified origins remain distinct.
      </p>
      <p>
        Event window uses an inclusive start and exclusive end. Undated rows
        remain a separate stratum with unknown period membership. Source
        availability is limited to simulation time {e.simulated_at}; future and
        inaccessible versions are not a visible inventory.
      </p>
      <p>
        Audit interval: {e.scope.period_start} — {e.scope.period_end} (
        {str(e.scope.timezone) || "UTC"}). The server validates the event window
        against that interval.
      </p>
      {loading && <p role="status">Loading census source systems…</p>}
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <fieldset disabled={frozen || !permitted}>
          <button type="button" onClick={() => void loadSystems()}>
            Load census source systems
          </button>
          <label>
            Census source system
            <select
              required
              aria-label="Census source system"
              value={system}
              onChange={(event) => setSystem(event.target.value)}
            >
              <option value="">Choose granted system</option>
              {systems.map((s) => (
                <option key={str(s.system)} value={str(s.system)}>
                  {str(s.system)}
                  {s.source_store_id
                    ? ` · source ${str(s.source_store_id)}`
                    : ""}
                </option>
              ))}
            </select>
          </label>
          <label>
            Version policy
            <select
              aria-label="Census version policy"
              value={versionPolicy}
              onChange={(event) => setVersionPolicy(event.target.value)}
            >
              <option value="ALL_VISIBLE_VERSIONS">All visible versions</option>
              <option value="LATEST_VISIBLE_PER_RECORD">
                Latest visible version per record
              </option>
            </select>
          </label>
          <p>
            The latest visible version is selected before event-window
            filtering; a newer version outside the window does not cause an
            older version to be substituted.
          </p>
          <label>
            Event window start
            <input
              required
              aria-label="Census event window start"
              placeholder="2027-01-01T00:00:00Z"
              value={start}
              onChange={(event) => setStart(event.target.value)}
            />
          </label>
          <label>
            Event window end (exclusive)
            <input
              required
              aria-label="Census event window end"
              placeholder="2028-01-01T00:00:00Z"
              value={end}
              onChange={(event) => setEnd(event.target.value)}
            />
          </label>
          <label>
            Undated-record policy
            <select
              aria-label="Census undated policy"
              value={unknownPolicy}
              onChange={(event) => setUnknownPolicy(event.target.value)}
            >
              <option value="EXCLUDE">Exclude undated source versions</option>
              <option value="INCLUDE_UNDATED_STRATUM">
                Include a separate undated stratum
              </option>
            </select>
          </label>
          <label>
            Issued census evidence request
            <select
              required
              aria-label="Census evidence request"
              value={requestId}
              onChange={(event) => setRequestId(event.target.value)}
            >
              <option value="">Choose scoped issued request</option>
              {eligible.map((r) => (
                <option key={r.id} value={r.id}>
                  {str(r.title)} · {str(r.boundary_id)}
                </option>
              ))}
            </select>
          </label>
          <button>Collect census and source manifest</button>
        </fieldset>
      </form>
      {pending.current && !submitting && (
        <p>
          Submission outcome unconfirmed. The exact original query is retained
          locally until acceptance. Inspect background work before changing it.
          <button
            type="button"
            onClick={() => {
              const p = pending.current?.payload;
              if (p) {
                setSystem(p.system_id);
                setRequestId(p.request_id);
                setVersionPolicy(p.query.version_policy);
                setStart(p.query.event_window.start);
                setEnd(p.query.event_window.end);
                setUnknownPolicy(p.query.unknown_event_policy);
              }
            }}
          >
            Restore unconfirmed census query
          </button>
        </p>
      )}
      <h3>Retained source-record censuses</h3>
      {e.requests.flatMap((r) =>
        (Array.isArray(r.company_census_collections)
          ? (r.company_census_collections as Row[])
          : []
        ).map((c) => {
          const key = `${r.id}:${c.snapshot_id}`,
            next = c.next_command as {
              kind?: string;
              payload?: Record<string, unknown>;
            } | null,
            registered = e.populations.some(
              (p) => p.artifact_id === c.population_artifact_id,
            ),
            strata = c.strata as Row,
            excluded = c.excluded as Row;
          return (
            <section key={key}>
              <h4>{str(r.title)}</h4>
              <p>
                {str(c.system_id)} · {str(c.source_versions)} source versions ·{" "}
                {str(c.distinct_source_records)} distinct source records
              </p>
              <p>
                In event window: {str(strata?.IN_EVENT_WINDOW)} · Undated:{" "}
                {str(strata?.UNDATED)}. Excluded outside event window:{" "}
                {str(excluded?.outside_event_window)} · Excluded undated:{" "}
                {str(excluded?.undated)}.
              </p>
              <p>
                Manifest SHA256: <code>{str(c.manifest_sha256)}</code>
              </p>
              <p>
                Snapshot {str(c.snapshot_id)} · Captured {str(c.recorded_at)} ·
                Availability cutoff {str(c.as_of ?? c.simulated_at)}. One
                concrete source transaction; this does not create a globally
                synchronized portfolio.
              </p>
              <p>{str(c.qualification)}</p>
              {Boolean(c.source_store_id) && (
                <p>
                  Collection route {str(c.source_system_alias)} · Source store{" "}
                  {str(c.source_store_id)} · {str(c.portfolio_qualification)}
                </p>
              )}
              <details>
                <summary>Exact retained census query</summary>
                <pre>{JSON.stringify(c.query, null, 2)}</pre>
              </details>
              <p>
                <a href={artifactURL(e.id, str(c.manifest_artifact_id))}>
                  Download census manifest
                </a>{" "}
                ·{" "}
                <a href={artifactURL(e.id, str(c.population_artifact_id))}>
                  Download census population rows
                </a>
              </p>
              <details>
                <summary>Pinned original source versions</summary>
                <ul>
                  {(Array.isArray(c.native_artifacts)
                    ? (c.native_artifacts as Row[])
                    : []
                  ).map((a) => {
                    const source = a.source as Row;
                    const rows = Array.isArray(next?.payload?.rows)
                      ? (next.payload.rows as Row[])
                      : [];
                    const member = rows.find((row) => {
                      const physical = row.source as Row;
                      return (
                        physical &&
                        [
                          "company",
                          "branch",
                          "system",
                          "record",
                          "version",
                          "sha256",
                        ].every((k) => physical[k] === source?.[k])
                      );
                    });
                    const qualifiers = (source?.provenance ?? {}) as Row;
                    return (
                      <li key={str(a.artifact_id)}>
                        {["company", "branch", "system", "record"]
                          .map((k) => str(source?.[k]))
                          .join(" / ")}{" "}
                        · Version {str(source?.version)} · SHA256{" "}
                        <code>{str(source?.sha256)}</code>
                        <p>
                          Origin:{" "}
                          {str(source?.origin) || "See retained manifest"} ·
                          Date stratum:{" "}
                          {str(member?.date_stratum ?? source?.date_stratum) ||
                            "See retained rows"}
                        </p>
                        {Boolean(
                          qualifiers.classification ||
                          qualifiers.operational_fact_status,
                        ) && (
                          <p>
                            Source qualification:{" "}
                            {str(qualifiers.classification)}{" "}
                            {str(qualifiers.operational_fact_status)}
                          </p>
                        )}
                        <a href={artifactURL(e.id, str(a.artifact_id))}>
                          Download original {str(a.artifact_id)}
                        </a>
                      </li>
                    );
                  })}
                </ul>
              </details>
              <p>
                Independent reliability review has not been performed. Neither
                collection nor provisional import accepts completeness or
                testing sufficiency.
              </p>
              {registered ? (
                <p>
                  Imported in the population workspace; consult its current
                  reliability status.
                </p>
              ) : c.registration === "EMPTY_CENSUS" ? (
                <p>Empty census: no population import is available.</p>
              ) : (
                <>
                  <label>
                    <input
                      type="checkbox"
                      checked={!!reviewed[key]}
                      onChange={(event) =>
                        setReviewed((old) => ({
                          ...old,
                          [key]: event.target.checked,
                        }))
                      }
                    />
                    I reviewed the exact query, version unit, undated stratum
                    and source qualifiers for provisional import.
                  </label>
                  <button
                    disabled={
                      busy ||
                      !permitted ||
                      !reviewed[key] ||
                      next?.kind !== "population.import" ||
                      !next.payload
                    }
                    onClick={() => {
                      if (
                        reviewed[key] &&
                        next?.kind === "population.import" &&
                        next.payload
                      )
                        onCommand(next.kind, next.payload);
                    }}
                  >
                    Import reviewed census as provisional
                  </button>
                </>
              )}
            </section>
          );
        }),
      )}
    </details>
  );
}
