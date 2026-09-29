import { useEffect, useRef, useState } from "react";
import { ApiError, request } from "./api";
import type { Engagement, Row } from "./api";
import { investigationKinds, selectedVersion } from "./investigationContext";
import type { ContextLink, InvestigationKind } from "./investigationContext";
import type { SavedViewReferenceDescriptor } from "./savedViews";
import {
  currentHandoff,
  freezeHandoffCommand,
  handoffAuthority,
  handoffLinkKey,
  handoffsPath,
  handoffWaiting,
  resolveHandoffReference,
} from "./investigationHandoffs";
import type { Handoff, PendingHandoffCommand } from "./investigationHandoffs";
type Props = {
  engagement: Engagement;
  viewerId: string;
  enabled: boolean;
  onPreview: (kind: string, row: Row, reference?: Row) => void;
  selectedReference?: SavedViewReferenceDescriptor | null;
};
type Member = { id: string; display_name: string; permission: string };
const labels: Record<string, string> = {
  ACCEPT: "Accept investigation",
  DECLINE: "Decline",
  WITHDRAW: "Withdraw offer",
  COMPLETE: "Send completion response",
};
export function InvestigationHandoffs(props: Props) {
  if (
    !props.enabled ||
    !props.engagement.permissions?.some((p) =>
      ["learn", "review", "instruct"].includes(p),
    )
  )
    return null;
  return (
    <details className="panel">
      <summary>Share an investigation</summary>
      <HandoffPanel
        key={handoffAuthority(props.engagement, props.viewerId)}
        {...props}
      />
    </details>
  );
}
function HandoffPanel({
  engagement: e,
  viewerId,
  onPreview,
  selectedReference,
}: Props) {
  const [members, setMembers] = useState<Member[]>([]),
    [items, setItems] = useState<Handoff[]>([]);
  const [form, setForm] = useState({
    recipient_id: "",
    title: "",
    question: "",
    next_step: "",
    links: [] as ContextLink[],
  });
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [kind, setKind] = useState<InvestigationKind>("artifact"),
    [record, setRecord] = useState(""),
    [version, setVersion] = useState<number | null>(null),
    [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [basis, setBasis] = useState(e.revision),
    [loaded, setLoaded] = useState<number | null>(null),
    [conflict, setConflict] = useState(false);
  const [pending, setPending] = useState<PendingHandoffCommand | null>(null);
  const live = useRef(true),
    epoch = useRef(0),
    revision = useRef(e.revision);
  revision.current = e.revision;
  const path = handoffsPath(e.id),
    current = loaded === e.revision;
  async function load() {
    setLoaded(null);
    const token = ++epoch.current,
      rev = e.revision;
    const [directory, list] = await Promise.all([
      request<{
        engagement_id: string;
        engagement_revision: number;
        members: Member[];
      }>(path + "/members"),
      request<{ handoffs: Handoff[] }>(path),
    ]);
    if (!live.current || token !== epoch.current || revision.current !== rev)
      return false;
    if (
      directory.engagement_id !== e.id ||
      directory.engagement_revision !== rev ||
      !list.handoffs.every((h) => currentHandoff(h, e, viewerId))
    )
      throw Error("Workspace changed. Refresh the investigation list.");
    setMembers(directory.members);
    setItems(list.handoffs);
    setLoaded(rev);
    return true;
  }
  useEffect(() => {
    live.current = true;
    void load().catch((x) => {
      if (live.current) setError(x.message);
    });
    return () => {
      live.current = false;
      epoch.current++;
    };
  }, [e.revision]);
  const dirty = Boolean(
    form.title ||
    form.question ||
    form.next_step ||
    form.links.length ||
    Object.values(responses).some(Boolean),
  );
  useEffect(() => {
    const warn = (ev: BeforeUnloadEvent) => {
      if (dirty) {
        ev.preventDefault();
        ev.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  async function refresh() {
    setBusy(true);
    setError("");
    try {
      if (await load()) {
        setConflict(false);
        setPending(null);
        setBasis(e.revision);
        setForm((f) => ({ ...f, links: [] }));
        setNotice(
          "Current workspace reviewed. Text retained; explicitly add links again before offering.",
        );
      }
    } catch (x) {
      if (live.current) setError((x as Error).message);
    } finally {
      if (live.current) setBusy(false);
    }
  }
  async function pin(descriptor: SavedViewReferenceDescriptor) {
    setBusy(true);
    setError("");
    const rev = e.revision;
    try {
      const link = await request<ContextLink>(path + "/link", "POST", {
        recipient_id: form.recipient_id,
        ...descriptor,
      });
      if (!live.current || revision.current !== rev) return;
      if (
        link.kind !== descriptor.kind ||
        link.id !== descriptor.id ||
        link.version !== descriptor.version ||
        !resolveHandoffReference(e, link, "EXACT_PIN_AVAILABLE")
      )
        throw Error("The selected exact reference is no longer available.");
      setForm((f) => ({
        ...f,
        links: f.links.some((x) => handoffLinkKey(x) === handoffLinkKey(link))
          ? f.links
          : [...f.links, link],
      }));
    } catch (x) {
      if (live.current) setError((x as Error).message);
    } finally {
      if (live.current) setBusy(false);
    }
  }
  async function send(command: PendingHandoffCommand) {
    setPending(command);
    setBusy(true);
    setError("");
    const rev = e.revision;
    try {
      const value = await request<Handoff>(command.path, "POST", command.body);
      if (!live.current || revision.current !== rev) return;
      if (!currentHandoff(value, e, viewerId))
        throw Error("Workspace changed; refresh before reviewing the result.");
      setPending(null);
      setConflict(false);
      if (command.path === path) {
        setForm({
          recipient_id: "",
          title: "",
          question: "",
          next_step: "",
          links: [],
        });
        setNotice("Investigation offered to the selected member.");
      } else {
        setResponses((r) => ({ ...r, [value.id]: "" }));
        setNotice(
          "Coordination response recorded. Audit tasks and conclusions are unchanged.",
        );
      }
      await load();
    } catch (x) {
      if (live.current) {
        setError((x as Error).message);
        if (x instanceof ApiError && x.status === 409) {
          setConflict(true);
          setPending(null);
        }
      }
    } finally {
      if (live.current) setBusy(false);
    }
  }
  function offer() {
    void send(
      freezeHandoffCommand(path, {
        payload: form,
        expected_engagement_revision: e.revision,
        command_id: crypto.randomUUID(),
      }),
    );
  }
  function transition(h: Handoff, action: string) {
    void send(
      freezeHandoffCommand(
        path + "/" + encodeURIComponent(h.id) + "/transition",
        {
          action,
          response: responses[h.id] ?? "",
          expected_version: h.version,
          expected_engagement_revision: e.revision,
          command_id: crypto.randomUUID(),
        },
      ),
    );
  }
  const stale = basis !== e.revision || conflict;
  const available = (e[investigationKinds[kind]] as Row[]).filter((r) =>
    [r.id, r.title, r.name].some((v) =>
      String(v ?? "")
        .toLowerCase()
        .includes(query.toLowerCase()),
    ),
  );
  const choices = available.slice(0, 50),
    chosen = (e[investigationKinds[kind]] as Row[]).find(
      (r) => r.id === record,
    );
  const selected =
    chosen && !choices.some((r) => r.id === chosen.id)
      ? [chosen, ...choices]
      : choices;
  return (
    <div>
      <p>
        Ask another workspace member a specific question. Only your written
        message and selected record links are shared.
      </p>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      {stale && (
        <p role="status">
          The workspace or handoff changed. Your text is retained. Refresh and
          review before sending.
        </p>
      )}
      <button type="button" disabled={busy} onClick={() => void refresh()}>
        Refresh and review current workspace
      </button>
      {pending && (
        <div>
          <p>
            An offer or response may already have been recorded. Retry the same
            command to check its outcome.
          </p>
          <button
            type="button"
            disabled={busy || stale}
            onClick={() => void send(pending)}
          >
            Retry exact submission
          </button>
        </div>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          offer();
        }}
      >
        <fieldset disabled={busy || Boolean(pending)}>
          <legend>Offer an investigation</legend>
          <label>
            Recipient
            <select
              aria-label="Investigation recipient"
              value={form.recipient_id}
              onChange={(ev) =>
                setForm((f) => ({
                  ...f,
                  recipient_id: ev.target.value,
                  links: [],
                }))
              }
            >
              <option value="">Choose a workspace member</option>
              {current &&
                members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name} ({m.permission})
                  </option>
                ))}
            </select>
          </label>
          <label>
            Title
            <input
              aria-label="Investigation title"
              maxLength={120}
              value={form.title}
              onChange={(ev) =>
                setForm((f) => ({ ...f, title: ev.target.value }))
              }
            />
          </label>
          <label>
            Question
            <textarea
              aria-label="Investigation question"
              maxLength={2000}
              value={form.question}
              onChange={(ev) =>
                setForm((f) => ({ ...f, question: ev.target.value }))
              }
            />
          </label>
          <label>
            Suggested next step
            <textarea
              aria-label="Investigation next step"
              maxLength={1000}
              value={form.next_step}
              onChange={(ev) =>
                setForm((f) => ({ ...f, next_step: ev.target.value }))
              }
            />
          </label>
          <fieldset
            disabled={
              stale || !current || !form.recipient_id || form.links.length >= 8
            }
          >
            <legend>Explicit record links (up to eight)</legend>
            {selectedReference && (
              <button type="button" onClick={() => void pin(selectedReference)}>
                Add selected {selectedReference.kind} {selectedReference.id}
                {selectedReference.version !== null
                  ? ` v${selectedReference.version}`
                  : ""}
              </button>
            )}
            <label>
              Record type
              <select
                aria-label="Handoff record type"
                value={kind}
                onChange={(ev) => {
                  setKind(ev.target.value as InvestigationKind);
                  setRecord("");
                  setVersion(null);
                }}
              >
                {Object.keys(investigationKinds).map((k) => (
                  <option key={k}>{k}</option>
                ))}
              </select>
            </label>
            <label>
              Find a record
              <input
                aria-label="Find handoff record"
                value={query}
                onChange={(ev) => setQuery(ev.target.value)}
              />
            </label>
            <p>
              {available.length} matching records; showing up to 50. Refine the
              search if needed.
            </p>
            <label>
              Record
              <select
                aria-label="Handoff record"
                value={record}
                onChange={(ev) => {
                  setRecord(ev.target.value);
                  const row = (e[investigationKinds[kind]] as Row[]).find(
                    (r) => r.id === ev.target.value,
                  );
                  setVersion(row ? selectedVersion(kind, row) : null);
                }}
              >
                <option value="">Choose a record</option>
                {selected.map((r) => (
                  <option key={r.id} value={r.id}>
                    {String(r.title ?? r.name ?? r.id)} · {r.id}
                  </option>
                ))}
              </select>
            </label>
            {kind === "workpaper" && chosen && (
              <label>
                Retained version
                <select
                  aria-label="Handoff workpaper version"
                  value={version ?? ""}
                  onChange={(ev) => setVersion(Number(ev.target.value))}
                >
                  {(chosen.versions as Row[]).map((v) => (
                    <option key={String(v.version)} value={Number(v.version)}>
                      Version {String(v.version)}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <button
              type="button"
              disabled={!record}
              onClick={() => void pin({ kind, id: record, version })}
            >
              Add exact record link
            </button>
          </fieldset>
          <ul>
            {form.links.map((link, i) => (
              <li key={handoffLinkKey(link)}>
                {link.kind} {link.id} v{link.version ?? "unversioned"}{" "}
                <code>{link.sha256}</code>
                <button
                  type="button"
                  onClick={() =>
                    setForm((f) => ({
                      ...f,
                      links: f.links.filter((_, index) => index !== i),
                    }))
                  }
                >
                  Remove {link.id}
                </button>
              </li>
            ))}
          </ul>
          <button
            type="submit"
            disabled={
              stale ||
              !current ||
              !form.recipient_id ||
              !form.title.trim() ||
              !form.question.trim() ||
              !form.next_step.trim()
            }
          >
            Offer investigation
          </button>
          <button
            type="button"
            onClick={() => {
              setForm({
                recipient_id: "",
                title: "",
                question: "",
                next_step: "",
                links: [],
              });
              setBasis(e.revision);
              setConflict(false);
            }}
          >
            Discard offer text
          </button>
        </fieldset>
      </form>
      <h4>Investigations involving you</h4>
      {!current ? (
        <p>Loading current participant records…</p>
      ) : items.length === 0 ? (
        <p>No investigations shared yet.</p>
      ) : (
        items.map((h) => (
          <article key={h.id} className="panel">
            <h5>
              {h.shared_content_visible && h.context_status === "CURRENT"
                ? (h.content?.title ?? "Shared investigation")
                : "Shared investigation unavailable"}
            </h5>
            <p>
              {handoffWaiting(h, viewerId)} · {h.status} · version {h.version}
            </p>
            <p>
              From{" "}
              {members.find((m) => m.id === h.sender_id)?.display_name ??
                (h.sender_id === viewerId ? "you" : h.sender_id)}{" "}
              to{" "}
              {members.find((m) => m.id === h.recipient_id)?.display_name ??
                (h.recipient_id === viewerId ? "you" : h.recipient_id)}
            </p>
            {h.shared_content_visible &&
            h.context_status === "CURRENT" &&
            h.content ? (
              <>
                <p>{h.content.question}</p>
                <p>Next step: {h.content.next_step || "None specified"}</p>
                <ul>
                  {h.content.links.map((link) => {
                    const row = resolveHandoffReference(
                      e,
                      link,
                      "EXACT_PIN_AVAILABLE",
                    );
                    return (
                      <li key={handoffLinkKey(link)}>
                        {link.kind} {link.id}
                        {link.version !== null ? ` v${link.version}` : ""}{" "}
                        <button
                          type="button"
                          disabled={!row || busy}
                          onClick={() =>
                            row &&
                            onPreview(link.kind, row, {
                              id: link.id,
                              version: link.version,
                              sha256: link.sha256,
                            })
                          }
                        >
                          Open exact {link.kind}
                        </button>
                      </li>
                    );
                  })}
                </ul>
                {h.content.response && <p>Response: {h.content.response}</p>}
              </>
            ) : (
              <p>
                {h.context_status}: shared content and links are unavailable
                under the current participant context.
              </p>
            )}
            {h.status === "COMPLETED" && (
              <p>
                This completes the coordination response only. It does not
                complete testing or independent review.
              </p>
            )}
            {h.allowed_actions.length > 0 && (
              <fieldset disabled={busy || Boolean(pending) || conflict}>
                <legend>Your response</legend>
                <label>
                  Response
                  <textarea
                    aria-label={`Response for ${h.id}`}
                    maxLength={4000}
                    value={responses[h.id] ?? ""}
                    onChange={(ev) =>
                      setResponses((r) => ({ ...r, [h.id]: ev.target.value }))
                    }
                  />
                </label>
                {h.allowed_actions.map((action) => (
                  <button
                    key={action}
                    type="button"
                    disabled={action === "COMPLETE" && !responses[h.id]?.trim()}
                    onClick={() => transition(h, action)}
                  >
                    {labels[action] ?? action}
                  </button>
                ))}
              </fieldset>
            )}
          </article>
        ))
      )}
    </div>
  );
}
