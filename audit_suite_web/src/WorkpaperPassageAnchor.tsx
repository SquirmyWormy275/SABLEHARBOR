import { useRef, useState, useId } from "react";
import {
  ANCHOR_FIELDS,
  selectedAnchor,
  validAnchor,
  recordedAnchor,
  type AnchorVersion,
  type PassageAnchor,
} from "./workpaperAnchor";
import "./workpaperAnchor.css";
export function WorkpaperReviewAction({
  version,
  supported,
  disabled,
  onReview,
}: {
  version: AnchorVersion;
  supported: boolean;
  disabled?: boolean;
  onReview: (anchor?: PassageAnchor) => void;
}) {
  // Remount on exact version content, so stale selections cannot migrate between versions.
  return (
    <ReviewAction
      key={
        typeof version._workspace_version_sha256 === "string"
          ? `${version.version}:${version._workspace_version_sha256}`
          : JSON.stringify(version)
      }
      version={version}
      supported={supported}
      disabled={disabled}
      onReview={onReview}
    />
  );
}
function ReviewAction({
  version,
  supported,
  disabled,
  onReview,
}: {
  version: AnchorVersion;
  supported: boolean;
  disabled?: boolean;
  onReview: (anchor?: PassageAnchor) => void;
}) {
  const [anchor, setAnchor] = useState<PassageAnchor | null>(null);
  return (
    <div className="passage-anchor">
      {supported && (
        <details>
          <summary>Attach exact passage (optional)</summary>
          <WorkpaperPassageAnchor
            version={version}
            value={anchor}
            onChange={setAnchor}
            disabled={disabled}
          />
        </details>
      )}
      <button
        disabled={disabled}
        onClick={() =>
          onReview(
            supported && anchor && validAnchor(anchor, version)
              ? anchor
              : undefined,
          )
        }
      >
        Review version {String(version.version)}
      </button>
    </div>
  );
}
export function WorkpaperPassageAnchor({
  version,
  value,
  onChange,
  disabled,
}: {
  version: AnchorVersion;
  value?: PassageAnchor | null;
  onChange: (anchor: PassageAnchor | null) => void;
  disabled?: boolean;
}) {
  const id = useId(),
    area = useRef<HTMLTextAreaElement>(null);
  const fields = ANCHOR_FIELDS.filter(
    (f) => typeof version[f] === "string" && version[f] !== "",
  );
  const [field, setField] = useState<PassageAnchor["field"]>(
    fields[0] ?? "text",
  );
  const [error, setError] = useState("");
  const text = typeof version[field] === "string" ? String(version[field]) : "";
  return (
    <fieldset disabled={disabled}>
      <legend>Exact retained passage</legend>
      <label htmlFor={id}>Passage field</label>
      <select
        id={id}
        value={field}
        onChange={(e) => {
          setField(e.target.value as PassageAnchor["field"]);
          setError("");
        }}
      >
        {fields.map((f) => (
          <option key={f}>{f}</option>
        ))}
      </select>
      <label htmlFor={id + "-text"}>Select passage in retained text</label>
      <textarea id={id + "-text"} ref={area} readOnly value={text} />
      <button
        type="button"
        onClick={() => {
          const a = area.current;
          const selected =
            !text.includes("\r") &&
            a &&
            selectedAnchor(version, field, a.selectionStart, a.selectionEnd);
          if (selected) {
            onChange(selected);
            setError("");
          } else
            setError(
              "Select 1–4000 complete characters. Carriage-return text cannot be anchored here; review this version without an anchor.",
            );
        }}
      >
        Use selected passage
      </button>
      {error && <p role="alert">{error}</p>}
      {value && validAnchor(value, version) && (
        <>
          <blockquote>{value.excerpt}</blockquote>
          <p>
            {value.field} · characters {value.start}–{value.end} (Unicode code
            points)
          </p>
          <button type="button" onClick={() => onChange(null)}>
            Clear passage
          </button>
        </>
      )}
      <p>
        Only this exact version is referenced. No passage is moved to a later
        version.
      </p>
    </fieldset>
  );
}
export function ReviewPassageAnchor({ review }: { review: AnchorVersion }) {
  const a = recordedAnchor(review);
  if (!review.anchor) return null;
  if (!a)
    return (
      <p role="status">Recorded passage metadata is unavailable or invalid.</p>
    );
  return (
    <section className="passage-anchor" aria-label="Recorded review passage">
      <h3>Recorded review passage</h3>
      <p>
        Workpaper version {String(review.workpaper_version)} · {a.field} ·
        characters {a.start}–{a.end} (Unicode code points)
      </p>
      <blockquote>{a.excerpt}</blockquote>
      <p className="passage-pin">
        Version digest: {String(review.workpaper_version_digest)}
      </p>
      <p>
        This is the excerpt retained with the review, without substitution from
        a newer workpaper.
      </p>
    </section>
  );
}
