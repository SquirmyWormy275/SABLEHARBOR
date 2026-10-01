import { useDurableDraft } from "./useDurableDraft";
import { useTableMemory } from "./TableWorkspace";
import { formDraftFields } from "./durableDraft";
import { withoutSourceLinks } from "./draftContext";
import type { DraftStore, DraftKey, DraftLookup } from "./draftContext";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { human, str, type Row } from "./api";
export function Badge({ children }: { children: ReactNode }) {
  return <span className="badge">{children}</span>;
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}
type TableProps = {
  rows: Row[];
  columns: {
    key: string;
    label: string;
    render?: (row: Row, sequence: string[]) => ReactNode;
  }[];
  onOpen?: (row: Row, sequence: string[]) => void;
  memoryKey?: string;
};
export function Table(props: TableProps) {
  return <RecordTable key={props.memoryKey} {...props} />;
}
function RecordTable({ rows, columns, onOpen, memoryKey }: TableProps) {
  const memory = useTableMemory();
  const [initial] = useState(() =>
    memory && memoryKey
      ? memory.read(memoryKey)
      : { query: "", page: 0, sort: "" },
  );
  const [query, setQuery] = useState(initial.query),
    [page, setPage] = useState(initial.page),
    [sort, setSort] = useState(
      columns.some((c) => c.key === initial.sort) ? initial.sort : "",
    );
  const [restored, setRestored] = useState<{
    page: number;
    sort: string;
  } | null>(() => (memory && memoryKey ? memory.restoration(memoryKey) : null));
  useEffect(() => {
    if (!memory || !memoryKey) return;
    return memory.subscribe(memoryKey, (value) => {
      setQuery(value.query);
      setPage(value.page);
      setSort(columns.some((c) => c.key === value.sort) ? value.sort : "");
      setRestored({ page: value.page, sort: value.sort });
    });
  }, [memory, memoryKey, columns]);
  function dismissRestoreNotice() {
    setRestored(null);
    if (memory && memoryKey) memory.dismissRestoration(memoryKey);
  }
  const filtered = rows
    .filter((r) =>
      columns.some((c) =>
        str(r[c.key]).toLowerCase().includes(query.toLowerCase()),
      ),
    )
    .sort((a, b) =>
      sort
        ? str(a[sort]).localeCompare(str(b[sort]), undefined, { numeric: true })
        : 0,
    );
  const pages = Math.max(1, Math.ceil(filtered.length / 25));
  const sequence = filtered.map((row) => row.id);
  const currentPage = Math.min(page, pages - 1);
  useEffect(() => {
    if (memory && memoryKey)
      memory.write(memoryKey, { query, page: currentPage, sort });
  }, [memory, memoryKey, query, currentPage, sort]);
  return (
    <div className="record-table">
      {restored && (
        <p role="status">
          Saved table navigation restored.
          {restored.page !== currentPage &&
            ` Page adjusted from ${restored.page + 1} to ${currentPage + 1} for current visible records.`}
          {restored.sort !== sort &&
            " Saved sort column is unavailable; showing original order."}
        </p>
      )}
      <div className="table-tools">
        <label className="search">
          Search records
          <input
            type="search"
            value={query}
            maxLength={1000}
            onChange={(e) => {
              dismissRestoreNotice();
              setQuery(e.target.value);
              setPage(0);
            }}
            placeholder="Identifier, owner or description"
          />
        </label>
        <span>{filtered.length.toLocaleString()} records</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key}>
                  <button
                    onClick={() => {
                      dismissRestoreNotice();
                      setSort(c.key);
                      setPage(0);
                    }}
                    aria-label={`Sort by ${c.label}`}
                  >
                    {c.label} {sort === c.key ? "↓" : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered
              .slice(currentPage * 25, currentPage * 25 + 25)
              .map((row) => (
                <tr key={row.id}>
                  {columns.map((c, i) => (
                    <td key={c.key}>
                      {c.render ? (
                        c.render(row, sequence)
                      ) : i === 0 && onOpen ? (
                        <button
                          className="text-link"
                          onClick={() =>
                            onOpen(row, sequence)
                          }
                        >
                          {str(row[c.key])}
                        </button>
                      ) : (
                        str(row[c.key])
                      )}
                    </td>
                  ))}
                </tr>
              ))}
          </tbody>
        </table>
      </div>
      {!filtered.length && (
        <Empty
          title={query ? "No records match this search" : "No records yet"}
        >
          {query ? (
            <>
              Search: “{query}”.{" "}
              <button
                onClick={() => {
                  dismissRestoreNotice();
                  setQuery("");
                  setPage(0);
                }}
              >
                Clear table search
              </button>
            </>
          ) : (
            "Records appear here as work is recorded or evidence is collected."
          )}
        </Empty>
      )}
      <div className="pagination">
        <button
          disabled={currentPage === 0}
          onClick={() => {
            dismissRestoreNotice();
            setPage(currentPage - 1);
          }}
        >
          Previous
        </button>
        <span>
          Page {currentPage + 1} of {pages}
        </span>
        <button
          disabled={currentPage + 1 >= pages}
          onClick={() => {
            dismissRestoreNotice();
            setPage(currentPage + 1);
          }}
        >
          Next
        </button>
      </div>
    </div>
  );
}
export type Field = {
  name: string;
  label: string;
  type?: "text" | "textarea" | "select" | "date" | "number" | "checkbox";
  options?: { value: string; label: string }[];
  required?: boolean;
  hint?: string;
};
export type Action = {
  title: string;
  kind: string;
  fields: Field[];
  initial?: Record<string, unknown>;
  description?: string;
  submit?: string;
  sourceBasis?: string;
};
export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current!;
    const opener =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    dialog.showModal();
    return () => {
      dialog.close();
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className={wide ? "modal modal-wide" : "modal"}
      aria-labelledby={titleId}
      tabIndex={-1}
      onKeyDown={(event) => {
        const dialog = event.currentTarget;
        if (
          event.key !== "Tab" ||
          event.altKey ||
          event.ctrlKey ||
          event.metaKey ||
          (event.target as HTMLElement).closest("dialog") !== dialog
        )
          return;
        const candidates = Array.from(
          dialog.querySelectorAll<HTMLElement>(
            "a[href],button,input,select,textarea,summary,[tabindex]",
          ),
        ).filter(
          (el) =>
            el.tabIndex >= 0 &&
            !el.matches(":disabled") &&
            !el.closest("[inert]") &&
            !Array.from(dialog.querySelectorAll("details:not([open])")).some(
              (details) =>
                details.contains(el) &&
                !details.querySelector(":scope > summary")?.contains(el),
            ) &&
            el.getClientRects().length > 0 &&
            getComputedStyle(el).visibility === "visible",
        );
        // Positive tabindex order precedes ordinary document-order stops.
        candidates.sort(
          (a, b) => (a.tabIndex || Infinity) - (b.tabIndex || Infinity),
        );
        const first = candidates[0],
          last = candidates.at(-1);
        if (!first) {
          event.preventDefault();
          dialog.focus();
          return;
        }
        if (
          event.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === dialog)
        ) {
          event.preventDefault();
          last?.focus();
        } else if (
          !event.shiftKey &&
          (document.activeElement === last || document.activeElement === dialog)
        ) {
          event.preventDefault();
          first.focus();
        }
      }}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <div className="modal-title">
        <h2 id={titleId}>{title}</h2>
        <button aria-label="Close dialog" onClick={onClose}>
          ✕
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function ActionForm({
  action,
  busy,
  onSubmit,
  onClose,
  draft,
  onDraftCleanupFailure,
  submitError,
  support,
  sourceContextStale = false,
  onReviewSource,
}: {
  action: Action;
  draft?: {
    store: DraftStore;
    remote?: boolean;
    key: DraftKey;
    initial: Record<string, unknown>;
  };
  busy: boolean;
  onSubmit: (
    value: Record<string, unknown>,
    afterFormalSave?: () => Promise<boolean>,
  ) => Promise<boolean | void>;
  onDraftCleanupFailure?: () => void;
  submitError?: string;
  sourceContextStale?: boolean;
  onReviewSource?: () => void;
  support?: (
    values: Record<string, unknown>,
    onChange: (values: Record<string, unknown>) => void,
    editable: boolean,
  ) => ReactNode;
  onClose: () => void;
}) {
  const [restored] = useState<DraftLookup>(() =>
    draft ? draft.store.lookup(draft.key) : { status: "EMPTY" },
  );
  const initial = draft?.initial ?? action.initial ?? {};
  const [value, setValue] = useState<Record<string, unknown>>({
    ...initial,
    ...(restored.status === "EMPTY" ? {} : restored.draft.values),
  });
  const [stale, setStale] = useState(restored.status === "STALE_BASE");
  const [sourceNeedsReview, setSourceNeedsReview] = useState(
    restored.status === "STALE_SOURCE",
  );
  const sourceBlocked = sourceContextStale || sourceNeedsReview;
  const [draftError, setDraftError] = useState("");
  const [baseKey, setBaseKey] = useState(
    restored.status !== "EMPTY" ? restored.draft.key : draft?.key,
  );
  const durable = useDurableDraft(
    draft?.remote ? draft.key : undefined,
    (saved) => {
      if (!draft) return;
      // A changed-context row has no fields by contract. Keep any already
      // authored volatile text visible; never replace it with blank fields.
      if (saved.status === "STALE") return;
      if (saved.status === "STALE_SOURCE") {
        if (restored.status === "EMPTY")
          setValue(withoutSourceLinks({ ...initial, ...formDraftFields(saved.fields ?? {}) }));
        setSourceNeedsReview(true);
        return;
      }
      if (
        sourceContextStale ||
        draft.store.lookup(draft.key).status === "STALE_SOURCE"
      ) {
        setSourceNeedsReview(true);
        return;
      }
      const fields = formDraftFields(saved.fields ?? {});
      const sourceKey = {
        ...draft.key,
        baseVersion:
          saved.base_workpaper_version == null
            ? "NEW"
            : String(saved.base_workpaper_version),
      };
      setBaseKey(sourceKey);
      setValue({ ...initial, ...fields });
      setStale(
        saved.status === "DRAFT" &&
          (saved.workpaper_stale === true ||
            sourceKey.baseVersion !== draft.key.baseVersion),
      );
      setDraftError("");
      if (saved.status === "DRAFT") draft.store.save(sourceKey, fields);
    },
  );
  function update(next: Record<string, unknown>) {
    if (sourceBlocked) return;
    setValue(next);
    if (!draft) return;
    try {
      const target = stale && baseKey ? baseKey : draft.key;
      draft.store.save(target, next);
      durable.schedule(next, target);
      setDraftError("");
    } catch (error) {
      setDraftError((error as Error).message);
    }
  }
  function close() {
    if (sourceBlocked || durable.blocked) {
      onClose();
      return;
    }
    if (!draftError)
      void durable.flush().then((ok) => {
        if (ok) onClose();
      });
  }
  async function submit() {
    if (stale || sourceBlocked || durable.blocked || draftError || !(await durable.flush())) return;
    await onSubmit(
      value,
      draft
        ? async () => {
            const cleaned = await durable.discard();
            if (!cleaned) onDraftCleanupFailure?.();
            return cleaned;
          }
        : undefined,
    );
  }
  return (
    <Modal title={action.title} onClose={close} wide={Boolean(support)}>
      <div className={support ? "workpaper-editor" : undefined}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!stale && !sourceBlocked && !draftError) void submit();
          }}
        >
          {action.description && <p className="muted">{action.description}</p>}
          {draft && (
            <p role="status">
              {draft.remote ? (
                <>
                  {durable.status} Personal draft text is stored separately from
                  submitted audit records. Current-context saved drafts can be
                  recovered after reload. Changed source or acquisition
                  context requires fresh source review before old links can be
                  used; a stale saved copy must be explicitly discarded.
                </>
              ) : (
                <>
                  Draft retained only in this open workroom. Closing this form
                  keeps it in memory; reloading, signing out or changing
                  workroom context clears it. This service does not support
                  saved personal drafts.
                </>
              )}
            </p>
          )}
          {submitError && (
            <p role="alert" className="error">
              {submitError}
            </p>
          )}
          {draft && durable.error && <p role="alert">{durable.error}</p>}
          {draft && !durable.ready && (
            <button type="button" onClick={() => void durable.retry()}>
              Retry loading personal draft
            </button>
          )}
          {draft && durable.remote && (
            <div role="alert">
              <strong>Saved draft conflict or changed context</strong>
              {durable.remote.fields && (
                <details>
                  <summary>Inspect saved draft from the other session</summary>
                  <dl>
                    {Object.entries(formDraftFields(durable.remote.fields)).map(
                      ([field, text]) => (
                        <div key={field}>
                          <dt>{field}</dt>
                          <dd>{String(text)}</dd>
                        </div>
                      ),
                    )}
                  </dl>
                </details>
              )}
              {!["STALE", "STALE_SOURCE"].includes(durable.remote.status) && (
                <>
                  <button type="button" onClick={durable.useRemote}>
                    Replace this form with the saved draft
                  </button>
                  <button type="button" onClick={durable.keepLocal}>
                    Keep this form; replace the inspected saved draft
                  </button>
                </>
              )}
            </div>
          )}
          {draftError && (
            <p role="alert">
              Draft not retained: {draftError} Keep this form open, shorten the
              text or explicitly discard it.
            </p>
          )}
          {draft && stale && (
            <div role="alert">
              <strong>
                Stale base: draft version {baseKey?.baseVersion ?? "unknown"};
                current version {draft.key.baseVersion}.
              </strong>
              <p>
                Inspect the current saved base before reusing this draft. Saving
                is disabled until you explicitly review or discard it.
              </p>
              <details>
                <summary>Inspect current saved base</summary>
                <dl>
                  {action.fields.map((field) => (
                    <div key={field.name}>
                      <dt>{field.label}</dt>
                      <dd>{String(initial[field.name] ?? "")}</dd>
                    </div>
                  ))}
                </dl>
              </details>
              <button
                type="button"
                disabled={sourceBlocked || durable.blocked}
                onClick={() => {
                  if (sourceBlocked || durable.blocked) return;
                  try {
                    draft.store.save(draft.key, value);
                    setBaseKey(draft.key);
                    durable.schedule(value, draft.key);
                    setStale(false);
                    setDraftError("");
                  } catch (error) {
                    setDraftError((error as Error).message);
                  }
                }}
              >
                I reviewed the current base; use this draft
              </button>
            </div>
          )}
          {sourceBlocked && (
            <div role="alert">
              <strong>Source context changed.</strong>
              {draft ? (
                <p>
                  Your authored text is retained. Earlier evidence, task,
                  control and message links will be cleared before reuse.
                  Inspect current originals and reselect any support you still
                  need. Carrying text forward does not record an inspection.
                </p>
              ) : (
                <p>
                  This action was opened under an earlier source context. Close
                  it and reopen the current record before submitting. Its old
                  selections cannot be rebased here.
                </p>
              )}
              {draft && (
                <button
                  type="button"
                  disabled={!durable.ready}
                  onClick={async () => {
                    // A saved stale row must be explicitly discarded; its fields
                    // are withheld by the service and cannot be silently rebased.
                    if (durable.blocked && !(await durable.discard())) return;
                    try {
                      const retained = withoutSourceLinks(value);
                      const current = draft.store.lookup(draft.key);
                      if (current.status === "STALE_SOURCE")
                        draft.store.reviewSource(draft.key);
                      draft.store.save(draft.key, retained);
                      durable.schedule(retained, draft.key);
                      setValue(retained);
                      setBaseKey(draft.key);
                      setSourceNeedsReview(false);
                      setDraftError("");
                      onReviewSource?.();
                    } catch (error) {
                      setDraftError((error as Error).message);
                    }
                  }}
                >
                  {durable.blocked
                    ? "Keep my text; clear old links and discard stale saved copy"
                    : "Keep my text and clear old source links"}
                </button>
              )}
            </div>
          )}
          {draft && (
            <button
              type="button"
              onClick={async () => {
                if (!(await durable.discard())) return;
                draft.store.discardObject(draft.key);
                setValue({ ...initial });
                setStale(false);
                setSourceNeedsReview(false);
                setDraftError("");
                if (sourceContextStale) onClose();
              }}
            >
              Discard unsaved draft
            </button>
          )}
          <fieldset className="form-grid" disabled={sourceBlocked || durable.blocked || (!!draft && !durable.ready)}>
            {action.fields.map((field) => (
              <label
                key={field.name}
                className={field.type === "textarea" ? "wide" : ""}
              >
                {field.label}
                {field.type === "textarea" ? (
                  <textarea
                    aria-label={field.label}
                    rows={5}
                    required={field.required}
                    value={
                      value[field.name] === undefined
                        ? ""
                        : String(value[field.name])
                    }
                    onChange={(e) =>
                      update({ ...value, [field.name]: e.target.value })
                    }
                  />
                ) : field.type === "select" ? (
                  <select
                    aria-label={field.label}
                    required={field.required}
                    value={
                      value[field.name] === undefined
                        ? ""
                        : String(value[field.name])
                    }
                    onChange={(e) =>
                      update({ ...value, [field.name]: e.target.value })
                    }
                  >
                    <option value="">Select…</option>
                    {field.options?.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                ) : field.type === "checkbox" ? (
                  <input
                    aria-label={field.label}
                    type="checkbox"
                    checked={Boolean(value[field.name])}
                    onChange={(e) =>
                      update({ ...value, [field.name]: e.target.checked })
                    }
                  />
                ) : (
                  <input
                    aria-label={field.label}
                    step="any"
                    type={field.type ?? "text"}
                    required={field.required}
                    value={
                      value[field.name] === undefined
                        ? ""
                        : String(value[field.name])
                    }
                    onChange={(e) =>
                      update({
                        ...value,
                        [field.name]:
                          field.type === "number"
                            ? Number(e.target.value)
                            : e.target.value,
                      })
                    }
                  />
                )}
                <small>{field.hint}</small>
              </label>
            ))}
          </fieldset>
          <div className="form-footer">
            <button type="button" onClick={close}>
              {draft ? "Close (keep draft)" : "Cancel"}
            </button>
            <button
              className="primary"
              disabled={
                busy ||
                stale ||
                sourceBlocked ||
                !!draftError ||
                !durable.ready ||
                durable.blocked
              }
              type="submit"
            >
              {busy ? "Saving…" : (action.submit ?? "Save record")}
            </button>
          </div>
        </form>
        {support && (
          <div className="workpaper-inspection">
            {support(
              value,
              update,
              !busy &&
                !stale &&
                !sourceBlocked &&
                !draftError &&
                durable.ready &&
                !durable.blocked,
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
export function Detail({
  row,
  title,
  onClose,
  children,
}: {
  row: Row;
  title: string;
  onClose: () => void;
  children?: ReactNode;
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <dl className="details">
        {Object.entries(row)
          .filter(
            ([, v]) =>
              typeof v !== "object" ||
              (Array.isArray(v) && v.every((x) => typeof x !== "object")),
          )
          .map(([key, value]) => (
            <div key={key}>
              <dt>{human(key)}</dt>
              <dd>{str(value)}</dd>
            </div>
          ))}
      </dl>
      {children}
    </Modal>
  );
}
