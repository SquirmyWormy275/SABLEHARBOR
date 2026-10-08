import { useState } from "react";
import "./referenceCrosswalk.css";
import type {
  ReferenceCrosswalkValue,
  ReferenceStatus,
} from "./referenceCrosswalk";

type Props = {
  value: ReferenceCrosswalkValue;
  mode: "CURRENT" | "ARCHIVE";
  selected?: string;
  onLegacy?: (id: string) => void;
  onCurrent?: (id: string) => void;
};

/** Metadata navigation only. Selecting a relation never opens original answers. */
export function ReferenceCrosswalk(props: Props) {
  return (
    <ReferenceCrosswalkContext
      key={JSON.stringify([
        props.mode,
        props.selected ?? "",
        props.value.sha256,
      ])}
      {...props}
    />
  );
}

function ReferenceCrosswalkContext({
  value,
  mode,
  selected = "",
  onLegacy,
  onCurrent,
}: Props) {
  const [query, setQuery] = useState(""),
    [status, setStatus] = useState("all"),
    [page, setPage] = useState(0);
  const q = query.trim().toLowerCase();
  const currentIndex = mode === "CURRENT" && !selected;
  const cards = new Map(value.current_cards.map((card) => [card.id, card]));
  const currentStatuses = new Map<string, Set<ReferenceStatus>>();
  for (const row of value.rows) {
    for (const relation of row.relations) {
      if (relation.current_id) {
        const statuses = currentStatuses.get(relation.current_id) ?? new Set();
        statuses.add(relation.status);
        currentStatuses.set(relation.current_id, statuses);
      }
    }
  }
  const currentRows = value.inverse.filter((row) => {
    const card = cards.get(row.current_id);
    return (
      (status === "all" ||
        (status === "UNMAPPED"
          ? row.legacy_ids.length === 0
          : currentStatuses
              .get(row.current_id)
              ?.has(status as ReferenceStatus))) &&
      (!q ||
        [
          row.current_id,
          row.unmapped_reason ?? "",
          ...(card?.control_ids ?? []),
          ...(card?.task_ids ?? []),
          ...row.legacy_ids,
        ]
          .join(" ")
          .toLowerCase()
          .includes(q))
    );
  });
  const rows = value.rows.filter(
    (r) =>
      (!selected ||
        (mode === "ARCHIVE"
          ? r.legacy_id === selected
          : r.relations.some((x) => x.current_id === selected))) &&
      (status === "all" || r.relations.some((x) => x.status === status)) &&
      (!q ||
        [
          r.legacy_id,
          ...r.relations.flatMap((x) => [
            x.current_id ?? "",
            x.status,
            x.reason,
          ]),
        ]
          .join(" ")
          .toLowerCase()
          .includes(q)),
  );
  const start = page * 20;
  const matches = currentIndex ? currentRows.length : rows.length;
  return (
    <details className="reference-crosswalk">
      <summary>Current cards and preserved reference variants</summary>
      <p>
        {value.current_cards.length} current cards · {value.rows.length}{" "}
        preserved variants. Reference variants provide context for the current
        audit. A shared control does not establish the same scenario or test
        result.
      </p>
      <details>
        <summary>About these reference links</summary>
        <p>
          The reference archive remains NOT_BOUND. EXACT requires the same
          declared episode and version; it does not establish corroboration.
          Unresolved links remain visible for review.
        </p>
        <p>
          Crosswalk version: <code>{value.sha256}</code>
        </p>
      </details>
      <div className="actions">
        <label>
          {currentIndex
            ? "Search current reference cards"
            : "Search reference links"}
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(0);
            }}
          />
        </label>
        <label>
          Relation status
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(0);
            }}
          >
            <option value="all">All relation statuses</option>
            {(
              [
                "EXACT",
                "SHARED_CONTROL_ONLY",
                "OUT_OF_SCOPE",
                "UNRESOLVED",
              ] as ReferenceStatus[]
            ).map((x) => (
              <option key={x}>{x}</option>
            ))}
            {currentIndex && (
              <option value="UNMAPPED">No declared links</option>
            )}
          </select>
        </label>
        <button
          onClick={() => {
            setQuery("");
            setStatus("all");
            setPage(0);
          }}
        >
          Clear reference filters
        </button>
      </div>
      {currentIndex ? (
        <>
          <p>
            Select a current card to inspect its declared reference links. Cards
            without links remain explicitly unmapped.
          </p>
          <p>
            {currentRows.length}{" "}
            {currentRows.length === 1
              ? "current card matches."
              : "current cards match."}
          </p>
          {!currentRows.length && (
            <p role="status">
              No current cards match. Clear filters or search by a card, control
              or procedure ID.
            </p>
          )}
          <ul>
            {currentRows.slice(start, start + 20).map((i) => (
              <li key={i.current_id}>
                <button onClick={() => onCurrent?.(i.current_id)}>
                  {i.current_id}
                </button>{" "}
                · {i.legacy_ids.length} declared links
                {cards.get(i.current_id)?.control_ids.length
                  ? ` · ${cards.get(i.current_id)!.control_ids.join(", ")}`
                  : ""}
                {i.unmapped_reason ? ` · ${i.unmapped_reason}` : ""}
              </li>
            ))}
          </ul>
        </>
      ) : (
        <>
          <p>{rows.length} reference variants match.</p>
          {!rows.length && (
            <p role="status">
              No declared reference links match. Clear filters or select another
              card.
            </p>
          )}
          <ul>
            {rows.slice(start, start + 20).map((r) => (
              <li key={r.legacy_id}>
                <button onClick={() => onLegacy?.(r.legacy_id)}>
                  {r.legacy_id}
                </button>
                <details>
                  <summary>Preserved version and relation pointers</summary>
                  <p>
                    Raw original: <code>{r.raw_sha256}</code>
                  </p>
                  <p>
                    Canonical original: <code>{r.canonical_sha256}</code>
                  </p>
                  <p>
                    Preserved explanation: <code>{r.key_sha256}</code>
                  </p>
                  <ul>
                    {r.relations.map((x, i) => (
                      <li key={i}>
                        {x.proof ? (
                          <>
                            Original <code>{x.proof.legacy_pointer}</code> ·
                            current <code>{x.proof.current_pointer}</code>
                          </>
                        ) : (
                          "No literal two-sided relation proof recorded."
                        )}
                      </li>
                    ))}
                  </ul>
                </details>
                <ul>
                  {r.relations.map((x, i) => (
                    <li key={i}>
                      {x.status}
                      {" · "}
                      {x.reason}{" "}
                      {x.current_id && (
                        <button onClick={() => onCurrent?.(x.current_id!)}>
                          Current card {x.current_id}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </>
      )}
      <div className="actions">
        <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
          {currentIndex ? "Previous current cards" : "Previous reference links"}
        </button>
        <span aria-live="polite">
          Page {page + 1} of {Math.max(1, Math.ceil(matches / 20))}
        </span>
        <button
          disabled={start + 20 >= matches}
          onClick={() => setPage((p) => p + 1)}
        >
          {currentIndex ? "Next current cards" : "Next reference links"}
        </button>
      </div>
    </details>
  );
}
