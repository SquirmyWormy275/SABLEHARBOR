import { useEffect, useRef, useState } from "react";
import { request, str, type Engagement, type Row } from "./api";
import {
  ownedSystems,
  sourcePin,
  addSourcePin,
  type SourcePin,
} from "./meetingSources";
export function MeetingSourceContext({
  engagement: e,
  personId,
  pins,
  onChange,
}: {
  engagement: Engagement;
  personId: string;
  pins: SourcePin[];
  onChange: (pins: SourcePin[]) => void;
}) {
  const [systems, setSystems] = useState<Row[]>([]),
    [system, setSystem] = useState(""),
    [rows, setRows] = useState<Row[]>([]),
    [registry, setRegistry] = useState(""),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false),
    [next, setNext] = useState<string | null>(null);
  const epoch = useRef(0),
    base = `/api/engagements/${encodeURIComponent(e.id)}/company/systems`;
  useEffect(() => {
    ++epoch.current;
    return () => {
      epoch.current++;
    };
  }, []);
  async function loadSystems() {
    const n = ++epoch.current;
    setLoading(true);
    setError("");
    setRows([]);
    setSystem("");
    setNext(null);
    try {
      const value = await request<{ systems: Row[]; registry_sha256?: string }>(
        base,
      );
      if (n !== epoch.current) return;
      const pin = value.registry_sha256 ?? "";
      if (registry !== pin && pins.length) {
        onChange([]);
        setError(
          "The source registry changed. Select records again; your question is unchanged.",
        );
      }
      setRegistry(pin);
      const owned = ownedSystems(value.systems, personId);
      setSystems(owned);
      if (pins.some((p) => !owned.some((s) => s.system === p.system_id))) {
        onChange([]);
        setError("Source ownership or access changed. Select records again.");
      }
    } catch (err) {
      if (n === epoch.current) {
        setError((err as Error).message);
        setSystems([]);
        onChange([]);
      }
    } finally {
      if (n === epoch.current) setLoading(false);
    }
  }
  async function loadRecords(after?: string) {
    if (!systems.some((s) => s.system === system)) return;
    const n = ++epoch.current;
    setLoading(true);
    setError("");
    if (!after) setRows([]);
    try {
      const q = new URLSearchParams({ limit: "50" });
      if (after) q.set("after_record", after);
      const value = await request<{
        records: Row[];
        registry_sha256?: string;
        next_after_record: string | null;
      }>(`${base}/${encodeURIComponent(system)}/records?${q}`);
      if (n !== epoch.current) return;
      if (
        (value.registry_sha256 ?? "") !== registry ||
        value.records.some((r) => !sourcePin(r, system, registry))
      ) {
        onChange([]);
        throw Error(
          "Source identity changed or is unavailable. Reload systems and reselect records.",
        );
      }
      setRows((old) => (after ? [...old, ...value.records] : value.records));
      setNext(value.next_after_record);
    } catch (err) {
      if (n === epoch.current) {
        setRows([]);
        setNext(null);
        setError((err as Error).message);
      }
    } finally {
      if (n === epoch.current) setLoading(false);
    }
  }
  return (
    <details className="panel">
      <summary>Choose exact company records for this question</summary>
      <p>
        Optional: select up to four records owned by this meeting participant.
        Without a selection, the company uses its bounded automatic source
        sample. Selection supplies source context, not a testing conclusion.
      </p>
      <button
        type="button"
        disabled={loading}
        onClick={() => void loadSystems()}
      >
        Load participant's source systems
      </button>
      {error && <p role="alert">{error}</p>}
      {loading && <p role="status">Loading source metadata…</p>}
      {systems.length > 0 && (
        <>
          <label>
            Participant source system
            <select
              aria-label="Participant source system"
              value={system}
              onChange={(event) => {
                epoch.current++;
                setLoading(false);
                setSystem(event.target.value);
                setRows([]);
                setNext(null);
              }}
            >
              <option value="">Choose system</option>
              {systems.map((s) => (
                <option key={str(s.system)} value={str(s.system)}>
                  {str(s.system)}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={!system || loading}
            onClick={() => void loadRecords()}
          >
            Load source records
          </button>
        </>
      )}
      <ul>
        {rows.map((row) => {
          const pin = sourcePin(row, system, registry);
          return (
            <li key={`${row.record}:${row.version}`}>
              <span>
                Original source: {str(row.company)} / {str(row.branch)} /{" "}
                {str(row.system)} / {str(row.record)} · Version{" "}
                {str(row.version)}
              </span>
              <p>
                SHA256 <code>{str(row.sha256)}</code>
              </p>
              <button
                type="button"
                disabled={
                  !pin ||
                  loading ||
                  pins.length >= 4 ||
                  pins.some(
                    (p) => p.system_id === system && p.record_id === row.record,
                  )
                }
                onClick={() => {
                  if (pin)
                    try {
                      onChange(addSourcePin(pins, pin));
                    } catch (err) {
                      setError((err as Error).message);
                    }
                }}
              >
                Use record {str(row.record)} version {str(row.version)}
              </button>
            </li>
          );
        })}
      </ul>
      {next && (
        <button
          type="button"
          disabled={loading}
          onClick={() => void loadRecords(next)}
        >
          Load more source records
        </button>
      )}
      <p>{pins.length} explicit source records selected</p>
      <ul>
        {pins.map((p, index) => (
          <li key={`${p.system_id}:${p.record_id}`}>
            {p.system_id} / {p.record_id} · Version {p.version} · SHA256{" "}
            <code>{p.sha256}</code>
            <button
              type="button"
              onClick={() => onChange(pins.filter((_, i) => i !== index))}
            >
              Remove source {p.record_id}
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}
