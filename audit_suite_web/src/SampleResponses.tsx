import { useState } from "react";
import { str, type Engagement } from "./api";
export default function SampleResponses({
  engagement: e,
  busy,
  onCommand,
}: {
  engagement: Engagement;
  busy: boolean;
  onCommand: (kind: string, payload: Record<string, unknown>) => void;
}) {
  const [selected, setSelected] = useState(""),
    [items, setItems] = useState<
      Record<
        string,
        { status: string; rationale: string; artifact_ids: string[] }
      >
    >({});
  const selection = e.selections.find((s) => s.id === selected);
  const ids = [
    ...((selection?.selected_ids ?? []) as string[]),
    ...((selection?.targeted_ids ?? []) as string[]),
  ];
  const ready =
    ids.length > 0 &&
    ids.every(
      (id) =>
        items[id]?.rationale.trim() &&
        (items[id].status !== "DELIVERED" || items[id].artifact_ids.length),
    );
  return (
    <details className="panel">
      <summary>Record item-by-item support dispositions</summary>
      <p>
        Support delivery is distinct from the test conclusion. Each submission
        is retained separately.
      </p>
      <label>
        Selection
        <select
          value={selected}
          onChange={(v) => {
            setSelected(v.target.value);
            setItems({});
          }}
        >
          <option value="">Select sample</option>
          {e.selections.map((s) => (
            <option key={s.id} value={s.id}>
              {s.id} · {str(s.purpose)}
            </option>
          ))}
        </select>
      </label>
      {ids.map((id) => {
        const value = items[id] ?? {
          status: "AWAITING_CLARIFICATION",
          rationale: "",
          artifact_ids: [],
        };
        const update = (patch: Partial<typeof value>) =>
          setItems({ ...items, [id]: { ...value, ...patch } });
        return (
          <fieldset key={id}>
            <legend>{id}</legend>
            <label>
              Disposition
              <select
                value={value.status}
                onChange={(v) => update({ status: v.target.value })}
              >
                {[
                  "DELIVERED",
                  "PARTIAL",
                  "REFUSED",
                  "UNAVAILABLE",
                  "AWAITING_CLARIFICATION",
                ].map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
            <label>
              Rationale
              <input
                value={value.rationale}
                onChange={(v) => update({ rationale: v.target.value })}
              />
            </label>
            <label>
              Available supporting artifact IDs
              <input
                value={value.artifact_ids.join(", ")}
                onChange={(v) =>
                  update({
                    artifact_ids: v.target.value
                      .split(/[\s,]+/)
                      .filter(Boolean),
                  })
                }
              />
            </label>
          </fieldset>
        );
      })}
      <button
        disabled={busy || !ready}
        onClick={() =>
          onCommand("selection.dispositions", {
            selection_id: selected,
            dispositions: items,
          })
        }
      >
        Record support dispositions
      </button>
    </details>
  );
}
