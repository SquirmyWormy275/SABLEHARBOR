import { useEffect, useRef, useState } from "react";
import { request, ApiError, type Engagement } from "./api";
import {
  assistanceContext,
  assistancePointer,
  previewMatches,
  validateAssistanceDraft,
  type AssistanceDraft,
  type AssistanceOptions,
  type ReleasePreview,
  type Pointer,
} from "./instructorAssistance";
import "./instructorAssistance.css";
import { DebriefDocument, DebriefExport } from "./DebriefDocument";
import type { SelectedDebrief } from "./instructorDebrief";
type Metadata = {
  release_id: string;
  status: string;
  delivered: boolean;
  acknowledged: boolean;
  recipient_id?: string;
  stage?: string;
  preview_id?: string;
};
type Content = {
  release_id: string;
  release_sha256: string;
  content: {
    stage: string;
    text: string;
    pointers: Pointer[];
    document?: SelectedDebrief;
  };
  pre_release_revision: number;
  understanding: string;
};
export function InstructorAssistance({
  engagement,
  viewerId,
  supported,
  mode,
  onOpenPointer,
  onReloadContext,
}: {
  engagement: Engagement;
  viewerId: string;
  supported: boolean;
  mode: "instructor" | "learner";
  onOpenPointer?: (p: Pointer) => void;
  onReloadContext?: () => Promise<unknown>;
}) {
  if (
    !supported ||
    !engagement.permissions?.includes(
      mode === "instructor" ? "instruct" : "learn",
    )
  )
    return null;
  return (
    <AssistancePanel
      key={assistanceContext(engagement, viewerId) + mode}
      e={engagement}
      actor={viewerId}
      mode={mode}
      onOpenPointer={onOpenPointer}
      onReloadContext={onReloadContext}
    />
  );
}
function AssistancePanel({
  e,
  actor,
  mode,
  onOpenPointer,
  onReloadContext,
}: {
  e: Engagement;
  actor: string;
  mode: "instructor" | "learner";
  onOpenPointer?: (p: Pointer) => void;
  onReloadContext?: () => Promise<unknown>;
}) {
  const instructor = mode === "instructor",
    base = `/api/engagements/${encodeURIComponent(e.id)}`,
    route = instructor ? "/instructor-releases" : "/assistance";
  const [options, setOptions] = useState<AssistanceOptions | null>(null),
    [history, setHistory] = useState<Metadata[]>([]),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [draft, setDraft] = useState<AssistanceDraft>({
      recipient_id: "",
      expected_revision: e.revision,
      stage: "HINT",
      text: "",
      pointers: [],
    }),
    [preview, setPreview] = useState<ReleasePreview | null>(null),
    [content, setContent] = useState<Content | null>(null),
    [search, setSearch] = useState(""),
    [pointerKind, setPointerKind] = useState<"task" | "artifact">("task"),
    [pointerId, setPointerId] = useState(""),
    [revokeId, setRevokeId] = useState(""),
    [reason, setReason] = useState("");
  const [historySearch, setHistorySearch] = useState(""),
    [historyPage, setHistoryPage] = useState(0);
  const matchedHistory = history.filter((r) =>
    (r.release_id + " " + (r.recipient_id ?? "") + " " + r.status)
      .toLowerCase()
      .includes(historySearch.toLowerCase()),
  );
  const [contextUnavailable, setContextUnavailable] = useState(false);
  const historyRequest = useRef(0);
  const alive = useRef(true),
    generation = useRef(0),
    commands = useRef(new Map<string, string>());
  const commandId = (action: unknown) => {
    const key = JSON.stringify(action);
    if (!commands.current.has(key))
      commands.current.set(key, crypto.randomUUID());
    return commands.current.get(key)!;
  };
  const load = async () => {
    const n = ++historyRequest.current;
    const rows = await request<Metadata[]>(base + route);
    if (alive.current && n === historyRequest.current) {
      setHistory(rows);
      setContent((current) =>
        current &&
        rows.some(
          (r) => r.release_id === current.release_id && r.status === "RELEASED",
        )
          ? current
          : null,
      );
    }
  };
  useEffect(() => {
    alive.current = true;
    void (async () => {
      try {
        if (instructor) {
          const o = await request<AssistanceOptions>(base + route + "/options");
          if (!alive.current) return;
          if (o.engagement_id !== e.id || o.revision !== e.revision)
            throw Error(
              "Options belong to a changed engagement. Refresh before preparing assistance.",
            );
          setOptions(o);
          setContextUnavailable(false);
        }
        await load();
      } catch (err) {
        if (alive.current) {
          setError((err as Error).message);
          setContextUnavailable(true);
        }
      }
    })();
    return () => {
      alive.current = false;
      generation.current++;
    };
  }, []);
  const edit = (patch: Partial<AssistanceDraft>) => {
    generation.current++;
    setPreview(null);
    setDraft({ ...draft, ...patch });
    setError("");
    setNotice("");
  };
  const action = async (fn: () => Promise<void>) => {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (err) {
      if (alive.current) {
        setError((err as Error).message);
        setContent(null);
        if (err instanceof ApiError && [401, 403, 409].includes(err.status)) {
          setPreview(null);
          setOptions(null);
          setContextUnavailable(true);
        }
      }
    } finally {
      if (alive.current) setBusy(false);
    }
  };
  const pointerLabel = (p: Pointer) =>
    p.kind === "task"
      ? (options?.tasks.find((r) => r.id === p.id)?.title ??
        e.tasks?.find((r) => r.id === p.id)?.title ??
        p.id)
      : (options?.artifacts.find((r) => r.id === p.id)?.name ??
        e.artifacts?.find((r) => r.id === p.id)?.name ??
        p.id);
  const pointers = options
    ? pointerKind === "task"
      ? options.tasks.map((p) => ({ ...p, label: p.title }))
      : options.artifacts.map((p) => ({ ...p, label: p.name }))
    : [];
  const matches = pointers.filter((p) =>
    (p.id + " " + p.label).toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <section
      className="instructor-assistance"
      aria-label={
        instructor
          ? "Instructor assistance release"
          : "My instructor assistance"
      }
    >
      <h2>
        {instructor
          ? "Instructor assistance release"
          : "My instructor assistance"}
      </h2>
      <p>
        {instructor
          ? "Prepare a message for one named learner. Preview and confirmation are separate; no Key content is copied automatically."
          : "Released assistance is listed without opening its message. Opening records delivery; acknowledgment does not establish understanding."}
      </p>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      {instructor && !options && contextUnavailable && (
        <p>
          Reload the engagement before preparing assistance. Refreshing history
          alone does not restore authoring context.
          {onReloadContext && (
            <button
              disabled={busy}
              onClick={() =>
                void action(async () => {
                  await onReloadContext();
                  if (!alive.current) return;
                  const o = await request<AssistanceOptions>(
                    base + route + "/options",
                  );
                  if (!alive.current) return;
                  if (o.engagement_id !== e.id || o.revision !== e.revision)
                    throw Error(
                      "Engagement changed; reopen the review workspace.",
                    );
                  setOptions(o);
                  setContextUnavailable(false);
                  await load();
                })
              }
            >
              Reload engagement context
            </button>
          )}
        </p>
      )}
      <div className="assistance-compose">
        {instructor && options && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              void action(async () => {
                const d = validateAssistanceDraft(draft, options),
                  token = ++generation.current;
                const result = await request<ReleasePreview>(
                  base + route + "/preview",
                  "POST",
                  d,
                );
                if (!alive.current || token !== generation.current) return;
                if (!previewMatches(result, d, e, actor))
                  throw Error(
                    "Preview does not match the current recipient and exact selected content.",
                  );
                setPreview(result);
              });
            }}
          >
            <fieldset disabled={busy}>
              <legend>Author assistance</legend>
              <label>
                Named assistance recipient
                <select
                  aria-label="Named assistance recipient"
                  required
                  value={draft.recipient_id}
                  onChange={(x) => edit({ recipient_id: x.target.value })}
                >
                  <option value="">Choose learner</option>
                  {options.recipients.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} · {r.id}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Assistance stage
                <select
                  aria-label="Assistance stage"
                  value={draft.stage}
                  onChange={(x) =>
                    edit({
                      stage: x.target.value as AssistanceDraft["stage"],
                      pointers: [],
                    })
                  }
                >
                  <option value="HINT">Hint</option>
                  <option value="POINTER">
                    Pointer to authorized original or procedure
                  </option>
                </select>
              </label>
              <label>
                Exact assistance message
                <textarea
                  required
                  maxLength={4000}
                  value={draft.text}
                  onChange={(x) => edit({ text: x.target.value })}
                />
              </label>
              {draft.stage === "POINTER" && (
                <>
                  <label>
                    Pointer type
                    <select
                      aria-label="Pointer type"
                      value={pointerKind}
                      onChange={(x) => {
                        edit({});
                        setPointerKind(x.target.value as "task" | "artifact");
                        setPointerId("");
                      }}
                    >
                      <option value="task">Procedure</option>
                      <option value="artifact">Retained original</option>
                    </select>
                  </label>
                  <label>
                    Find assistance pointer
                    <input
                      type="search"
                      value={search}
                      onChange={(x) => {
                        edit({});
                        setSearch(x.target.value);
                      }}
                    />
                  </label>
                  <p>
                    {matches.length} matches; showing up to 50 choices. Add at
                    most four pointers.
                  </p>
                  <label>
                    Exact assistance pointer
                    <select
                      aria-label="Exact assistance pointer"
                      value={pointerId}
                      onChange={(x) => {
                        edit({});
                        setPointerId(x.target.value);
                      }}
                    >
                      <option value="">Choose pointer</option>
                      {matches.slice(0, 50).map((p) => (
                        <option value={p.id} key={p.id}>
                          {p.label} · {p.id}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    disabled={!pointerId || draft.pointers.length >= 4}
                    onClick={() => {
                      const p = pointers.find((p) => p.id === pointerId);
                      if (
                        p &&
                        !draft.pointers.some(
                          (r) => r.kind === pointerKind && r.id === p.id,
                        )
                      )
                        edit({
                          pointers: [
                            ...draft.pointers,
                            { kind: pointerKind, id: p.id, sha256: p.sha256 },
                          ],
                        });
                    }}
                  >
                    Add exact pointer
                  </button>
                </>
              )}
              {draft.pointers.map((p, n) => (
                <p key={p.kind + p.id}>
                  {p.kind === "task" ? "Procedure" : "Original"}:{" "}
                  {String(pointerLabel(p))} · {p.id}
                  <button
                    type="button"
                    onClick={() =>
                      edit({
                        pointers: draft.pointers.filter((_, i) => i !== n),
                      })
                    }
                  >
                    Remove pointer {p.id}
                  </button>
                </p>
              ))}
              <button type="submit">Preview exact assistance</button>
            </fieldset>
          </form>
        )}
        {preview && instructor && (
          <section
            className="assistance-preview"
            aria-label="Exact assistance preview"
          >
            <h3>Not yet released</h3>
            <p>
              Recipient:{" "}
              {
                options?.recipients.find(
                  (r) => r.id === preview.preview.recipient_id,
                )?.name
              }{" "}
              · {preview.preview.recipient_id}
            </p>
            <p>Stage: {preview.preview.content.stage}</p>
            <blockquote>{preview.preview.content.text}</blockquote>
            {preview.preview.content.pointers.map((p) => (
              <p key={p.kind + p.id}>
                {p.kind === "task" ? "Procedure" : "Original"}:{" "}
                {String(pointerLabel(p))} · {p.id}
              </p>
            ))}
            <p>
              Preview expires{" "}
              {new Date(preview.preview.expires_at).toLocaleString()}.
            </p>
            <details>
              <summary>Source and version details</summary>
              <p>Preview digest: {preview.preview_sha256}</p>
              <p>Exact expiry: {preview.preview.expires_at}</p>
              <p>Engagement revision: {preview.preview.revision}</p>
              {preview.preview.content.pointers.map((p) => (
                <p key={p.kind + p.id}>
                  {p.kind} {p.id} · SHA256 {p.sha256}
                </p>
              ))}
            </details>
            <button
              disabled={busy || !previewMatches(preview, draft, e, actor)}
              onClick={() =>
                void action(async () => {
                  if (!previewMatches(preview, draft, e, actor))
                    throw Error("Prepare a new preview before confirming.");
                  const payload = {
                    preview_id: preview.preview.id,
                    preview_sha256: preview.preview_sha256,
                    command_id: commandId([
                      "confirm",
                      preview.preview.id,
                      preview.preview_sha256,
                    ]),
                  };
                  await request(base + route, "POST", payload);
                  if (!alive.current) return;
                  setPreview(null);
                  setNotice(
                    "Released to the named learner. Delivery is recorded only when they explicitly open it.",
                  );
                  await load();
                })
              }
            >
              Confirm release to named learner
            </button>
          </section>
        )}
      </div>
      <h3>{instructor ? "Release history" : "Available assistance"}</h3>
      <button
        disabled={busy}
        onClick={() =>
          void action(async () => {
            setContent(null);
            await load();
          })
        }
      >
        Refresh assistance history
      </button>
      {history.length === 0 && <p>No release metadata available.</p>}
      <label>
        Find assistance history
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
        {matchedHistory.length} matching releases · page {historyPage + 1}
      </p>
      <button
        disabled={historyPage === 0}
        onClick={() => setHistoryPage(historyPage - 1)}
      >
        Previous releases
      </button>
      <button
        disabled={(historyPage + 1) * 20 >= matchedHistory.length}
        onClick={() => setHistoryPage(historyPage + 1)}
      >
        Next releases
      </button>
      {matchedHistory
        .slice(historyPage * 20, historyPage * 20 + 20)
        .map((r) => (
          <article key={r.release_id}>
            <p>
              {r.release_id}
              {r.recipient_id ? ` · Recipient ${r.recipient_id}` : ""} ·{" "}
              {r.status} · Delivered: {String(r.delivered)} · Acknowledged:{" "}
              {String(r.acknowledged)}
            </p>
            {!instructor && r.status === "RELEASED" && (
              <button
                disabled={busy}
                onClick={() =>
                  void action(async () => {
                    setContent(null);
                    const value = await request<Content>(
                      base + route + "/" + encodeURIComponent(r.release_id),
                    );
                    if (!alive.current) return;
                    if (value.release_id !== r.release_id)
                      throw Error("Assistance identity changed.");
                    setContent(value);
                    await load();
                  })
                }
              >
                Open assistance {r.release_id}
              </button>
            )}
            {instructor && r.status !== "REVOKED" && (
              <button
                disabled={busy}
                onClick={() => {
                  setRevokeId(r.release_id);
                  setReason("");
                }}
              >
                Revoke assistance {r.release_id}
              </button>
            )}
          </article>
        ))}
      {content && !instructor && (
        <section
          className="assistance-preview"
          aria-label="Opened instructor assistance"
        >
          <h3>{content.content.stage}</h3>
          {content.content.stage === "EXPLANATION" &&
          content.content.document ? (
            <>
              <DebriefDocument
                document={content.content.document}
                engagement={e}
                onOpenPointer={onOpenPointer}
              />
              <DebriefExport
                engagement={e}
                viewerId={actor}
                releaseId={content.release_id}
                releaseSha256={content.release_sha256}
              />
            </>
          ) : (
            <blockquote>{content.content.text}</blockquote>
          )}
          {content.content.pointers.map((p) => (
            <p key={p.kind + p.id}>
              {p.kind === "task" ? "Procedure" : "Original"}:{" "}
              {String(pointerLabel(p))} · {p.id}
              {onOpenPointer && assistancePointer(e, p) ? (
                <button
                  onClick={() => {
                    if (assistancePointer(e, p)) onOpenPointer(p);
                  }}
                >
                  {p.kind === "task"
                    ? "Open procedure"
                    : "Open retained original"}{" "}
                  {p.id}
                </button>
              ) : (
                <span>
                  {" "}
                  · Exact pointer navigation unavailable in this workspace
                  snapshot.
                </span>
              )}
            </p>
          ))}
          <details>
            <summary>Source and version details</summary>
            <p>
              Pre-release revision: {content.pre_release_revision} · Release
              SHA256: {content.release_sha256}
            </p>
            {content.content.pointers.map((p) => (
              <p key={p.kind + p.id}>
                {p.kind} {p.id} · SHA256 {p.sha256}
              </p>
            ))}
          </details>
          <p>
            Instructor-authored assistance; no verified finding or professional
            acceptance is asserted.
          </p>
          <button
            disabled={
              busy ||
              history.some(
                (r) => r.release_id === content.release_id && r.acknowledged,
              )
            }
            onClick={() =>
              void action(async () => {
                await request(
                  base +
                    route +
                    "/" +
                    encodeURIComponent(content.release_id) +
                    "/acknowledge",
                  "POST",
                  {
                    release_id: content.release_id,
                    command_id: commandId(["acknowledge", content.release_id]),
                  },
                );
                if (!alive.current) return;
                setNotice(
                  "Acknowledgment recorded. Understanding is not inferred.",
                );
                await load();
              })
            }
          >
            Acknowledge opened assistance
          </button>
          <button onClick={() => setContent(null)}>
            Hide assistance content
          </button>
        </section>
      )}
      {instructor && revokeId && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void action(async () => {
              if (!reason.trim()) throw Error("Provide a revocation reason.");
              await request(
                base + route + "/" + encodeURIComponent(revokeId) + "/revoke",
                "POST",
                {
                  release_id: revokeId,
                  command_id: commandId(["revoke", revokeId, reason]),
                  reason,
                },
              );
              if (!alive.current) return;
              setRevokeId("");
              setNotice("Revoked. Earlier delivery history remains retained.");
              await load();
            });
          }}
        >
          <fieldset disabled={busy}>
            <legend>Revoke {revokeId}</legend>
            <label>
              Revocation reason
              <textarea
                required
                maxLength={4000}
                value={reason}
                onChange={(x) => setReason(x.target.value)}
              />
            </label>
            <button type="submit">Confirm revocation</button>
            <button type="button" onClick={() => setRevokeId("")}>
              Cancel revocation
            </button>
          </fieldset>
        </form>
      )}
    </section>
  );
}
