import { useState } from "react";
import type { Engagement } from "./api";
import {
  inputPins,
  selectionItems,
  executionPayload,
  ITEM_STATUSES,
  type Draft,
  type Item,
  type Pins,
} from "./sampleExecution";
import "./sampleExecutions.css";
const empty: Draft = {
  task: "",
  selection: "",
  workpaper: "",
  purpose: "",
  procedure: "",
  items: [],
  rationale: "",
};
export function SampleExecutions({
  engagement: e,
  supported,
  busy,
  onCommand,
}: {
  engagement: Engagement;
  supported: boolean;
  busy: boolean;
  onCommand: (
    kind: string,
    payload: Record<string, unknown>,
  ) => Promise<unknown>;
}) {
  const key = JSON.stringify([
    e.id,
    e.revision,
    e.permissions,
    e.scope,
    e.company_source_binding,
    e.evidence_acquisition,
    e.sample_execution_inputs,
  ]);
  return (
    <SampleWorkspace
      key={key}
      e={e}
      p={inputPins(e, supported)}
      busy={busy}
      onCommand={onCommand}
    />
  );
}
function SampleWorkspace({
  e,
  p,
  busy,
  onCommand,
}: {
  e: Engagement;
  p: Pins | null;
  busy: boolean;
  onCommand: (
    kind: string,
    payload: Record<string, unknown>,
  ) => Promise<unknown>;
}) {
  const [d, setD] = useState<Draft>(empty),
    [open, setOpen] = useState(false),
    [error, setError] = useState(""),
    [pending, setPending] = useState(false),
    [itemId, setItemId] = useState("");
  const update = (patch: Partial<Draft>) => {
    setError("");
    setD({ ...d, ...patch });
  };
  const item = (index: number, patch: Partial<Item>) =>
    update({
      items: d.items.map((i, n) => (n === index ? { ...i, ...patch } : i)),
    });
  const [taskSearch, setTaskSearch] = useState(""),
    [sourceSearch, setSourceSearch] = useState("");
  const taskLabels = new Map(
    e.tasks.map((t) => [t.id, String(t.title ?? t.text ?? t.id)]),
  );
  const sourceLabels = new Map(
    e.artifacts.map((a) => [a.id, String(a.name ?? a.id)]),
  );
  const matchingTasks =
    p?.tasks.filter((t) =>
      (t.task_id + " " + taskLabels.get(t.task_id))
        .toLowerCase()
        .includes(taskSearch.toLowerCase()),
    ) ?? [];
  const matchingSources =
    p?.artifacts.filter((a) =>
      (a.artifact_id + " " + sourceLabels.get(a.artifact_id))
        .toLowerCase()
        .includes(sourceSearch.toLowerCase()),
    ) ?? [];
  const [itemSearch, setItemSearch] = useState(""),
    [historySearch, setHistorySearch] = useState(""),
    [historyPage, setHistoryPage] = useState(0);
  const task = p?.tasks.find((t) => t.task_id === d.task),
    selection = p?.selections.find((s) => s.selection_id === d.selection);
  const inputStatus = String(
    (e.sample_execution_inputs as { status?: string } | undefined)?.status ??
      "UNAVAILABLE",
  );
  const traces = (
    Array.isArray(e.sample_executions) ? e.sample_executions : []
  ) as Record<string, unknown>[];
  const historyQuery = historySearch.trim().toLowerCase();
  const matchingTraces = traces.filter((t) =>
    [
      t.id,
      t.task_id,
      taskLabels.get(String(t.task_id)),
      t.selection_id,
      t.workpaper_id,
      t.purpose,
    ]
      .join(" ")
      .toLowerCase()
      .includes(historyQuery),
  );
  return (
    <section className="sample-executions" aria-label="Sample execution traces">
      <h2>Sample execution traces</h2>
      <p>
        Record explicit observations against selected items and a retained
        workpaper version. These manual records do not set procedure results or
        independent review status.
      </p>
      {p ? (
        <button
          disabled={busy}
          onClick={() => {
            setD(empty);
            setOpen(true);
            setError("");
          }}
        >
          Record sample execution
        </button>
      ) : (
        <p>
          Recording requires an active engagement, current input pins and
          learner or instructor permission.
        </p>
      )}
      {!p &&
        ["INPUT_LIMIT_EXCEEDED", "INPUT_DATA_UNAVAILABLE"].includes(
          inputStatus,
        ) && (
          <p role="status">
            Sample input index unavailable:{" "}
            {inputStatus === "INPUT_LIMIT_EXCEEDED"
              ? "the bounded input limit was exceeded"
              : "current input metadata could not be validated"}
            . Retained history remains readable.
          </p>
        )}
      {open && p && (
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (pending || busy) return;
            try {
              const payload = executionPayload(e, p, d);
              setPending(true);
              await onCommand(
                d.predecessor
                  ? "sample.execution.correct"
                  : "sample.execution.record",
                payload,
              );
              setOpen(false);
            } catch (err) {
              setError((err as Error).message);
            } finally {
              setPending(false);
            }
          }}
        >
          <h3>
            {d.predecessor
              ? "Correct sample execution"
              : "New sample execution"}
          </h3>
          <p>
            This form is kept only in this open context. A revision or
            permission change clears it.
          </p>
          <fieldset disabled={busy || pending}>
            <div className="sample-entry-grid">
              <details className="sample-entry-context" open>
                <summary>Procedure, sample and workpaper context</summary>
                <label>
                  Find execution procedure
                  <input
                    type="search"
                    value={taskSearch}
                    onChange={(x) => setTaskSearch(x.target.value)}
                  />
                </label>
                <p>
                  {matchingTasks.length} matching procedures; showing up to 50
                  plus current selection.
                </p>
                <label>
                  Execution procedure
                  <select
                    aria-label="Execution procedure"
                    required
                    value={d.task}
                    disabled={!!d.predecessor}
                    onChange={(x) =>
                      update({
                        task: x.target.value,
                        selection: "",
                        workpaper: "",
                        items: [],
                      })
                    }
                  >
                    <option value="">Choose procedure</option>
                    {p.tasks
                      .filter(
                        (t) =>
                          t.task_id === d.task ||
                          matchingTasks.slice(0, 50).includes(t),
                      )
                      .map((t) => (
                        <option key={t.task_id} value={t.task_id}>
                          {t.task_id} · {taskLabels.get(t.task_id)}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Execution selection
                  <select
                    aria-label="Execution selection"
                    required
                    value={d.selection}
                    disabled={!!d.predecessor}
                    onChange={(x) =>
                      update({ selection: x.target.value, items: [] })
                    }
                  >
                    <option value="">Choose selection</option>
                    {p.selections
                      .filter((s) => s.boundary_id === task?.boundary_id)
                      .map((s) => (
                        <option key={s.selection_id} value={s.selection_id}>
                          {s.selection_id} · {s.population_id}
                        </option>
                      ))}
                  </select>
                </label>
                {selection && (
                  <p>
                    Unit: {selection.sampling_unit} · Population:{" "}
                    {selection.population_status} · Selection provisional:{" "}
                    {String(selection.selection_provisional)}. Only the
                    explicitly added items below are recorded.
                  </p>
                )}
                <label>
                  Execution workpaper version
                  <select
                    aria-label="Execution workpaper version"
                    required
                    value={d.workpaper}
                    onChange={(x) => update({ workpaper: x.target.value })}
                  >
                    <option value="">Choose exact linked version</option>
                    {p.workpaper_versions
                      .filter((w) => w.task_ids.includes(d.task))
                      .map((w) => (
                        <option
                          key={`${w.workpaper_id}:${w.workpaper_version}`}
                          value={`${w.workpaper_id}:${w.workpaper_version}`}
                        >
                          {w.workpaper_id} · version {w.workpaper_version}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Execution purpose
                  <textarea
                    required
                    maxLength={4000}
                    value={d.purpose}
                    onChange={(x) => update({ purpose: x.target.value })}
                  />
                </label>
                <label>
                  Procedure actually performed
                  <textarea
                    required
                    maxLength={12000}
                    value={d.procedure}
                    onChange={(x) => update({ procedure: x.target.value })}
                  />
                </label>
              </details>
              <div className="sample-entry-items">
                <h4>Explicit item observations</h4>
                {!d.predecessor && (
                  <div>
                    <label>
                      Find selected item
                      <input
                        type="search"
                        value={itemSearch}
                        onChange={(x) => setItemSearch(x.target.value)}
                      />
                    </label>
                    <p>Item choices show up to 50 matching unrecorded IDs.</p>
                    <label>
                      Selected item to add
                      <select
                        aria-label="Selected item to add"
                        value={itemId}
                        onChange={(x) => setItemId(x.target.value)}
                      >
                        <option value="">Choose item</option>
                        {selectionItems(e, d.selection)
                          .filter(
                            (id) => !d.items.some((i) => i.item_id === id),
                          )
                          .filter((id) =>
                            id.toLowerCase().includes(itemSearch.toLowerCase()),
                          )
                          .slice(0, 50)
                          .map((id) => (
                            <option key={id}>{id}</option>
                          ))}
                      </select>
                    </label>
                    <button
                      type="button"
                      disabled={
                        !selectionItems(e, d.selection).includes(itemId) ||
                        d.items.some((i) => i.item_id === itemId) ||
                        d.items.length >= 500
                      }
                      onClick={() => {
                        update({
                          items: [
                            ...d.items,
                            {
                              item_id: itemId,
                              observation: "",
                              status: "",
                              evidence: [],
                            },
                          ],
                        });
                        setItemId("");
                      }}
                    >
                      Add selected item
                    </button>
                  </div>
                )}
                <label>
                  Find retained support
                  <input
                    type="search"
                    value={sourceSearch}
                    onChange={(x) => setSourceSearch(x.target.value)}
                  />
                </label>
                <p>
                  {matchingSources.length} matching originals; each support
                  selector shows up to 50 plus its current selection.
                </p>
                {d.items.map((i, index) => (
                  <fieldset key={i.item_id}>
                    <legend>Item {i.item_id}</legend>
                    <label>
                      Manual item status
                      <select
                        aria-label="Manual item status"
                        required
                        value={i.status}
                        onChange={(x) =>
                          item(index, { status: x.target.value })
                        }
                      >
                        <option value="">Choose an explicit status</option>
                        {ITEM_STATUSES.map((s) => (
                          <option key={s} value={s}>
                            {s.toLowerCase().replaceAll("_", " ")}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Item observation
                      <textarea
                        required
                        maxLength={8000}
                        value={i.observation}
                        onChange={(x) =>
                          item(index, { observation: x.target.value })
                        }
                      />
                    </label>
                    {i.evidence.map((r, n) => (
                      <div key={n}>
                        <label>
                          Retained support
                          <select
                            aria-label="Retained support"
                            required
                            value={r.artifact_id}
                            onChange={(x) => {
                              const a = p.artifacts.find(
                                (a) => a.artifact_id === x.target.value,
                              );
                              item(index, {
                                evidence: i.evidence.map((v, j) =>
                                  j === n
                                    ? {
                                        artifact_id: a?.artifact_id ?? "",
                                        sha256: a?.sha256 ?? "",
                                        locator: v.locator,
                                      }
                                    : v,
                                ),
                              });
                            }}
                          >
                            <option value="">Choose retained original</option>
                            {p.artifacts
                              .filter(
                                (a) =>
                                  a.artifact_id === r.artifact_id ||
                                  matchingSources.slice(0, 50).includes(a),
                              )
                              .map((a) => (
                                <option
                                  key={a.artifact_id}
                                  value={a.artifact_id}
                                >
                                  {a.artifact_id} ·{" "}
                                  {sourceLabels.get(a.artifact_id)}
                                </option>
                              ))}
                          </select>
                        </label>
                        <label>
                          Exact author-supplied locator
                          <input
                            required
                            maxLength={1000}
                            value={r.locator}
                            onChange={(x) =>
                              item(index, {
                                evidence: i.evidence.map((v, j) =>
                                  j === n
                                    ? { ...v, locator: x.target.value }
                                    : v,
                                ),
                              })
                            }
                          />
                        </label>
                        <small>
                          SHA256: {r.sha256 || "Select an original"}
                        </small>
                        <button
                          type="button"
                          onClick={() =>
                            item(index, {
                              evidence: i.evidence.filter((_, j) => j !== n),
                            })
                          }
                        >
                          Remove support
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      disabled={i.evidence.length >= 20}
                      onClick={() =>
                        item(index, {
                          evidence: [
                            ...i.evidence,
                            { artifact_id: "", sha256: "", locator: "" },
                          ],
                        })
                      }
                    >
                      Add retained support
                    </button>
                    {!d.predecessor && (
                      <button
                        type="button"
                        onClick={() =>
                          update({
                            items: d.items.filter((_, n) => n !== index),
                          })
                        }
                      >
                        Remove item
                      </button>
                    )}
                  </fieldset>
                ))}
              </div>
            </div>
            {d.predecessor && (
              <label>
                Correction rationale
                <textarea
                  required
                  maxLength={4000}
                  value={d.rationale}
                  onChange={(x) => update({ rationale: x.target.value })}
                />
              </label>
            )}
            <p>
              Locators and observations are your assertions; source bytes and
              pins are rechecked on save. Missing support is not a passing
              result.
            </p>
            {error && <p role="alert">{error}</p>}
            <button type="submit">
              {d.predecessor ? "Save correction" : "Save sample execution"}
            </button>
            <button type="button" onClick={() => setOpen(false)}>
              Cancel execution
            </button>
          </fieldset>
        </form>
      )}
      <p>{traces.length} retained execution revisions</p>
      <label>
        Find retained execution
        <input
          type="search"
          value={historySearch}
          onChange={(x) => {
            setHistorySearch(x.target.value);
            setHistoryPage(0);
          }}
        />
      </label>
      <p>
        Showing {Math.min(historyPage * 20 + 20, matchingTraces.length)} of{" "}
        {matchingTraces.length} matching revisions.
      </p>
      <button
        disabled={historyPage === 0}
        onClick={() => setHistoryPage(historyPage - 1)}
      >
        Previous executions
      </button>
      <button
        disabled={(historyPage + 1) * 20 >= matchingTraces.length}
        onClick={() => setHistoryPage(historyPage + 1)}
      >
        Next executions
      </button>
      {matchingTraces
        .slice(historyPage * 20, historyPage * 20 + 20)
        .map((t) => (
          <details key={String(t.id)}>
            <summary>
              {taskLabels.get(String(t.task_id)) ?? String(t.task_id)} ·
              revision {String(t.revision)}
            </summary>
            <p>
              Execution {String(t.id)} · Task {String(t.task_id)}
            </p>
            <p>
              Selection {String(t.selection_id)} · Workpaper{" "}
              {String(t.workpaper_id)} version {String(t.workpaper_version)} ·
              Predecessor {String(t.predecessor_id ?? "none")}
            </p>
            <p>{String(t.purpose)}</p>
            <p>{String(t.procedure)}</p>
            <p>
              Population {String(t.population_status ?? "UNKNOWN")} ·
              Independent review {String(t.independent_review)} · Automatic
              testing credit: false
            </p>
            {((t.items as Item[]) ?? []).map((i) => (
              <article key={i.item_id} className="sample-execution-observation">
                <h4>
                  {i.item_id} · {i.status}
                </h4>
                <p>{i.observation}</p>
                {i.evidence.length ? (
                  <details className="sample-evidence-references">
                    <summary>Evidence references ({i.evidence.length})</summary>
                    <ol>
                      {i.evidence.map((r, n) => (
                        <li key={n}>
                          <p>
                            <strong>{r.artifact_id}</strong>
                            {sourceLabels.get(r.artifact_id) !==
                              r.artifact_id &&
                              sourceLabels.has(r.artifact_id) &&
                              ` · ${sourceLabels.get(r.artifact_id)}`}
                          </p>
                          <p>{r.locator}</p>
                          <p>SHA256: {r.sha256}</p>
                        </li>
                      ))}
                    </ol>
                  </details>
                ) : (
                  <p>No evidence references recorded.</p>
                )}
              </article>
            ))}
            <details>
              <summary>Exact retained trace and lineage</summary>
              <pre>{JSON.stringify(t, null, 2)}</pre>
            </details>
            {p?.correctable_executions?.some(
              (pin) => pin.execution_id === t.id,
            ) && (
              <button
                disabled={busy}
                onClick={() => {
                  setD({
                    task: String(t.task_id),
                    selection: String(t.selection_id),
                    workpaper: `${t.workpaper_id}:${t.workpaper_version}`,
                    purpose: String(t.purpose),
                    procedure: String(t.procedure),
                    items: (t.items as Item[]).map((i) => ({
                      item_id: i.item_id,
                      observation: i.observation,
                      status: i.status,
                      evidence: i.evidence.map((r) => ({ ...r })),
                    })),
                    predecessor: String(t.id),
                    rationale: "",
                  });
                  setError("");
                  setOpen(true);
                }}
              >
                Correct this execution
              </button>
            )}
          </details>
        ))}
    </section>
  );
}
