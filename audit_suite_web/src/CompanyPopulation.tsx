import { useEffect, useState } from "react";
import { artifactURL, request, str, type Engagement, type Row } from "./api";
const tables = [
  "commercial_changes",
  "service_incidents",
  "workforce_changes",
  "contract_versions",
];
export function sourceMonth(value: string) {
  const m = /^(\d{4})-(\d{2})-/.exec(value);
  return m ? (Number(m[1]) - 2027) * 12 + Number(m[2]) : 0;
}
export function populationQuery(
  table: string,
  scenario: string,
  first: string,
  last: string,
  text: string,
) {
  const a = Number(first),
    b = Number(last),
    units = text
      .split(/[,\n]/)
      .map((x) => x.trim())
      .filter(Boolean);
  if (
    !tables.includes(table) ||
    !["base", "downside", "expansion"].includes(scenario)
  )
    throw new Error("Choose a granted table and source scenario.");
  if (!Number.isInteger(a) || !Number.isInteger(b) || a < 1 || b > 60 || a > b)
    throw new Error("Choose ordered whole source months from 1 through 60.");
  if (!units.length || new Set(units).size !== units.length)
    throw new Error(
      "Enter distinct source unit identifiers; no corporate mapping is assumed.",
    );
  return {
    table,
    source_scenario: scenario,
    month_start: a,
    month_end: b,
    units,
  };
}
export default function CompanyPopulation({
  engagement: e,
  busy,
  onCommand,
}: {
  engagement: Engagement;
  busy: boolean;
  onCommand: (kind: string, payload: Record<string, unknown>) => void;
}) {
  const [systems, setSystems] = useState<Row[]>([]),
    [table, setTable] = useState("");
  const [scenario, setScenario] = useState("base"),
    [first, setFirst] = useState(""),
    [last, setLast] = useState("");
  const [units, setUnits] = useState(""),
    [requestId, setRequestId] = useState(""),
    [error, setError] = useState("");
  const [loading, setLoading] = useState(false),
    [reviewed, setReviewed] = useState<Record<string, boolean>>({});
  useEffect(() => {
    let active = true;
    setSystems([]);
    setTable("");
    setLoading(true);
    setError("");
    request<{ systems: Row[] }>(
      `/api/engagements/${encodeURIComponent(e.id)}/company/systems`,
    )
      .then((r) => {
        if (active)
          setSystems(r.systems.filter((s) => tables.includes(str(s.system))));
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [e.id, e.simulated_at, JSON.stringify(e.permissions)]);
  useEffect(() => {
    const a = sourceMonth(e.scope.period_start),
      b = sourceMonth(e.scope.period_end);
    setFirst(a >= 1 && a <= 60 ? String(a) : "");
    setLast(b >= 1 && b <= 60 ? String(b) : "");
    setUnits("");
    setRequestId("");
    setReviewed({});
    setScenario("base");
  }, [e.id, e.scope.period_start, e.scope.period_end]);
  const permitted =
    (e.permissions ?? []).some((p) => ["learn", "instruct"].includes(p)) &&
    e.phase === "ACTIVE";
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
  return (
    <details className="panel">
      <summary>Collect a company source population</summary>
      <p>
        Sampling unit: one source record version. All matching visible versions
        are included, including earlier versions. These are not necessarily
        distinct transactions or independent observations.
      </p>
      <p>
        Forecast and planning qualifiers remain unchanged. Choose exact source
        units explicitly; their applicability to the request boundary needs
        review.
      </p>
      {error && <p role="alert">{error}</p>}
      {loading && <p role="status">Reading granted source tables…</p>}
      {!loading && !error && !systems.length && (
        <p>No supported operating tables are granted to this engagement.</p>
      )}
      <form
        onSubmit={(ev) => {
          ev.preventDefault();
          try {
            const query = populationQuery(table, scenario, first, last, units);
            if (
              !eligible.some((r) => r.id === requestId) ||
              !systems.some((s) => s.system === table)
            )
              throw new Error(
                "Choose a granted table and issued request with a scoped boundary.",
              );
            setError("");
            onCommand("company.population.collect", {
              request_id: requestId,
              query,
            });
          } catch (err) {
            setError((err as Error).message);
          }
        }}
      >
        <label>
          Source table
          <select
            required
            value={table}
            onChange={(ev) => setTable(ev.target.value)}
          >
            <option value="">Choose a granted table</option>
            {systems.map((s) => (
              <option key={str(s.system)} value={str(s.system)}>
                {str(s.system).replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <label>
          Source scenario
          <select
            value={scenario}
            onChange={(ev) => setScenario(ev.target.value)}
          >
            {["base", "downside", "expansion"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
        <p>
          The scenario must match the connected branch. Month 1 is January 2027;
          month 60 is December 2031. Whole source months must fit the audit
          period and have closed by the simulation date.
        </p>
        <label>
          First source month
          <input
            required
            type="number"
            min="1"
            max="60"
            step="1"
            value={first}
            onChange={(ev) => setFirst(ev.target.value)}
          />
        </label>
        <label>
          Last source month
          <input
            required
            type="number"
            min="1"
            max="60"
            step="1"
            value={last}
            onChange={(ev) => setLast(ev.target.value)}
          />
        </label>
        <label>
          Exact source unit identifiers (comma or newline separated)
          <textarea
            required
            value={units}
            onChange={(ev) => setUnits(ev.target.value)}
          />
        </label>
        <label>
          Issued evidence request
          <select
            required
            value={requestId}
            onChange={(ev) => setRequestId(ev.target.value)}
          >
            <option value="">Choose a request with a scoped boundary</option>
            {eligible.map((r) => (
              <option key={r.id} value={r.id}>
                {str(r.title)} · {str(r.boundary_id)}
              </option>
            ))}
          </select>
        </label>
        <button disabled={busy || loading || !permitted}>
          Collect population and query manifest
        </button>
      </form>
      <h3>Retained collection history</h3>
      {e.requests.flatMap((r) =>
        (Array.isArray(r.company_population_collections)
          ? (r.company_population_collections as Row[])
          : []
        ).map((c) => {
          const key = `${r.id}:${str(c.snapshot_id)}`,
            next = c.next_command as
              { kind?: string; payload?: Record<string, unknown> } | undefined;
          const registered = e.populations.some(
            (p) => p.artifact_id === c.population_artifact_id,
          );
          return (
            <section key={key}>
              <h4>{str(r.title)}</h4>
              <p>
                {str(c.source_versions)} source versions ·{" "}
                {str(c.distinct_source_records)} distinct records · Collected{" "}
                {str(c.recorded_at)}
              </p>
              <p>
                Independent review: not performed. Review the query, source
                originals and boundary applicability before provisional
                registration.
              </p>
              <a href={artifactURL(e.id, str(c.manifest_artifact_id))}>
                Download query manifest
              </a>
              {" · "}
              <a href={artifactURL(e.id, str(c.population_artifact_id))}>
                Download population rows
              </a>
              <details>
                <summary>Original source versions</summary>
                <ul>
                  {(Array.isArray(c.native_artifacts)
                    ? (c.native_artifacts as Row[])
                    : []
                  ).map((a) => (
                    <li key={str(a.artifact_id)}>
                      <a href={artifactURL(e.id, str(a.artifact_id))}>
                        {str((a.source as Row)?.record)} · version{" "}
                        {str((a.source as Row)?.version)}
                      </a>
                    </li>
                  ))}
                </ul>
              </details>
              {registered ? (
                <p>
                  Registered in the population workspace; consult its current
                  reliability status.
                </p>
              ) : (
                <>
                  <label>
                    <input
                      type="checkbox"
                      checked={Boolean(reviewed[key])}
                      onChange={(ev) =>
                        setReviewed({ ...reviewed, [key]: ev.target.checked })
                      }
                    />
                    I reviewed this query and source-version sampling unit for
                    provisional registration.
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
                      if (next?.kind === "population.import" && next.payload)
                        onCommand(next.kind, next.payload);
                    }}
                  >
                    Register reviewed population as provisional
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
