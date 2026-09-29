import { useState } from "react";
import { normalize, request, str, type Engagement } from "./api";
export default function SelectionImport({
  engagement: e,
  onSaved,
}: {
  engagement: Engagement;
  onSaved: (e: Engagement) => void;
}) {
  const [population, setPopulation] = useState(""),
    [kind, setKind] = useState("selection"),
    [purpose, setPurpose] = useState(""),
    [rationale, setRationale] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <details className="panel">
      <summary>
        Import selected IDs or revise a population from an original
      </summary>
      <label>
        Import purpose
        <select value={kind} onChange={(v) => setKind(v.target.value)}>
          <option value="selection">Manual selected IDs</option>
          <option value="population_revision">
            New immutable population version
          </option>
        </select>
      </label>
      <p>
        UTF-8 text or one-column CSV, one exact supplied population ID per row.
        This records a manual selection and retains the original file; it does
        not establish statistical representativeness.
      </p>
      {kind === "population_revision" && (
        <p>
          Upload a UTF-8 CSV with distinct column names including id. The new
          version preserves its predecessor and existing selections remain
          linked to their original version.
        </p>
      )}
      <label>
        Population version
        <select
          value={population}
          onChange={(v) => setPopulation(v.target.value)}
        >
          <option value="">Select population</option>
          {e.populations.map((p) => (
            <option key={p.id} value={p.id}>
              {str(p.title)} · version {str(p.version)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Selection purpose / source query and completeness representation
        <input value={purpose} onChange={(v) => setPurpose(v.target.value)} />
      </label>
      <label>
        Methodology and rationale
        <textarea
          value={rationale}
          onChange={(v) => setRationale(v.target.value)}
        />
      </label>
      <label>
        Original source file
        <input
          type="file"
          accept={kind === "selection" ? ".txt,.csv" : ".csv"}
          disabled={busy || !population || !purpose.trim() || !rationale.trim()}
          onChange={async (v) => {
            const file = v.target.files?.[0];
            if (!file) return;
            setBusy(true);
            setError("");
            try {
              const data = new FormData();
              data.set("file", file);
              data.set("kind", kind);
              data.set("linked_id", population);
              data.set("purpose", purpose);
              data.set("rationale", rationale);
              data.set("expected_revision", String(e.revision));
              data.set("command_id", crypto.randomUUID());
              onSaved(
                normalize(
                  await request<Engagement>(
                    `/api/engagements/${e.id}/uploads`,
                    "POST",
                    data,
                  ),
                ),
              );
            } catch (ex) {
              setError((ex as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        />
      </label>
      {busy && <p role="status">Validating and retaining original…</p>}
      {error && <p role="alert">{error}</p>}
    </details>
  );
}
