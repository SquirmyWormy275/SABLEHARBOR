import { useEffect, useRef, useState } from "react";
import { ApiError, request, type Engagement } from "./api";
import type { BoundResponse } from "./boundInstructorKey";
import { sameDebriefValue } from "./instructorDebrief";
import {
  assessmentContext,
  assessmentSavePayload,
  assertAssessmentOptions,
  assertAssessmentRecord,
  emptyAssessment,
  type AssessmentDraft,
  type AssessmentHistoryPin,
  type PinnedAssessmentOptions,
  type AssessmentReference,
  type AssessmentRecord,
} from "./instructorAssessments";
export type InstructorAssessmentsProps = {
  engagement: Engagement;
  viewerId: string;
  enabled: boolean;
  bound: BoundResponse;
  history: AssessmentHistoryPin;
};
export function InstructorAssessments(p: InstructorAssessmentsProps) {
  if (
    !p.enabled ||
    !p.viewerId ||
    !p.engagement.permissions?.includes("instruct")
  )
    return null;
  return (
    <Panel
      key={assessmentContext(
        p.engagement,
        p.viewerId,
        p.bound.binding.manifest_sha256,
        p.history,
      )}
      {...p}
    />
  );
}
function References({
  label,
  options,
  selected,
  onChange,
  readonly = false,
}: {
  label: string;
  options: AssessmentReference[];
  selected: string[];
  onChange?: (ids: string[]) => void;
  readonly?: boolean;
}) {
  const [query, setQuery] = useState("");
  const rows = options.filter((r) =>
    [r.id, r.kind, r.record_id, r.relation]
      .join(" ")
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const shown = [
    ...options.filter((r) => selected.includes(r.id)),
    ...rows.filter((r) => !selected.includes(r.id)).slice(0, 40),
  ];
  return (
    <details>
      <summary>
        {label} · {selected.length} selected historical references
      </summary>
      {!readonly && (
        <label>
          Find work references for {label}
          <input
            type="search"
            value={query}
            onChange={(ev) => setQuery(ev.target.value)}
          />
        </label>
      )}
      {!readonly && (
        <p>
          {rows.length} matches; at most 40 unselected results shown. Refine
          search to choose another exact record.
        </p>
      )}
      {(readonly ? options.filter((r) => selected.includes(r.id)) : shown).map(
        (r) => (
          <div key={r.id}>
            <label>
              {!readonly && (
                <input
                  type="checkbox"
                  checked={selected.includes(r.id)}
                  onChange={(ev) =>
                    onChange?.(
                      ev.target.checked
                        ? [...selected, r.id]
                        : selected.filter((id) => id !== r.id),
                    )
                  }
                />
              )}{" "}
              {r.kind} {r.record_id}
              {r.version !== null ? ` · version ${r.version}` : ""} ·{" "}
              {r.relation}
            </label>
            <details>
              <summary>Exact reference {r.id}</summary>
              <p>Inventory SHA256 {r.inventory_sha256}</p>
              <p>Content SHA256 {r.content_sha256 ?? "Not recorded"}</p>
              <p>
                Associated expectations:{" "}
                {r.expectation_ids.join(", ") || "None recorded"}
              </p>
            </details>
          </div>
        ),
      )}
      {selected
        .filter((id) => !options.some((r) => r.id === id))
        .map((id) => (
          <p key={id}>
            Unavailable reference {id}
            {!readonly && (
              <button
                type="button"
                onClick={() => onChange?.(selected.filter((v) => v !== id))}
              >
                Remove unavailable reference {id}
              </button>
            )}
          </p>
        ))}
    </details>
  );
}
function Panel({
  engagement: e,
  viewerId,
  bound,
  history,
}: InstructorAssessmentsProps) {
  const base = `/api/engagements/${encodeURIComponent(e.id)}/instructor-assessments`,
    key = bound.binding.manifest_sha256;
  const [options, setOptions] = useState<PinnedAssessmentOptions | null>(null),
    [draft, setDraft] = useState<AssessmentDraft>(emptyAssessment),
    [records, setRecords] = useState<AssessmentRecord[]>([]),
    [opened, setOpened] = useState<AssessmentRecord | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [retry, setRetry] = useState(false);
  const epoch = useRef(0),
    pending = useRef<ReturnType<typeof assessmentSavePayload> | null>(null);
  useEffect(() => {
    epoch.current++;
    return () => {
      epoch.current++;
    };
  }, []);
  const dirty = !sameDebriefValue(draft, emptyAssessment());
  function edit(patch: Partial<AssessmentDraft>) {
    setDraft({ ...draft, ...patch });
    setNotice("");
  }
  function readFailure(err: unknown) {
    setError((err as Error).message);
    setOptions(null);
    setOpened(null);
    setRecords([]);
    if (err instanceof ApiError && [401, 403].includes(err.status))
      setDraft(emptyAssessment());
  }
  async function choices() {
    const n = epoch.current;
    setBusy(true);
    setError("");
    setOptions(null);
    setOpened(null);
    try {
      const o = await request<PinnedAssessmentOptions>(
        base + `/options?revision=${history.revision}`,
      );
      if (n !== epoch.current) return;
      setOptions(
        assertAssessmentOptions(
          o,
          e,
          key,
          bound.snapshot.audited_actor_id,
          bound.binding.bound_revision,
          history,
        ),
      );
    } catch (err) {
      if (n === epoch.current) readFailure(err);
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  async function list() {
    const n = epoch.current;
    setBusy(true);
    setOpened(null);
    setError("");
    try {
      const value = await request<{
        engagement_id: string;
        current_engagement_revision: number;
        assessments: AssessmentRecord[];
      }>(base);
      if (n !== epoch.current) return;
      if (
        value.engagement_id !== e.id ||
        value.current_engagement_revision !== e.revision ||
        !Array.isArray(value.assessments)
      )
        throw Error("Assessment history changed. Reload the engagement.");
      const rows = value.assessments.map((r) =>
        assertAssessmentRecord(r, e, key),
      );
      if (rows.some((r) => r.document !== undefined))
        throw Error("History must not include unopened assessment documents.");
      setRecords(rows);
      if (rows.some((r) => r.context_status !== "CURRENT")) {
        setOptions(null);
        setOpened(null);
      }
    } catch (err) {
      if (n === epoch.current) {
        readFailure(err);
      }
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  async function open(row: AssessmentRecord) {
    const n = epoch.current;
    setBusy(true);
    setOpened(null);
    setError("");
    try {
      const r = await request<AssessmentRecord>(
        base + `/${encodeURIComponent(row.id)}`,
      );
      if (n !== epoch.current) return;
      assertAssessmentRecord(r, e, key);
      if (
        r.id !== row.id ||
        r.sha256 !== row.sha256 ||
        !r.personal_content_visible ||
        !r.document
      )
        throw Error("Exact assessment is unavailable or changed.");
      setOpened(r);
    } catch (err) {
      if (n === epoch.current) readFailure(err);
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  async function save() {
    if (!options || busy) return;
    const n = epoch.current;
    setError("");
    try {
      const payload =
        pending.current ??
        assessmentSavePayload(draft, options, crypto.randomUUID());
      pending.current = payload;
      setBusy(true);
      const r = await request<AssessmentRecord>(base, "POST", payload);
      if (n !== epoch.current) return;
      assertAssessmentRecord(r, e, key);
      const {
        predecessor,
        command_id,
        expected_engagement_revision,
        learner_revision,
        key_pin,
        rubric_sha256,
        inventory_sha256,
        ...authored
      } = payload;
      if (
        !r.document ||
        !sameDebriefValue(r.document.authored, authored) ||
        !sameDebriefValue(r.predecessor, predecessor) ||
        r.document.actor_id !== viewerId ||
        r.document.pins.rubric_sha256 !== rubric_sha256 ||
        r.document.pins.inventory_sha256 !== inventory_sha256 ||
        r.document.pins.audited_actor_id !== bound.snapshot.audited_actor_id ||
        r.document.pins.selected_state_sha256 !== history.state_sha256 ||
        r.document.pins.selected_history_sha256 !== history.history_sha256 ||
        r.document.pins.selected_history_tip_sha256 !== history.event_sha256 ||
        r.learner_revision !== learner_revision
      )
        throw Error(
          "Assessment receipt differs from the exact authored judgment.",
        );
      pending.current = null;
      setRetry(false);
      setOpened(r);
      setRecords((old) => [
        ...old.filter((v) => v.id !== r.id),
        { ...r, document: undefined },
      ]);
      setDraft(emptyAssessment());
      setNotice(
        "Instructor judgment recorded privately. No grade, task result or learner release changed.",
      );
    } catch (err) {
      if (n !== epoch.current) return;
      setError((err as Error).message);
      if (pending.current) {
        if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
          pending.current = null;
          setRetry(false);
          if ([401, 403, 409].includes(err.status)) {
            setOptions(null);
            setOpened(null);
            setRecords([]);
            if ([401, 403].includes(err.status)) setDraft(emptyAssessment());
          }
        } else setRetry(true);
      }
    } finally {
      if (n === epoch.current) setBusy(false);
    }
  }
  const expectations =
    options?.expectations.filter((x) =>
      x.issue_ids.every((id) => draft.issue_ids.includes(id)),
    ) ?? [];
  return (
    <details className="panel">
      <summary>Instructor assessment of this recorded work</summary>
      <p>
        Record separate instructor judgments about history revision{" "}
        {history.revision}. Authored expectations and technical links do not
        determine these judgments. No aggregate grade is calculated.
      </p>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <button disabled={busy || retry} onClick={() => void choices()}>
        Load exact assessment choices
      </button>
      <button disabled={busy || retry} onClick={() => void list()}>
        Load assessment history
      </button>
      {options && (
        <form
          onSubmit={(ev) => {
            ev.preventDefault();
            void save();
          }}
        >
          <fieldset disabled={busy || retry}>
            <legend>Instructor-authored judgment</legend>
            <label>
              Assessment title
              <input
                required
                maxLength={200}
                value={draft.title}
                onChange={(ev) => edit({ title: ev.target.value })}
              />
            </label>
            <label>
              Assessment issues
              <select
                aria-label="Assessment issues"
                multiple
                value={draft.issue_ids}
                onChange={(ev) =>
                  edit({
                    issue_ids: Array.from(
                      ev.target.selectedOptions,
                      (x) => x.value,
                    ),
                  })
                }
              >
                {options.issues.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.id}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Assessment expectations
              <select
                aria-label="Assessment expectations"
                multiple
                value={draft.expectation_ids}
                onChange={(ev) =>
                  edit({
                    expectation_ids: Array.from(
                      ev.target.selectedOptions,
                      (x) => x.value,
                    ),
                  })
                }
              >
                {expectations.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.id}
                  </option>
                ))}
              </select>
            </label>
            <details>
              <summary>Selected authored rubric</summary>
              {options.issues
                .filter((i) => draft.issue_ids.includes(i.id))
                .map((i) => (
                  <section key={i.id}>
                    <h4>{i.id}</h4>
                    <p>{i.claim}</p>
                    <p>Authored uncertainty: {i.uncertainty}</p>
                  </section>
                ))}
              {expectations
                .filter((i) => draft.expectation_ids.includes(i.id))
                .map((i) => (
                  <section key={i.id}>
                    <h4>{i.id}</h4>
                    <p>{i.procedure}</p>
                    <ul>
                      {i.acceptable_alternatives.map((a, j) => (
                        <li key={j}>{a}</li>
                      ))}
                    </ul>
                  </section>
                ))}
            </details>
            {draft.predecessor && (
              <p>
                Explicit correction of {draft.predecessor.id}. This new record
                uses selected history revision {history.revision}; its
                predecessor remains immutable.
              </p>
            )}
            {draft.dimensions.map((d, i) => (
              <fieldset key={d.dimension}>
                <legend>{d.dimension}</legend>
                <label>
                  {d.dimension} assessment
                  <textarea
                    required
                    maxLength={2000}
                    aria-label={`${d.dimension} assessment`}
                    value={d.assessment}
                    onChange={(ev) =>
                      edit({
                        dimensions: draft.dimensions.map((v, j) =>
                          i === j ? { ...v, assessment: ev.target.value } : v,
                        ),
                      })
                    }
                  />
                </label>
                <label>
                  {d.dimension} rationale
                  <textarea
                    required
                    maxLength={4000}
                    aria-label={`${d.dimension} rationale`}
                    value={d.rationale}
                    onChange={(ev) =>
                      edit({
                        dimensions: draft.dimensions.map((v, j) =>
                          i === j ? { ...v, rationale: ev.target.value } : v,
                        ),
                      })
                    }
                  />
                </label>
                <References
                  label={d.dimension}
                  options={options.references}
                  selected={d.reference_ids}
                  onChange={(ids) =>
                    edit({
                      dimensions: draft.dimensions.map((v, j) =>
                        i === j ? { ...v, reference_ids: ids } : v,
                      ),
                    })
                  }
                />
              </fieldset>
            ))}
            {(["alternatives", "overrides", "defects"] as const).map((kind) => (
              <fieldset key={kind}>
                <legend>{kind}</legend>
                {draft[kind].map((row, i) => (
                  <fieldset key={i}>
                    <legend>
                      {kind} {i + 1}
                    </legend>
                    {Object.entries(row)
                      .filter(([field]) => field !== "reference_ids")
                      .map(([field, value]) =>
                        field === "expectation_id" || field === "issue_id" ? (
                          <label key={field}>
                            {kind} {i + 1} {field}
                            <select
                              aria-label={`${kind} ${i + 1} ${field}`}
                              value={value as string}
                              onChange={(ev) =>
                                edit({
                                  [kind]: draft[kind].map((v, j) =>
                                    i === j
                                      ? { ...v, [field]: ev.target.value }
                                      : v,
                                  ),
                                })
                              }
                            >
                              <option value="">
                                Choose explicit selection
                              </option>
                              {(field === "issue_id"
                                ? draft.issue_ids
                                : draft.expectation_ids
                              ).map((id) => (
                                <option key={id} value={id}>
                                  {id}
                                </option>
                              ))}
                            </select>
                          </label>
                        ) : (
                          <label key={field}>
                            {kind} {i + 1} {field}
                            <textarea
                              required
                              maxLength={field === "rationale" ? 4000 : 2000}
                              aria-label={`${kind} ${i + 1} ${field}`}
                              value={value as string}
                              onChange={(ev) =>
                                edit({
                                  [kind]: draft[kind].map((v, j) =>
                                    i === j
                                      ? { ...v, [field]: ev.target.value }
                                      : v,
                                  ),
                                })
                              }
                            />
                          </label>
                        ),
                      )}
                    <References
                      label={`${kind} ${i + 1}`}
                      options={options.references}
                      selected={row.reference_ids}
                      onChange={(ids) =>
                        edit({
                          [kind]: draft[kind].map((v, j) =>
                            i === j ? { ...v, reference_ids: ids } : v,
                          ),
                        })
                      }
                    />
                    <button
                      type="button"
                      onClick={() =>
                        edit({ [kind]: draft[kind].filter((_, j) => i !== j) })
                      }
                    >
                      Remove {kind} {i + 1}
                    </button>
                  </fieldset>
                ))}
                <button
                  type="button"
                  disabled={draft[kind].length >= 8}
                  onClick={() =>
                    edit({
                      [kind]: [
                        ...draft[kind],
                        kind === "alternatives"
                          ? {
                              expectation_id: "",
                              description: "",
                              rationale: "",
                              reference_ids: [],
                            }
                          : kind === "overrides"
                            ? {
                                expectation_id: "",
                                prior_interpretation: "",
                                replacement: "",
                                rationale: "",
                                reference_ids: [],
                              }
                            : {
                                issue_id: "",
                                description: "",
                                impact: "",
                                rationale: "",
                                reference_ids: [],
                              },
                      ],
                    })
                  }
                >
                  Add {kind}
                </button>
              </fieldset>
            ))}
            <button type="submit">Save instructor assessment</button>
            <button
              type="button"
              onClick={() => {
                setDraft(emptyAssessment());
                setNotice("Unsaved assessment discarded.");
              }}
            >
              Discard unsaved assessment
            </button>
          </fieldset>
        </form>
      )}
      {retry && (
        <>
          <p>
            The save response was not confirmed. Retry uses the same authored
            content, historical pins and command.
          </p>
          <button disabled={busy} onClick={() => void save()}>
            Retry exact assessment save
          </button>
          <button
            disabled={busy}
            onClick={() => {
              pending.current = null;
              setRetry(false);
              setNotice(
                "Pending request discarded locally. Inspect history before saving again.",
              );
            }}
          >
            Discard pending assessment request
          </button>
        </>
      )}
      <section aria-label="Assessment history">
        {records.map((r) => (
          <article key={r.id}>
            <h4>{r.personal_content_visible ? r.title : r.id}</h4>
            <p>
              {r.context_status} · version {r.version} · history revision{" "}
              {r.learner_revision}
            </p>
            <button
              disabled={busy || retry || !r.personal_content_visible}
              onClick={() => void open(r)}
            >
              Open assessment {r.id}
            </button>
          </article>
        ))}
      </section>
      {opened?.document && (
        <section aria-label="Opened instructor assessment">
          <h3>{opened.title}</h3>
          <p>
            Instructor {opened.document.actor_id} ·{" "}
            {opened.document.recorded_at} · UNVALIDATED instructor judgment.
          </p>
          <p>{opened.document.qualification}</p>
          <details>
            <summary>Recorded authored rubric</summary>
            {opened.document.selected_issues.map((i) => (
              <section key={i.id}>
                <h4>{i.id}</h4>
                <p>{i.claim}</p>
                <p>Authored uncertainty: {i.uncertainty}</p>
              </section>
            ))}
            {opened.document.selected_expectations.map((x) => (
              <section key={x.id}>
                <h4>{x.id}</h4>
                <p>{x.procedure}</p>
                <ul>
                  {x.acceptable_alternatives.map((a, j) => (
                    <li key={j}>{a}</li>
                  ))}
                </ul>
              </section>
            ))}
          </details>
          <References
            label="All recorded work"
            options={opened.document.references}
            selected={opened.document.references.map((r) => r.id)}
            readonly
          />
          {opened.document.authored.dimensions.map((d) => (
            <section key={d.dimension}>
              <h4>{d.dimension}</h4>
              <p>{d.assessment}</p>
              <p>Rationale: {d.rationale}</p>
              <References
                label={`Recorded ${d.dimension}`}
                options={opened.document!.references}
                selected={d.reference_ids}
                readonly
              />
            </section>
          ))}
          {(["alternatives", "overrides", "defects"] as const).map((kind) => (
            <section key={kind}>
              <h4>{kind}</h4>
              {opened.document!.authored[kind].map((row, i) => (
                <dl key={i}>
                  {Object.entries(row).map(([field, value]) => (
                    <div key={field}>
                      <dt>{field.replaceAll("_", " ")}</dt>
                      <dd>{Array.isArray(value) ? value.join(", ") : value}</dd>
                    </div>
                  ))}
                </dl>
              ))}
            </section>
          ))}
          <details>
            <summary>Exact assessment provenance</summary>
            <p>Assessment SHA256 {opened.sha256}</p>
            {Object.entries(opened.document.pins).map(([field, value]) => (
              <p key={field}>
                {field}: {value}
              </p>
            ))}
          </details>
          <button
            disabled={
              busy || retry || dirty || !options || !opened.correction_allowed
            }
            onClick={() => {
              if (opened.document && options) {
                setDraft({
                  ...structuredClone(opened.document.authored),
                  predecessor: { id: opened.id, sha256: opened.sha256 },
                });
                setNotice(
                  "Correction copied explicitly. Review references against the selected historical inventory before saving.",
                );
              }
            }}
          >
            Prepare correction using history revision {history.revision}
          </button>
          {dirty && (
            <p>
              Save or discard the current draft before preparing a correction.
            </p>
          )}
          <button onClick={() => setOpened(null)}>
            Hide assessment document
          </button>
        </section>
      )}
    </details>
  );
}
