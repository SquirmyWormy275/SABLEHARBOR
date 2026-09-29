import { useState } from "react";
import { str, type Engagement } from "./api";
export default function ParentSupport({
  engagement: e,
  busy,
  onCommand,
}: {
  engagement: Engagement;
  busy: boolean;
  onCommand: (kind: string, payload: Record<string, unknown>) => void;
}) {
  const [kind, setKind] = useState("sites"),
    [control, setControl] = useState(""),
    [boundary, setBoundary] = useState(""),
    [parent, setParent] = useState(""),
    [purpose, setPurpose] = useState(""),
    [rationale, setRationale] = useState("");
  const controls = e.controls.filter((c) =>
    ["SH-ARU-001", "SH-AST-001"].includes(c.id),
  );
  const ready =
    purpose.trim() &&
    rationale.trim() &&
    (kind === "sites" ? control && boundary : parent);
  return (
    <details className="panel">
      <summary>Request linked company source records</summary>
      <p>
        Move from a company site population to selected-site movement tickets,
        then underlying support for selected tickets. Each request uses the
        exact retained parent selection. Issue the resulting draft request in
        PBC to receive available original records.
      </p>
      <label>
        Requested source
        <select value={kind} onChange={(v) => setKind(v.target.value)}>
          <option value="sites">Company sites</option>
          <option value="tickets">Moving tickets for selected sites</option>
          <option value="support">
            Underlying support for selected tickets
          </option>
        </select>
      </label>
      {kind === "sites" ? (
        <>
          <label>
            Scoped site or industrial asset control
            <select
              value={control}
              onChange={(v) => setControl(v.target.value)}
            >
              <option value="">Select supported control</option>
              {controls.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} · {str(c.title)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Scoped boundary
            <select
              value={boundary}
              onChange={(v) => setBoundary(v.target.value)}
            >
              <option value="">Select boundary</option>
              {e.scope.boundaries.map((b) => (
                <option key={b}>{b}</option>
              ))}
            </select>
          </label>
          {!controls.length && (
            <p>
              Add the relevant site or industrial asset control to scope before
              requesting this source.
            </p>
          )}
        </>
      ) : (
        <label>
          Exact parent selection
          <select value={parent} onChange={(v) => setParent(v.target.value)}>
            <option value="">Select parent</option>
            {e.selections.map((s) => (
              <option key={s.id} value={s.id}>
                {s.id} · {str(s.purpose)}
              </option>
            ))}
          </select>
        </label>
      )}
      <label>
        Request purpose
        <textarea
          value={purpose}
          onChange={(v) => setPurpose(v.target.value)}
        />
      </label>
      <label>
        Selection and source rationale
        <textarea
          value={rationale}
          onChange={(v) => setRationale(v.target.value)}
        />
      </label>
      <button
        disabled={busy || !ready}
        onClick={() =>
          onCommand("population.request_support", {
            support_kind: kind,
            purpose,
            rationale,
            ...(kind === "sites"
              ? { control_id: control, boundary_id: boundary }
              : { parent_selection_id: parent }),
          })
        }
      >
        Create linked source request
      </button>
    </details>
  );
}
