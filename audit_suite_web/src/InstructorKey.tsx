import { InstructorKeyViews } from "./InstructorKeyViews";
import { ReferenceCrosswalk } from "./ReferenceCrosswalk";
import { InstructorRelationshipExplorer } from "./InstructorRelationshipExplorer";
import { InstructorOriginalInspection } from "./InstructorOriginals";
import {
  validateArchiveFilters,
  type ArchiveKeyFilters,
} from "./instructorKeyViews";
import { useEffect, useRef, useState } from "react";
import { request, type Engagement } from "./api";
import {
  assertKeyContext,
  assertKeyDetail,
  authoredMatchIds,
  filterKeys,
  keyOption,
  keySelector,
  type InstructorIndex,
  type InstructorDetail,
  type KeyEntry,
  type AuthoredMatchResult,
} from "./instructorKey";
function Value({ value }: { value: unknown }) {
  if (value == null) return <span>Not authored</span>;
  if (Array.isArray(value))
    return (
      <ul>
        {value.map((v, i) => (
          <li key={i}>
            <Value value={v} />
          </li>
        ))}
      </ul>
    );
  if (typeof value === "object")
    return (
      <dl>
        {Object.entries(value).map(([k, v]) => (
          <div key={k}>
            <dt>{k.replaceAll("_", " ")}</dt>
            <dd>
              <Value value={v} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return <span>{String(value)}</span>;
}
/** Protected source library; saved filter metadata uses the separate instructor-only store. */
type InstructorKeyProps = {
  engagement: Engagement;
  viewerId?: string;
  savedViewsEnabled?: boolean;
  referenceLegacy?: string;
  onReferenceCurrent?: (id: string) => void;
};
export default function InstructorKey(props: InstructorKeyProps) {
  return (
    <ArchiveExplorer
      key={JSON.stringify([
        props.viewerId,
        props.engagement.id,
        props.engagement.permissions,
        props.engagement.revision,
        props.engagement.scope,
        props.engagement.company_source_binding,
        props.engagement.evidence_acquisition,
      ])}
      {...props}
    />
  );
}
function ArchiveExplorer({
  engagement,
  viewerId = "",
  savedViewsEnabled = false,
  referenceLegacy,
  onReferenceCurrent,
}: {
  engagement: Engagement;
  viewerId?: string;
  savedViewsEnabled?: boolean;
  referenceLegacy?: string;
  onReferenceCurrent?: (id: string) => void;
}) {
  const [index, setIndex] = useState<InstructorIndex | null>(null),
    [detail, setDetail] = useState<InstructorDetail | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false),
    [selected, setSelected] = useState("");
  const [query, setQuery] = useState(""),
    [selector, setSelector] = useState("all"),
    [option, setOption] = useState("all"),
    [review, setReview] = useState("all"),
    [reviewFacets, setReviewFacets] = useState<{
      causal_validation: string | null;
      grading: string | null;
    }>({ causal_validation: null, grading: null }),
    [page, setPage] = useState(0);
  const sequence = useRef(0),
    allowed = (engagement.permissions ?? []).includes("instruct");
  const searchSequence = useRef(0);
  const searchFilters = useRef({
    selector,
    option,
    review,
    review_facets: reviewFacets,
    page,
  });
  searchFilters.current = {
    selector,
    option,
    review,
    review_facets: reviewFacets,
    page,
  };
  const [matchReceipt, setMatchReceipt] = useState<{
      query: string;
      archive: string;
      ids: string[];
    } | null>(null),
    [searchError, setSearchError] = useState("");
  const completeIds =
    matchReceipt?.query === query &&
    matchReceipt.archive === index?.archive.sha256
      ? matchReceipt.ids
      : undefined;
  const searchPending = Boolean(
    index?.semantic_matching &&
    query.trim() &&
    completeIds === undefined &&
    !searchError,
  );
  useEffect(() => {
    const current = ++searchSequence.current;
    setMatchReceipt(null);
    setSearchError("");
    if (!allowed || !index?.semantic_matching || !query.trim()) return;
    const timer = setTimeout(() => {
      void request<AuthoredMatchResult>(
        `/api/engagements/${encodeURIComponent(engagement.id)}/instructor-key?query=${encodeURIComponent(query)}`,
      )
        .then((value) => {
          if (current !== searchSequence.current) return;
          const ids = authoredMatchIds(value, index, query);
          const currentFilters = searchFilters.current;
          const count = filterKeys(index.entries, {
            query,
            ...currentFilters,
            complete_match_ids: ids,
          }).length;
          if (currentFilters.page >= Math.max(1, Math.ceil(count / 25)))
            throw Error(
              "Saved archive page is outside the complete query results.",
            );
          setMatchReceipt({ query, archive: index.archive.sha256, ids });
        })
        .catch((error) => {
          if (current === searchSequence.current) setSearchError(error.message);
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      ++searchSequence.current;
    };
  }, [index, query, allowed, engagement.id]);
  useEffect(() => {
    if (
      referenceLegacy &&
      index?.entries.some((x) => x.id === referenceLegacy)
    ) {
      sequence.current++;
      setDetail(null);
      setSelected("");
      setLoading(false);
      setQuery(referenceLegacy);
      setSelector("all");
      setOption("all");
      setReview("all");
      setReviewFacets({ causal_validation: null, grading: null });
      setPage(0);
    }
  }, [referenceLegacy, index]);
  useEffect(() => {
    const current = ++sequence.current;
    setIndex(null);
    setDetail(null);
    setError("");
    setSelected("");
    setQuery("");
    setSelector("all");
    setOption("all");
    setReview("all");
    setReviewFacets({ causal_validation: null, grading: null });
    setPage(0);
    if (!allowed) {
      setLoading(false);
      return;
    }
    setLoading(true);
    void request<InstructorIndex>(
      `/api/engagements/${encodeURIComponent(engagement.id)}/instructor-key`,
    )
      .then((v) => {
        if (current !== sequence.current) return;
        assertKeyContext(v, engagement.id);
        if (v.audience !== "INSTRUCTOR_ONLY" || !Array.isArray(v.entries))
          throw Error("Invalid protected source index.");
        setIndex(v);
      })
      .catch((e) => {
        if (current === sequence.current) {
          setIndex(null);
          setDetail(null);
          setError(e.message);
        }
      })
      .finally(() => {
        if (current === sequence.current) setLoading(false);
      });
    return () => {
      ++sequence.current;
    };
  }, [
    engagement.id,
    allowed,
    viewerId,
    engagement.revision,
    JSON.stringify([
      engagement.scope,
      engagement.company_source_binding,
      engagement.evidence_acquisition,
    ]),
  ]);
  async function inspect(entry: KeyEntry) {
    if (!index || !allowed) return;
    const current = ++sequence.current;
    setSelected(entry.id);
    setDetail(null);
    setError("");
    setLoading(true);
    try {
      const v = await request<InstructorDetail>(
        `/api/engagements/${encodeURIComponent(engagement.id)}/instructor-key/${encodeURIComponent(entry.id)}`,
      );
      if (current !== sequence.current) return;
      assertKeyDetail(v, entry, engagement.id, index.archive.sha256);
      setDetail(v);
    } catch (e) {
      if (current === sequence.current) {
        setIndex(null);
        setDetail(null);
        setError((e as Error).message);
      }
    } finally {
      if (current === sequence.current) setLoading(false);
    }
  }
  if (!allowed) return <p>Instructor access is required.</p>;
  if (index && index.binding.engagement_id !== engagement.id)
    return <p role="status">Loading protected context…</p>;
  const entries = index
    ? index.semantic_matching && query.trim() && completeIds === undefined
      ? []
      : filterKeys(index.entries, {
          query,
          selector,
          option,
          review,
          review_facets: reviewFacets,
          complete_match_ids: completeIds,
        })
    : [];
  return (
    <section
      id="instructor-reference-library"
      className="instructor-key"
      aria-label="Protected instructor source archive"
    >
      <h2>Instructor source archive</h2>
      <p>
        <strong>NOT_BOUND · archived authored explanations.</strong> These
        records are not a list of scenarios active in this engagement. No
        learner comparison or grade is provided.
      </p>
      {loading && <p role="status">Loading protected source…</p>}
      {searchPending && (
        <p role="status">Matching complete authored content…</p>
      )}
      {searchError && (
        <p role="alert">
          {searchError} Clear the query or reopen the protected workspace.
        </p>
      )}
      {error && (
        <p role="alert">
          {error} Close and reopen this protected workspace to retry.
        </p>
      )}
      {index && (
        <>
          <p>
            Engagement access context: {engagement.title} ({engagement.id}).
            Archive: <code>{index.archive.sha256}</code>. Migrated{" "}
            {index.migrated} / required {index.required}.
          </p>
          {index.reference_crosswalk && (
            <ReferenceCrosswalk
              key={index.reference_crosswalk.sha256 + ":" + selected}
              value={index.reference_crosswalk}
              mode="ARCHIVE"
              selected={selected}
              onCurrent={onReferenceCurrent}
              onLegacy={(id) => {
                sequence.current++;
                setDetail(null);
                setSelected("");
                setQuery(id);
                setSelector("all");
                setOption("all");
                setReview("all");
                setReviewFacets({ causal_validation: null, grading: null });
                setPage(0);
                setLoading(false);
              }}
            />
          )}
          <InstructorKeyViews
            engagement={engagement}
            viewerId={viewerId}
            enabled={savedViewsEnabled}
            kind="ARCHIVE"
            keyPin={index.archive.sha256}
            filters={{
              query,
              selector,
              option,
              review,
              review_facets: reviewFacets,
              page,
              scenario:
                selected && index.entries.find((x) => x.id === selected)
                  ? {
                      id: selected,
                      key_sha256: index.entries.find((x) => x.id === selected)!
                        .key_sha256,
                    }
                  : null,
            }}
            validate={(value) =>
              validateArchiveFilters(
                value as ArchiveKeyFilters,
                index,
                (value as ArchiveKeyFilters).query === query
                  ? completeIds
                  : undefined,
                (value as ArchiveKeyFilters).query !== query,
              )
            }
            onRestore={(value) => {
              const v = validateArchiveFilters(
                value as ArchiveKeyFilters,
                index,
                (value as ArchiveKeyFilters).query === query
                  ? completeIds
                  : undefined,
                (value as ArchiveKeyFilters).query !== query,
              );
              sequence.current++;
              setLoading(false);
              setDetail(null);
              setQuery(v.query);
              setSelector(v.selector);
              setOption(v.option);
              setReview(v.review);
              setReviewFacets(
                v.review_facets ?? { causal_validation: null, grading: null },
              );
              setPage(v.page);
              setSelected(v.scenario?.id ?? "");
            }}
          />
          <div className="actions">
            <label>
              Search archive IDs, hashes or literal authored terms
              <input
                value={query}
                maxLength={1000}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setPage(0);
                }}
              />
            </label>
            {(["causal_validation", "grading"] as const).map((field) => (
              <label key={field}>
                {field === "causal_validation"
                  ? "Recorded causal validation"
                  : "Recorded grading status"}
                <select
                  value={reviewFacets[field] ?? ""}
                  onChange={(event) => {
                    setReviewFacets({
                      ...reviewFacets,
                      [field]: event.target.value || null,
                    });
                    setPage(0);
                  }}
                >
                  <option value="">All recorded states</option>
                  {[...new Set(index.entries.map((row) => row.review[field]))]
                    .filter(
                      (value) => typeof value === "string" && value.length > 0,
                    )
                    .sort()
                    .map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                </select>
              </label>
            ))}
            <label>
              Selector
              <select
                value={selector}
                onChange={(e) => {
                  setSelector(e.target.value);
                  setOption("all");
                  setPage(0);
                }}
              >
                <option value="all">All selectors</option>
                {[...new Set(index.entries.map((e) => keySelector(e.id)))]
                  .sort()
                  .map((v) => (
                    <option key={v}>{v}</option>
                  ))}
              </select>
            </label>
            <label>
              Option
              <select
                value={option}
                onChange={(e) => {
                  setOption(e.target.value);
                  setPage(0);
                }}
              >
                <option value="all">All options</option>
                {[
                  ...new Set(
                    index.entries
                      .filter(
                        (e) =>
                          selector === "all" || keySelector(e.id) === selector,
                      )
                      .map((e) => keyOption(e.id)),
                  ),
                ]
                  .sort()
                  .map((v) => (
                    <option key={v}>{v}</option>
                  ))}
              </select>
            </label>
            <label>
              Professional source review
              <select
                value={review}
                onChange={(e) => {
                  setReview(e.target.value);
                  setPage(0);
                }}
              >
                <option value="all">All review states</option>
                {[...new Set(index.entries.map((e) => e.review.professional))]
                  .sort()
                  .map((v) => (
                    <option key={v}>{v}</option>
                  ))}
              </select>
            </label>
            <button
              onClick={() => {
                setQuery("");
                setSelector("all");
                setOption("all");
                setReview("all");
                setReviewFacets({ causal_validation: null, grading: null });
                setPage(0);
              }}
            >
              Reset filters
            </button>
          </div>
          <p>
            {index.semantic_matching
              ? "Search matches every authored scalar in title, mechanism, facts, actor-role, artifact, event and path fields. Display previews alone are shortened."
              : "This older index supports metadata and bounded display-preview search only."}{" "}
            These are authored terms, not verified person, asset, owner,
            severity or calendar-period classifications. The full explanation
            remains available for omitted or shortened content. Recorded
            validation and grading labels do not create a new assessment.
          </p>
          <p>
            {entries.length} of {index.entries.length} archived explanations
            match these filters.
          </p>
          {!entries.length && !searchPending && !searchError && (
            <p>
              No matching archived explanations. Review or reset the active
              filters.
            </p>
          )}
          <ul>
            {entries.slice(page * 25, (page + 1) * 25).map((e) => (
              <li key={e.id}>
                <button
                  aria-pressed={selected === e.id}
                  onClick={() => void inspect(e)}
                >
                  {e.id}
                </button>{" "}
                · {e.review.professional} · {e.review.gaps.length} recorded gaps
                {e.semantic_search && (
                  <>
                    <p>
                      Authored title:{" "}
                      {e.semantic_search.terms.find(
                        (t) => t.pointer === "/title",
                      )?.text ?? "not included"}
                    </p>
                    <p>
                      {e.semantic_search.terms.length} of{" "}
                      {e.semantic_search.total_scalars} literal scalars
                      displayed; {e.semantic_search.omitted_scalars} omitted
                      from previews, {e.semantic_search.truncated_values}{" "}
                      shortened. Field coverage:{" "}
                      {e.semantic_search.coverage_fields
                        .map(
                          (f) =>
                            `${f} ${e.semantic_search!.included_by_field[f]} included / ${e.semantic_search!.omitted_by_field[f]} omitted`,
                        )
                        .join("; ")}
                      .
                    </p>
                  </>
                )}
              </li>
            ))}
          </ul>
          <div className="actions">
            <button disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              Previous explanations
            </button>
            <span>
              Page {page + 1} of {Math.max(1, Math.ceil(entries.length / 25))}
            </span>
            <button
              disabled={(page + 1) * 25 >= entries.length}
              onClick={() => setPage((p) => p + 1)}
            >
              Next explanations
            </button>
          </div>
        </>
      )}
      {detail && (
        <article aria-label="Selected instructor explanation">
          <h3>
            {detail.key.id} · {detail.key.explanation.title}
          </h3>
          <p>
            <strong>{detail.key.review.professional}</strong> · Causal
            validation: {detail.key.review.causal_validation} · Grading:{" "}
            {detail.key.review.grading} · Binding: {detail.binding.status}
          </p>
          <p>
            Original bytes: <code>{detail.key.source.raw_sha256}</code>
            <br />
            Canonical source: <code>
              {detail.key.source.canonical_sha256}
            </code>{" "}
            · Source schema {detail.key.source.schema_version}
          </p>
          <details open>
            <summary>Missing information and review limits</summary>
            <Value value={detail.key.review.gaps} />
          </details>
          {index && (
            <InstructorOriginalInspection
              key={detail.key.id + ":originals"}
              index={index}
              initialId={detail.key.id}
            />
          )}
          <InstructorRelationshipExplorer
            key={detail.key.id + ":" + detail.key.source.raw_sha256}
            graph={detail.key.graph}
            explanation={detail.key.explanation}
            renderValue={(value) => <Value value={value} />}
          />
          {Object.entries({
            Mechanism: detail.key.explanation.mechanism,
            Facts: detail.key.explanation.facts,
            "Actor knowledge and beliefs (authored statements)":
              detail.key.explanation.actor_knowledge,
            "Artifact definitions (not proof of delivery)":
              detail.key.explanation.artifacts,
            Events: detail.key.explanation.events,
            "Alternative playable paths": detail.key.explanation.playable_paths,
            "Supported authored conclusions":
              detail.key.explanation.rubric.supported_conclusions,
            "Acceptable alternatives":
              detail.key.explanation.rubric.acceptable_alternatives,
            "Unsupported guesses":
              detail.key.explanation.rubric.unsupported_guesses,
            "Authored reference graph (not corroboration)": detail.key.graph,
          }).map(([label, value]) => (
            <details key={label}>
              <summary>{label}</summary>
              <Value value={value} />
            </details>
          ))}
        </article>
      )}
    </section>
  );
}
