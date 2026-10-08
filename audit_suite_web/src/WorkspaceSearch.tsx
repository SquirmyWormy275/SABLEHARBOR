import { useEffect, useRef, useState } from "react";
import type { Engagement, Row } from "./api";
import {
  searchWorkspace,
  resolveSearchHit,
  searchContext,
  searchKinds,
  type SearchKind,
  type SearchHit,
} from "./workspaceSearch";
export type WorkspaceSearchProps = {
  engagement: Engagement;
  viewerId: string;
  onPreview: (kind: SearchKind, row: Row) => void;
  onOpenRecord: (hit: SearchHit) => void;
};
/** Context-keyed local search. No new API, persistent storage, model or global index. */
export default function WorkspaceSearch(props: WorkspaceSearchProps) {
  return (
    <ScopedSearch
      key={searchContext(props.engagement, props.viewerId)}
      {...props}
    />
  );
}
function ScopedSearch({
  engagement: e,
  onPreview,
  onOpenRecord,
}: WorkspaceSearchProps) {
  const [query, setQuery] = useState(""),
    [kind, setKind] = useState<SearchKind | "all">("all"),
    [submitted, setSubmitted] = useState("");
  const disclosure = useRef<HTMLDetailsElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    function shortcut(event: KeyboardEvent) {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "k" &&
        !document.querySelector("dialog[open]")
      ) {
        event.preventDefault();
        if (disclosure.current) disclosure.current.open = true;
        searchInput.current?.focus();
      }
    }
    window.addEventListener("keydown", shortcut);
    return () => window.removeEventListener("keydown", shortcut);
  }, []);
  const groups = searchWorkspace(e, submitted, kind),
    count = groups.reduce((total, g) => total + g.total, 0);
  return (
    <section className="workspace-search" aria-label="Search this engagement">
      <details ref={disclosure}>
        <summary>
          Find related work <kbd>Ctrl/⌘ K</kbd>
        </summary>
        <p>Search the records available in this engagement.</p>
        <form
          className="actions"
          onSubmit={(event) => {
            event.preventDefault();
            setSubmitted(query.trim());
          }}
        >
          <label>
            Search this engagement
            <input
              ref={searchInput}
              type="search"
              maxLength={200}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label>
            Record type
            <select
              value={kind}
              onChange={(event) =>
                setKind(event.target.value as SearchKind | "all")
              }
            >
              <option value="all">All record types</option>
              {Object.entries(searchKinds).map(([id, spec]) => (
                <option key={id} value={id}>
                  {spec.label}
                </option>
              ))}
            </select>
          </label>
          <button type="submit">Search records</button>
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setSubmitted("");
              setKind("all");
            }}
          >
            Reset search
          </button>
        </form>
        <p role="status">
          {submitted
            ? `${count} matching records for “${submitted}”${kind === "all" ? "" : ` in ${searchKinds[kind].label}`}.`
            : "Enter an identifier, name or phrase to search accessible work."}
        </p>
        {submitted && !count && (
          <p>
            No matches in the current authorized records and selected type.
            Reset the filters or change the search. Unavailable evidence and
            other engagements are not searched.
          </p>
        )}
        {groups.map((group) => (
          <section
            key={group.kind}
            aria-label={`${group.label} search results`}
          >
            <h3>
              {group.label} ({group.total})
            </h3>
            {group.total > group.hits.length && (
              <p>
                Showing the first {group.hits.length} matches. Refine your query
                to narrow the results.
              </p>
            )}
            <ul>
              {group.hits.map((hit) => (
                <li key={hit.id}>
                  <strong>{hit.title}</strong> <code>{hit.id}</code>
                  <p>{hit.snippet}</p>
                  <button
                    type="button"
                    onClick={() => {
                      const row = resolveSearchHit(e, hit);
                      if (row) onPreview(hit.kind, row);
                    }}
                  >
                    Preview {hit.id}
                  </button>{" "}
                  <button
                    type="button"
                    onClick={() => {
                      if (resolveSearchHit(e, hit)) onOpenRecord(hit);
                    }}
                  >
                    Open record {hit.id}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </details>
    </section>
  );
}
