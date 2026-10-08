import { str, type Engagement, type Row } from "./api";
import type { ContextLink } from "./investigationContext";
import {
  integrityStatusLabels,
  traceIntegrity,
  type OriginalIntegrity,
} from "./procedureIntegrity";
import {
  observationLabels,
  resolveTraceReference,
  tracePosition,
  visibleCount,
  type TraceReadiness,
} from "./traceReadiness";

function Counts({
  values,
}: {
  values: Record<string, number> | null | undefined;
}) {
  if (!values)
    return <p>Disposition counts unavailable. This is not a zero count.</p>;
  if (!Object.keys(values).length)
    return <p>No current recorded item observations.</p>;
  return (
    <ul>
      {Object.entries(values).map(([key, value]) => (
        <li key={key}>
          {observationLabels[key] ?? key}: {visibleCount(value)}
        </li>
      ))}
    </ul>
  );
}
export function ProcedureTraceReadiness({
  engagement,
  data,
  integrity,
  onPreview,
}: {
  engagement: Engagement;
  data?: TraceReadiness;
  integrity?: OriginalIntegrity;
  onPreview: (kind: string, row: Row, reference?: ContextLink) => void;
}) {
  if (!data)
    return <p>Sample trace metadata is not supplied by this report.</p>;
  return (
    <section
      aria-label="Procedure sample trace metadata"
      style={{ minWidth: 0, overflowWrap: "anywhere" }}
    >
      <h4>Recorded sample traces</h4>
      <p>
        Recorded metadata linkage only. Observations, population reliability
        decisions and item counts do not establish completeness, accuracy or
        effectiveness.{" "}
        {integrity
          ? "The separate retained-copy recheck appears below."
          : "Original bytes were not rechecked."}
      </p>
      <p>
        Retained traces: {visibleCount(data.trace_count)} · Current correction
        lineages: {visibleCount(data.current_leaf_count)}
      </p>
      {data.status === "NO_RECORDED_TRACES" ? (
        <p>No sample trace is recorded for this procedure.</p>
      ) : (
        data.status !== "RECORDED_TRACE_LINKS" && (
          <p role="status">
            Some trace metadata is unavailable. Current counts are not treated
            as zero or testing credit.
          </p>
        )
      )}
      <Counts values={data.current_leaf_item_status_counts} />
      <p>
        Counts describe current recorded observations across trace lineages, not
        unique business items or completed professional tests.
      </p>
      {data.traces.map((trace, index) => (
        <details key={`${trace.id}:${index}`}>
          <summary>
            {tracePosition(data, trace.id)} · {trace.id}
            {trace.revision ? ` · trace revision ${trace.revision}` : ""}
          </summary>
          {integrity && (
            <p>
              Retained-copy check:{" "}
              {
                integrityStatusLabels[
                  traceIntegrity(integrity, trace.id)?.status ?? "NOT_RECHECKED"
                ]
              }
            </p>
          )}
          {trace.status !== "EXACT_VISIBLE_METADATA_LINKS" ? (
            <p>
              Exact linked records unavailable:{" "}
              {trace.reason_codes.join(", ") || "Unresolved metadata"}.
            </p>
          ) : (
            <>
              <Counts values={trace.recorded_item_status_counts} />
              <p>
                Selected items: {visibleCount(trace.selected_item_count)} ·
                Items without a recorded observation:{" "}
                {visibleCount(trace.items_with_no_recorded_observation_count)}
              </p>
              <div className="actions">
                {trace.exact_refs?.map((reference, i) => {
                  const row = resolveTraceReference(engagement, reference);
                  return (
                    <button
                      key={`${reference.kind}:${reference.id}:${i}`}
                      type="button"
                      disabled={!row}
                      onClick={() => {
                        const current = resolveTraceReference(
                          engagement,
                          reference,
                        );
                        if (current)
                          onPreview(reference.kind, current, reference);
                      }}
                    >
                      Open exact {reference.kind} {reference.id}
                      {reference.version !== null
                        ? ` · version ${reference.version}`
                        : " · record pin"}
                      {!row ? " (unavailable)" : ""}
                    </button>
                  );
                })}
              </div>
              <details>
                <summary>
                  Population reliability and period qualifications
                </summary>
                <p>
                  Trace-recorded reliability:{" "}
                  {str(trace.population_reliability?.recorded_status)} ·
                  Trace-recorded provisional selection:{" "}
                  {str(trace.population_reliability?.selection_provisional)}
                </p>
                <p>
                  Current pinned population status:{" "}
                  {str(
                    trace.population_reliability?.current_population_status ??
                      trace.population_reliability?.recorded_status,
                  )}{" "}
                  · Current pinned selection provisional:{" "}
                  {str(
                    trace.population_reliability
                      ?.current_selection_provisional ??
                      trace.population_reliability?.selection_provisional,
                  )}
                </p>
                <p>
                  These are recorded qualifications, not independent population
                  acceptance. A later reliability decision does not rewrite this
                  historical trace.
                </p>
                <dl className="details">
                  {Object.entries(trace.period_qualification ?? {}).map(
                    ([key, value]) => (
                      <div key={key}>
                        <dt>{key.replaceAll("_", " ")}</dt>
                        <dd>{str(value)}</dd>
                      </div>
                    ),
                  )}
                </dl>
                <p>
                  Independent denominator and corroboration are not established
                  by this trace report.
                </p>
              </details>
            </>
          )}
        </details>
      ))}
    </section>
  );
}
