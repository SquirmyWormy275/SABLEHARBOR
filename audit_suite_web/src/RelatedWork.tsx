import { useId } from "react";
import type { Engagement } from "./api";
import {
  relatedWork,
  resolveRelatedWork,
  type RelatedWorkReference,
} from "./relatedWork";
import "./evidenceContext.css";
export type RelatedWorkNavigation = {
  query: string;
  limits: Record<string, number>;
};

/** Read-only relationship navigation alongside the existing inspector. */
export function RelatedWork({
  engagement: e,
  kind,
  objectId,
  onOpen,
  navigation,
  onNavigationChange,
}: {
  engagement: Engagement;
  kind: "control" | "task";
  objectId: string;
  onOpen: (reference: RelatedWorkReference) => void;
  navigation: RelatedWorkNavigation;
  onNavigationChange: (value: RelatedWorkNavigation) => void;
}) {
  const headingId = useId();
  const { query, limits } = navigation;
  const context = relatedWork(e, kind, objectId);
  if (!context) return <p>Related work is unavailable in the current scope.</p>;
  const q = query.trim().toLocaleLowerCase();
  const groups = context.groups.map((group) => ({
    ...group,
    matching: group.links.filter((item) =>
      [item.reference.id, item.title].some((value) =>
        value.toLocaleLowerCase().includes(q),
      ),
    ),
  }));
  const total = groups.reduce((count, group) => count + group.links.length, 0);
  const matched = groups.reduce(
    (count, group) => count + group.matching.length,
    0,
  );
  const emptyGroups = groups.filter(
    (group) =>
      !group.links.length && !["control", "workpapers"].includes(group.id),
  );
  return (
    <aside
      className="evidence-context related-work"
      aria-labelledby={headingId}
    >
      <h3 id={headingId}>
        Related work for {kind === "task" ? "procedure" : "control"} {objectId}
      </h3>
      <p>
        Engagement: {e.title} · {e.id}
      </p>
      <p>
        These are recorded relationships in your current scope. Shared control
        context does not establish support for this procedure. Workpaper links
        open the exact referenced version; no other version is substituted.
      </p>
      <label>
        Filter related work
        <input
          type="search"
          maxLength={200}
          value={query}
          onChange={(event) => {
            onNavigationChange({ query: event.target.value, limits: {} });
          }}
        />
      </label>{" "}
      <button
        type="button"
        onClick={() => {
          onNavigationChange({ query: "", limits: {} });
        }}
      >
        Reset related filter
      </button>
      <p role="status">
        {matched} of {total} recorded links
        {q ? ` match “${query.trim()}”` : " available"}.
      </p>
      {q && !matched && (
        <p>
          No related records match this filter. Reset the filter to see the
          recorded links.
        </p>
      )}
      {groups
        .filter(
          (group) =>
            group.matching.length ||
            (!q && ["control", "workpapers"].includes(group.id)),
        )
        .map((group) => (
          <section key={group.id} aria-label={group.title}>
            <h4>
              {group.title} ({group.matching.length})
            </h4>
            {group.matching.length ? (
              <>
                <ul>
                  {group.matching
                    .slice(0, limits[group.id] ?? 10)
                    .map((item) => (
                      <li
                        key={
                          item.reference.id +
                          ":" +
                          (item.reference.version ?? "")
                        }
                      >
                        <button
                          type="button"
                          onClick={() => {
                            if (resolveRelatedWork(e, item.reference))
                              onOpen(item.reference);
                          }}
                        >
                          Open {item.reference.id}
                          {item.reference.version !== undefined
                            ? ` · version ${item.reference.version}`
                            : ""}
                        </button>
                        <p>{item.title}</p>
                        <p>{item.reason}</p>
                      </li>
                    ))}
                </ul>
                {group.matching.length > (limits[group.id] ?? 10) && (
                  <button
                    type="button"
                    onClick={() =>
                      onNavigationChange({
                        query,
                        limits: {
                          ...limits,
                          [group.id]: (limits[group.id] ?? 10) + 10,
                        },
                      })
                    }
                  >
                    Show more {group.title.toLocaleLowerCase()}
                  </button>
                )}
              </>
            ) : (
              <p>
                {q
                  ? "No matches under the current filter."
                  : "No explicit available links are recorded in this scope. This is not an adverse conclusion."}
              </p>
            )}
          </section>
        ))}
      {!q && emptyGroups.length > 0 && (
        <details>
          <summary>
            Other groups without available recorded links ({emptyGroups.length})
          </summary>
          <ul>
            {emptyGroups.map((group) => (
              <li key={group.id}>{group.title}</li>
            ))}
          </ul>
          <p>
            This view does not establish that company records or relevant
            evidence do not exist.
          </p>
        </details>
      )}
    </aside>
  );
}
