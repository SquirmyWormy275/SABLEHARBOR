import { useEffect, useRef, useState } from "react";
import { request, str, type Engagement, type Row } from "./api";
export default function CompanySources({
  engagement: e,
  busy,
  onCommand,
}: {
  engagement: Engagement;
  busy: boolean;
  onCommand: (kind: string, payload: Record<string, unknown>) => void;
}) {
  const [systems, setSystems] = useState<Row[]>([]),
    [system, setSystem] = useState("");
  const [records, setRecords] = useState<Row[]>([]),
    [next, setNext] = useState<string | null>(null);
  const [requestId, setRequestId] = useState(""),
    [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const epoch = useRef(0);
  const base = `/api/engagements/${encodeURIComponent(e.id)}/company/systems`;
  useEffect(() => {
    const current = ++epoch.current;
    setRecords([]);
    setSystem("");
    setNext(null);
    setRequestId("");
    setError("");
    setSystems([]);
    setLoading(false);
    request<{ systems: Row[] }>(base)
      .then((result) => {
        if (epoch.current === current) setSystems(result.systems);
      })
      .catch((err) => {
        if (epoch.current === current) setError(err.message);
      });
    return () => {
      epoch.current++;
    };
  }, [base, e.simulated_at, JSON.stringify(e.permissions)]);
  async function browse(selected: string, after?: string) {
    const current = ++epoch.current;
    setSystem(selected);
    setError("");
    setLoading(true);
    if (!after) {
      setRecords([]);
      setNext(null);
    }
    if (!selected) {
      setLoading(false);
      return;
    }
    try {
      const q = new URLSearchParams({ limit: "50" });
      if (after) q.set("after_record", after);
      const result = await request<{
        records: Row[];
        next_after_record: string | null;
      }>(`${base}/${encodeURIComponent(selected)}/records?${q}`);
      if (current !== epoch.current) return;
      setRecords((previous) =>
        after ? [...previous, ...result.records] : result.records,
      );
      setNext(result.next_after_record);
    } catch (err) {
      if (current === epoch.current) {
        setError((err as Error).message);
        setRecords([]);
        setNext(null);
      }
    } finally {
      if (current === epoch.current) setLoading(false);
    }
  }
  const eligible = e.requests.filter((r) =>
    [
      "ISSUED",
      "ACKNOWLEDGED",
      "IN_PROGRESS",
      "CLARIFICATION",
      "SUBMITTED",
    ].includes(str(r.status)),
  );
  const canCollect = (e.permissions ?? []).some((p) =>
    ["learn", "instruct"].includes(p),
  );
  return (
    <details className="panel">
      <summary>Browse company source records</summary>
      <p>
        Read permitted company systems at the simulation date. Collect an exact
        version against an issued request; collection does not establish
        sufficient support.
      </p>
      {error && <p role="alert">{error}</p>}
      <label>
        Company system
        <select
          value={system}
          onChange={(event) => void browse(event.target.value)}
        >
          <option value="">Choose a source system</option>
          {systems.map((s) => (
            <option key={str(s.system)} value={str(s.system)}>
              {str(s.system).replaceAll("_", " ")} ·{" "}
              {str(
                e.people.find((person) => person.id === s.owner)?.name ??
                  s.owner,
              )}
            </option>
          ))}
        </select>
      </label>
      {!error && systems.length === 0 && (
        <p>
          No company systems are available through this engagement connection.
        </p>
      )}
      <label>
        Link collection to request
        <select
          value={requestId}
          onChange={(event) => setRequestId(event.target.value)}
        >
          <option value="">Choose an issued request</option>
          {eligible.map((r) => (
            <option key={r.id} value={r.id}>
              {str(r.title)} · {r.id}
            </option>
          ))}
        </select>
      </label>
      {loading && <p role="status">Reading company source index…</p>}
      {system && !loading && !error && records.length === 0 && (
        <p>
          No records available at this simulation date. Population completeness
          is not established.
        </p>
      )}
      <ul>
        {records.map((r) => {
          const provenance = (r.provenance ?? {}) as Row;
          const identity = (provenance.source_identity ?? {}) as Record<
            string,
            unknown
          >;
          const subject = Object.entries(identity)
            .filter(
              ([key, value]) =>
                key.endsWith("_id") && typeof value === "string",
            )
            .map(([, value]) => str(value))
            .join(" · ");
          return (
            <li key={`${r.record}:${r.version}`}>
              <strong>{subject || str(provenance.name ?? r.record)}</strong> ·
              Version {str(r.version)}
              <p>
                {str(identity.unit)} · Source period{" "}
                {str(provenance.source_period_start)} —{" "}
                {str(provenance.source_period_end)}
              </p>
              <p>
                Record {str(r.record)} · Event{" "}
                {r.event_at ? str(r.event_at) : "date not established"} ·
                Available {str(r.available_at)}
              </p>
              {Boolean(provenance.operational_fact_status) && (
                <p>
                  {str(provenance.operational_fact_status)
                    .replaceAll("_", " ")
                    .toLowerCase()}
                </p>
              )}
              <button
                disabled={
                  busy ||
                  loading ||
                  !canCollect ||
                  !eligible.some((x) => x.id === requestId)
                }
                onClick={() =>
                  onCommand("company.collect", {
                    system_id: system,
                    record_id: r.record,
                    version: r.version,
                    request_id: requestId,
                  })
                }
              >
                Collect this version
              </button>
            </li>
          );
        })}
      </ul>
      {next && (
        <button disabled={loading} onClick={() => void browse(system, next)}>
          Load more source records
        </button>
      )}
    </details>
  );
}
