import { DeferredPanel } from "./DeferredPanel";
import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "./api";
import type { Engagement, Row } from "./api";
import {
  contextsPath,
  contextAllowsOpen,
  investigationKinds,
  resolveContextLink,
  selectedVersion,
} from "./investigationContext";
import type {
  ContextLink,
  InvestigationKind,
  SavedInvestigation,
} from "./investigationContext";
export function InvestigationContexts(props: {
  engagement: Engagement;
  viewerId: string;
  onPreview: (kind: string, row: Row) => void;
}) {
  const key = JSON.stringify([
    props.viewerId,
    props.engagement.id,
    props.engagement.scope,
    props.engagement.permissions,
    props.engagement.company_source_binding,
    props.engagement.evidence_acquisition,
  ]);
  return (
    <DeferredPanel context={key} summary="Saved investigations">
      {(visible) => <ContextPanel key={key} {...props} visible={visible} />}
    </DeferredPanel>
  );
}
function ContextPanel({
  engagement: e,
  onPreview,
  visible,
}: {
  engagement: Engagement;
  viewerId: string;
  onPreview: (kind: string, row: Row) => void;
  visible: boolean;
}) {
  const [saved, setSaved] = useState<SavedInvestigation[]>([]),
    [editing, setEditing] = useState<SavedInvestigation | null>(null);
  const [form, setForm] = useState({
    title: "",
    question: "",
    next_step: "",
    links: [] as ContextLink[],
  });
  const [kind, setKind] = useState<InvestigationKind>("control"),
    [record, setRecord] = useState("");
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [conflict, setConflict] = useState(false);
  const [basisReviewed, setBasisReviewed] = useState(false);
  const alive = useRef(true), loadSequence = useRef(0);
  const pendingSave = useRef<{ signature: string; commandId: string } | null>(
    null,
  );
  const allowed = e.permissions?.some((p) =>
    ["learn", "instruct", "review"].includes(p),
  );
  const load = async () => {
    const token = ++loadSequence.current;
    const data = await request<{ contexts: SavedInvestigation[] }>(
      contextsPath(e.id),
    );
    if (alive.current && token === loadSequence.current) setSaved(data.contexts);
  };
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      loadSequence.current++;
    };
  }, []);
  useEffect(() => {
    if (!visible || !allowed) return;
    const token = loadSequence.current + 1;
    void load().catch((err) => {
      if (alive.current && token === loadSequence.current) setError(String(err.message));
    });
    return () => { loadSequence.current++; };
  }, [e.id, allowed, e.revision, visible]);
  const dirty =
    JSON.stringify(form) !==
    JSON.stringify(
      editing?.user ?? { title: "", question: "", next_step: "", links: [] },
    );
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (dirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  if (!allowed) return null;
  function edit(value: SavedInvestigation | null) {
    setEditing(value);
    setBasisReviewed(false);
    setForm(
      value
        ? structuredClone(value.user)
        : { title: "", question: "", next_step: "", links: [] },
    );
    setConflict(false);
    setError("");
  }
  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (err) {
      if (alive.current) {
        setError(
          err instanceof Error ? err.message : "Investigation unavailable",
        );
        if (err instanceof ApiError && err.status === 409) {
          setConflict(true);
          void load().catch(() => {});
        }
        if (err instanceof ApiError && [401, 403, 404].includes(err.status)) {
          setSaved([]);
          edit(null);
        }
      }
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  async function add() {
    const row = e[investigationKinds[kind]].find((r) => r.id === record);
    if (!row) return;
    const link = await request<ContextLink>(
      contextsPath(e.id) + "/link",
      "POST",
      { kind, id: row.id, version: selectedVersion(kind, row) },
    );
    if (alive.current)
      setForm((old) => ({
        ...old,
        links: [
          ...old.links.filter(
            (l) =>
              !(
                l.kind === link.kind &&
                l.id === link.id &&
                l.version === link.version
              ),
          ),
          link,
        ],
      }));
  }
  async function save() {
    if (editing && !contextAllowsOpen(editing) && !basisReviewed)
      throw new Error(
        "Review the current context before saving this investigation.",
      );
    const signature = JSON.stringify([editing?.id, editing?.version, form]);
    if (pendingSave.current?.signature !== signature)
      pendingSave.current = { signature, commandId: crypto.randomUUID() };
    const value = await request<SavedInvestigation>(
      contextsPath(e.id) +
        (editing ? "/" + encodeURIComponent(editing.id) : ""),
      editing ? "PUT" : "POST",
      {
        command_id: pendingSave.current.commandId,
        ...(editing ? { expected_version: editing.version } : {}),
        payload: form,
      },
    );
    if (alive.current) {
      pendingSave.current = null;
      edit(value);
      await load();
    }
  }
  return (
    <section aria-label="Saved investigations">
      <h2>Saved investigations</h2>
      <p>
        Your explicit questions, next steps and record links. These personal
        working contexts do not create findings, grades or formal workpapers.
        Unsaved edits remain in this panel until you save or discard them.
      </p>
      {error && <p role="alert">{error}</p>}
      {dirty && (
        <p>
          Unsaved investigation edits. Save them or explicitly discard the
          editor before switching investigations.
        </p>
      )}
      {conflict && (
        <p>
          Your text remains here. Another saved version or linked record
          changed. Inspect the current saved context before deliberately
          discarding this edit and reopening it.
        </p>
      )}
      <ul>
        {saved.map((context) => (
          <li key={context.id}>
            <strong>{context.user.title}</strong> · Version {context.version} ·{" "}
            Scope: {context.scope_status} · Company source and permission
            context: {context.context_status ?? "BASIS_UNRECORDED"}
            {!contextAllowsOpen(context) && (
              <p>
                Saved context differs from the current branch, acquisition
                settings, scope or permissions, or predates recorded context
                tracking. Original questions and pins remain unchanged. Review
                current records, then explicitly edit and save to record the
                current context.
              </p>
            )}
            <p>{context.user.question}</p>
            <p>Next step: {context.user.next_step || "Not specified"}</p>
            <button disabled={busy || dirty} onClick={() => edit(context)}>
              Edit saved investigation
            </button>
            <ul>
              {context.link_status.map(({ reference, status }) => {
                const row = resolveContextLink(e, reference, status);
                return (
                  <li key={reference.kind + reference.id + reference.version}>
                    {reference.kind} {reference.id} · pinned version{" "}
                    {reference.version ?? "record"} · {status}
                    <p>SHA256 {reference.sha256}</p>
                    <button
                      disabled={!row || !contextAllowsOpen(context)}
                      onClick={() => {
                        if (row && contextAllowsOpen(context))
                          onPreview(reference.kind, row);
                      }}
                    >
                      Open current record
                      {status === "HISTORICAL_VERSION_AVAILABLE"
                        ? " (historical pin shown above)"
                        : ""}
                    </button>
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ul>
      <button disabled={busy} onClick={() => edit(null)}>
        Discard editor and start new investigation
      </button>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void run(save);
        }}
      >
        <fieldset disabled={busy}>
          <h3>
            {editing
              ? `Editing version ${editing.version}`
              : "New investigation"}
          </h3>
          <label>
            Investigation title
            <input
              required
              maxLength={200}
              value={form.title}
              onChange={(event) =>
                setForm({ ...form, title: event.target.value })
              }
            />
          </label>
          <label>
            Your investigation question
            <textarea
              aria-label="Your investigation question"
              required
              maxLength={4000}
              value={form.question}
              onChange={(event) =>
                setForm({ ...form, question: event.target.value })
              }
            />
          </label>
          <label>
            Your next step
            <textarea
              aria-label="Your next step"
              maxLength={2000}
              value={form.next_step}
              onChange={(event) =>
                setForm({ ...form, next_step: event.target.value })
              }
            />
          </label>
          <label>
            Link record type
            <select
              aria-label="Link record type"
              value={kind}
              onChange={(event) => {
                setKind(event.target.value as InvestigationKind);
                setRecord("");
              }}
            >
              {Object.keys(investigationKinds).map((k) => (
                <option key={k}>{k}</option>
              ))}
            </select>
          </label>
          <label>
            Existing record
            <select
              aria-label="Existing record"
              value={record}
              onChange={(event) => setRecord(event.target.value)}
            >
              <option value="">Choose record</option>
              {e[investigationKinds[kind]].map((row) => (
                <option key={row.id} value={row.id}>
                  {row.id} · {String(row.title ?? row.name ?? "")}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={busy || !record || form.links.length >= 24}
            onClick={() => void run(add)}
          >
            Pin selected record
          </button>
          <ul>
            {form.links.map((link, index) => (
              <li key={link.kind + link.id + link.version}>
                {link.kind} {link.id} · version {link.version ?? "record"}
                <button
                  type="button"
                  onClick={() =>
                    setForm({
                      ...form,
                      links: form.links.filter((_, i) => i !== index),
                    })
                  }
                >
                  Remove link {link.id}
                </button>
              </li>
            ))}
          </ul>
          {editing && !contextAllowsOpen(editing) && (
            <label>
              <input
                type="checkbox"
                checked={basisReviewed}
                onChange={(event) => setBasisReviewed(event.target.checked)}
              />
              I reviewed the current company source, acquisition settings,
              permissions and original record pins.
            </label>
          )}
          <button
            disabled={
              busy ||
              conflict ||
              (!!editing && !contextAllowsOpen(editing) && !basisReviewed)
            }
          >
            Save investigation
          </button>
          {editing && (
            <button
              type="button"
              disabled={busy || conflict}
              onClick={() =>
                void run(async () => {
                  await request(
                    contextsPath(e.id) + "/" + editing.id + "/reset",
                    "POST",
                    {
                      command_id: crypto.randomUUID(),
                      expected_version: editing.version,
                    },
                  );
                  if (alive.current) {
                    edit(null);
                    await load();
                  }
                })
              }
            >
              Reset saved investigation
            </button>
          )}
        </fieldset>
      </form>
    </section>
  );
}
