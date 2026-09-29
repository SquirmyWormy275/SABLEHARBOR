import { useEffect, useId, useRef, useState } from "react";
import { artifactURL, human, type Engagement } from "./api";
import {
  loadTextPreview,
  textPreviewAllowed,
  PREVIEW_LIMIT,
} from "./workpaperSupport";
import {
  acceptsComparison,
  comparisonArtifact,
  comparisonContext,
  comparisonOptions,
  comparisonPin,
  originalIdentity,
  type OriginalPair,
} from "./originalComparison";
import "./originalComparison.css";
type Props = {
  engagement: Engagement;
  viewerId: string;
  initialArtifactIds?: OriginalPair;
};
function OriginalPane({
  engagement: e,
  viewerId,
  id,
  side,
}: {
  engagement: Engagement;
  viewerId: string;
  id: string;
  side: string;
}) {
  const a = comparisonArtifact(e, id),
    pin = comparisonPin(e, viewerId, id);
  const [result, setResult] = useState<{
    pin: string;
    text?: string;
    error?: string;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const request = useRef<AbortController | null>(null);
  const current = useRef({ e, viewerId, id });
  current.current = { e, viewerId, id };
  useEffect(() => {
    request.current?.abort();
    setResult(null);
    setBusy(false);
    return () => request.current?.abort();
  }, [pin]);
  async function inspect() {
    if (!a) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setResult(null);
    const valid = () =>
      !controller.signal.aborted &&
      request.current === controller &&
      current.current.id === id &&
      acceptsComparison(pin, current.current.e, current.current.viewerId, id);
    try {
      const text = await loadTextPreview(e.id, a, controller.signal);
      if (valid()) setResult({ pin, text });
    } catch (error) {
      if (valid())
        setResult({
          pin,
          error:
            error instanceof Error ? error.message : "Original unavailable.",
        });
    } finally {
      if (request.current === controller) setBusy(false);
    }
  }
  if (!a)
    return (
      <p>
        Select an available retained original for the {side.toLowerCase()} side.
      </p>
    );
  const identity = originalIdentity(a),
    visible = result?.pin === pin ? result : null;
  const supported =
    textPreviewAllowed(a) &&
    typeof a.bytes === "number" &&
    a.bytes >= 0 &&
    a.bytes <= PREVIEW_LIMIT;
  return (
    <article aria-label={`${side} retained original`}>
      <h4>{String(a.name ?? a.id)}</h4>
      <p>
        {a.id}
        {identity.native.record
          ? ` · ${String(identity.native.source_store_id ?? identity.native.company ?? "")} / ${String(identity.native.system ?? "")} / ${String(identity.native.record)} v${String(identity.native.version ?? "unrecorded")}`
          : ""}
      </p>
      {identity.routeStatus.startsWith("Incomplete") && (
        <p>{identity.routeStatus}</p>
      )}
      {identity.native.portfolio_qualification !== undefined && (
        <p>{human(identity.native.portfolio_qualification)}</p>
      )}
      <details>
        <summary>Exact identity and coverage</summary>
        <dl>
          <dt>Retained artifact</dt>
          <dd>{a.id}</dd>
          <dt>SHA-256</dt>
          <dd>{String(a.sha256)}</dd>
          <dt>Retained version</dt>
          <dd>{String(a.version ?? "Not separately recorded")}</dd>
          <dt>Size</dt>
          <dd>{String(a.bytes)} bytes</dd>
        </dl>
        {Object.keys(identity.native).length > 0 && (
          <>
            <p>{identity.routeStatus}</p>
            <dl>
              {[
                "company",
                "branch",
                "system",
                "record",
                "version",
                "sha256",
                "source_store_id",
                "source_system_alias",
                "registry_sha256",
                "portfolio_qualification",
                "origin",
              ]
                .filter((k) => identity.native[k] !== undefined)
                .map((k) => (
                  <div key={k}>
                    <dt>{k.replaceAll("_", " ")}</dt>
                    <dd>{String(identity.native[k])}</dd>
                  </div>
                ))}
            </dl>
          </>
        )}
        <p>Recorded coverage: {JSON.stringify(a.coverage ?? "Not recorded")}</p>
      </details>
      {supported ? (
        <button type="button" onClick={inspect} disabled={busy}>
          {busy ? "Loading original…" : `Load ${side.toLowerCase()} original`}
        </button>
      ) : (
        <p>
          Inline inspection unavailable for this format or size. Download the
          exact original.
        </p>
      )}
      <a href={artifactURL(e.id, a.id)} download>
        Download {side.toLowerCase()} original
      </a>
      <div role="status" aria-live="polite">
        {busy
          ? "Loading and verifying retained bytes."
          : (visible?.error ??
            (visible?.text !== undefined
              ? "Exact retained bytes verified."
              : ""))}
      </div>
      {visible?.text !== undefined && (
        <pre tabIndex={0} aria-label={`${side} original content`}>
          {visible.text}
        </pre>
      )}
    </article>
  );
}
export default function OriginalComparison({
  engagement,
  viewerId,
  initialArtifactIds = ["", ""],
}: Props) {
  const context = comparisonContext(engagement, viewerId),
    label = useId();
  const [selection, setSelection] = useState<{
    context: string;
    ids: OriginalPair;
  }>(() => ({ context, ids: initialArtifactIds }));
  const [search, setSearch] = useState<[string, string]>(["", ""]);
  const ids: OriginalPair =
    selection.context === context ? selection.ids : ["", ""];
  useEffect(() => {
    if (selection.context !== context) {
      setSelection({ context, ids: ["", ""] });
      setSearch(["", ""]);
    }
  }, [context, selection.context]);
  const matches = ids.map((id, index) =>
    comparisonOptions(
      engagement,
      selection.context === context ? search[index] : "",
      id,
    ),
  );

  return (
    <section className="original-comparison" aria-labelledby={label}>
      <h3 id={label}>Compare two retained originals</h3>
      <p>
        Compare exact retained files side by side. Choose each file, then load
        its contents. Text preview limit: 1 MiB per file.
      </p>
      <div className="original-comparison-columns">
        {(["Left", "Right"] as const).map((side, index) => (
          <section key={side}>
            <label>
              {side} file search
              <input
                aria-label={`${side} file search`}
                value={selection.context === context ? search[index] : ""}
                onChange={(event) => {
                  const next: [string, string] = [...search];
                  next[index] = event.target.value;
                  setSearch(next);
                }}
              />
            </label>
            <p>
              {matches[index].total} matching{" "}
              {matches[index].total === 1 ? "file" : "files"}.
              {matches[index].total > 50 &&
                " Showing the first 50 matches plus the selected file. Refine your search to see more."}
            </p>
            <label>
              {side} original
              <select
                aria-label={`${side} original`}
                value={
                  comparisonArtifact(engagement, ids[index]) ? ids[index] : ""
                }
                onChange={(event) => {
                  const next: [string, string] = [...ids];
                  next[index] = event.target.value;
                  setSelection({ context, ids: next });
                }}
              >
                <option value="">Choose retained original</option>
                {matches[index].options.map((a) => (
                  <option key={a.id} value={a.id}>
                    {String(a.name ?? a.id)} · {a.id}
                  </option>
                ))}
              </select>
            </label>
            <OriginalPane
              engagement={engagement}
              viewerId={viewerId}
              id={ids[index]}
              side={side}
            />
          </section>
        ))}
      </div>
      {ids[0] && ids[0] === ids[1] && (
        <p role="status">
          Both sides select the same retained artifact; this is not independent
          corroboration.
        </p>
      )}
    </section>
  );
}
