import { InstructorKeyViews } from "./InstructorKeyViews";
import { InstructorRelationshipExplorer } from "./InstructorRelationshipExplorer";
import {
  validateArchiveFilters,
  type ArchiveKeyFilters,
} from "./instructorKeyViews";
import { useEffect, useRef, useState } from "react";
import { request, type Engagement } from "./api";
import {
  assertKeyContext,
  assertKeyDetail,
  filterKeys,
  keyOption,
  keySelector,
  type InstructorIndex,
  type InstructorDetail,
  type KeyEntry,
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
}: {
  engagement: Engagement;
  viewerId?: string;
  savedViewsEnabled?: boolean;
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
    [page, setPage] = useState(0);
  const sequence = useRef(0),
    allowed = (engagement.permissions ?? []).includes("instruct");
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
    ? filterKeys(index.entries, { query, selector, option, review })
    : [];
  return (
    <section
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
              validateArchiveFilters(value as ArchiveKeyFilters, index)
            }
            onRestore={(value) => {
              const v = validateArchiveFilters(
                value as ArchiveKeyFilters,
                index,
              );
              sequence.current++;
              setLoading(false);
              setDetail(null);
              setQuery(v.query);
              setSelector(v.selector);
              setOption(v.option);
              setReview(v.review);
              setPage(v.page);
              setSelected(v.scenario?.id ?? "");
            }}
          />
          <div className="actions">
            <label>
              Search source ID or review gap
              <input
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setPage(0);
                }}
              />
            </label>
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
                setPage(0);
              }}
            >
              Reset filters
            </button>
          </div>
          <p>
            {entries.length} of {index.entries.length} archived explanations
            match these filters.
          </p>
          {!entries.length && (
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
