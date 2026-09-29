import { useEffect, useId, useRef, useState } from "react";
import { type InstructorIndex, type KeyEntry } from "./instructorKey";
import {
  loadInstructorOriginal,
  originalKeyOptions,
} from "./instructorOriginal";
import "./originalComparison.css";
export function InstructorOriginalInspection(props: {
  index: InstructorIndex;
  initialId: string;
}) {
  const [open, setOpen] = useState(false),
    id = useId();
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((value) => !value)}
      >
        {open
          ? "Close original source inspection"
          : "Inspect original source versions side by side"}
      </button>
      <div id={id}>{open && <InstructorOriginals {...props} />}</div>
    </div>
  );
}
function OriginalPane({
  entry,
  side,
  engagementId,
  archive,
}: {
  entry?: KeyEntry;
  side: string;
  engagementId: string;
  archive: string;
}) {
  const [result, setResult] = useState<{ text: string; bytes: number } | null>(
    null,
  );
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  async function load() {
    if (!entry) return;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setResult(null);
    setError("");
    setBusy(true);
    try {
      const value = await loadInstructorOriginal(
        entry,
        engagementId,
        archive,
        controller.signal,
      );
      if (!controller.signal.aborted) setResult(value);
    } catch (e) {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "Original unavailable.");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  if (!entry) return <p>Choose an archived source for this side.</p>;
  return (
    <article aria-label={`${side} archived source`}>
      <p>{entry.id}</p>
      <details>
        <summary>Exact source identity</summary>
        <dl>
          <dt>Original SHA-256</dt>
          <dd>{entry.raw_sha256}</dd>
          <dt>Canonical source SHA-256</dt>
          <dd>{entry.canonical_sha256}</dd>
          <dt>Migrated explanation SHA-256</dt>
          <dd>{entry.key_sha256}</dd>
        </dl>
      </details>
      <button type="button" disabled={busy} onClick={() => void load()}>
        {busy
          ? "Verifying original…"
          : `Load ${side.toLowerCase()} archived original`}
      </button>
      <p role="status">
        {busy
          ? "Loading protected original bytes."
          : error ||
            (result
              ? `Exact original verified · ${result.bytes} bytes`
              : "Contents load only when requested.")}
      </p>
      {result && (
        <pre tabIndex={0} aria-label={`${side} archived original content`}>
          {result.text}
        </pre>
      )}
    </article>
  );
}
export function InstructorOriginals({
  index,
  initialId,
}: {
  index: InstructorIndex;
  initialId: string;
}) {
  const [ids, setIds] = useState<[string, string]>([initialId, ""]);
  const [queries, setQueries] = useState<[string, string]>(["", ""]);
  return (
    <section
      className="original-comparison"
      aria-label="Inspect archived source versions"
    >
      <h3>Inspect original source versions</h3>
      <p>
        Choose two archived definitions and load their exact text side by side.
        Selection does not establish a revision lineage, active scenario, or
        independent corroboration. Up to 4 MiB per source.
      </p>
      <div className="original-comparison-columns">
        {["Left", "Right"].map((side, i) => {
          const matches = originalKeyOptions(index.entries, queries[i], ids[i]);
          const entry = index.entries.find((e) => e.id === ids[i]);
          return (
            <section key={side}>
              <label>
                {side} archived source search
                <input
                  value={queries[i]}
                  onChange={(e) => {
                    const next: [string, string] = [...queries];
                    next[i] = e.target.value;
                    setQueries(next);
                  }}
                />
              </label>
              <p>
                {matches.total} matching sources.
                {matches.total > 50 &&
                  " Showing the first 50 plus your selected source; refine the search for more."}
              </p>
              <label>
                {side} archived source
                <select
                  value={ids[i]}
                  onChange={(e) => {
                    const next: [string, string] = [...ids];
                    next[i] = e.target.value;
                    setIds(next);
                  }}
                >
                  <option value="">Choose archived source</option>
                  {matches.options.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.id}
                    </option>
                  ))}
                </select>
              </label>
              <OriginalPane
                key={JSON.stringify([
                  index.binding.engagement_id,
                  index.archive.sha256,
                  entry,
                ])}
                entry={entry}
                side={side}
                engagementId={index.binding.engagement_id}
                archive={index.archive.sha256}
              />
            </section>
          );
        })}
      </div>
      {ids[0] && ids[0] === ids[1] && (
        <p role="status">Both sides select the same archived original.</p>
      )}
    </section>
  );
}
