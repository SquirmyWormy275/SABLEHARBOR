import { useEffect, useRef, useState, type ReactNode } from "react";
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
export function Table({
  rows,
  columns,
  onOpen,
}: {
  rows: Row[];
  columns: { key: string; label: string; render?: (row: Row) => ReactNode }[];
  onOpen?: (row: Row) => void;
}) {
  const [query, setQuery] = useState(""),
    [page, setPage] = useState(0),
    [sort, setSort] = useState("");
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
  useEffect(() => setPage(0), [query, rows.length]);
  return (
    <div className="record-table">
      <div className="table-tools">
        <label className="search">
          Search records
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
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
                    onClick={() => setSort(c.key)}
                    aria-label={`Sort by ${c.label}`}
                  >
                    {c.label} {sort === c.key ? "↓" : ""}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.slice(page * 25, page * 25 + 25).map((row) => (
              <tr key={row.id}>
                {columns.map((c, i) => (
                  <td key={c.key}>
                    {c.render ? (
                      c.render(row)
                    ) : i === 0 && onOpen ? (
                      <button className="text-link" onClick={() => onOpen(row)}>
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
        <Empty title="No matching records">
          Adjust your search or create the first record.
        </Empty>
      )}
      <div className="pagination">
        <button disabled={page === 0} onClick={() => setPage((n) => n - 1)}>
          Previous
        </button>
        <span>
          Page {page + 1} of {pages}
        </span>
        <button
          disabled={page + 1 >= pages}
          onClick={() => setPage((n) => n + 1)}
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
};
export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current!;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <div className="modal-title">
        <h2>{title}</h2>
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
}: {
  action: Action;
  busy: boolean;
  onSubmit: (value: Record<string, unknown>) => Promise<void>;
  onClose: () => void;
}) {
  const [value, setValue] = useState<Record<string, unknown>>(
    action.initial ?? {},
  );
  return (
    <Modal title={action.title} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void onSubmit(value);
        }}
      >
        {action.description && <p className="muted">{action.description}</p>}
        <div className="form-grid">
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
                    setValue({ ...value, [field.name]: e.target.value })
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
                    setValue({ ...value, [field.name]: e.target.value })
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
                    setValue({ ...value, [field.name]: e.target.checked })
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
                    setValue({
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
        </div>
        <div className="form-footer">
          <button type="button" onClick={onClose}>
            Cancel
          </button>
          <button className="primary" disabled={busy} type="submit">
            {busy ? "Saving…" : (action.submit ?? "Save record")}
          </button>
        </div>
      </form>
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
