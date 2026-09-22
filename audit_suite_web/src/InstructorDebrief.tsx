import { useEffect, useRef, useState } from "react";
import { ApiError, request, type Engagement } from "./api";
import { DebriefDocument, DebriefExport } from "./DebriefDocument";
import { assistanceContext } from "./instructorAssistance";
import {
  debriefPin,
  debriefPreviewMatches,
  type DebriefPreview,
  emptyDebriefSection,
  validateDebriefDraft,
  type DebriefDraft,
  type DebriefOptions,
  type DebriefSection,
} from "./instructorDebrief";

export function InstructorDebrief({
  engagement,
  viewerId,
  supported,
}: {
  engagement: Engagement;
  viewerId: string;
  supported: boolean;
}) {
  if (!supported || !engagement.permissions?.includes("instruct")) return null;
  return (
    <Composer
      key={assistanceContext(engagement, viewerId)}
      e={engagement}
      actor={viewerId}
    />
  );
}
function Composer({ e, actor }: { e: Engagement; actor: string }) {
  const base = `/api/engagements/${encodeURIComponent(e.id)}/instructor-releases`;
  const [options, setOptions] = useState<DebriefOptions | null>(null),
    [draft, setDraft] = useState<DebriefDraft>({
      recipient_id: "",
      expected_revision: e.revision,
      learner_revision: e.revision,
      title: "",
      sections: [emptyDebriefSection()],
      predecessor_release_id: null,
    }),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(""),
    [preview, setPreview] = useState<DebriefPreview | null>(null),
    [released, setReleased] = useState<{
      release_id: string;
      release_sha256: string;
    } | null>(null),
    [retry, setRetry] = useState(false);
  const pending = useRef<{
    preview_id: string;
    preview_sha256: string;
    command_id: string;
  } | null>(null);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const edit = (next: DebriefDraft) => {
    setPreview(null);
    setDraft(next);
    setNotice("");
  };
  const section = (index: number, patch: Partial<DebriefSection>) =>
    edit({
      ...draft,
      sections: draft.sections.map((s, i) =>
        i === index ? { ...s, ...patch } : s,
      ),
    });
  async function load() {
    setBusy(true);
    setError("");
    setPreview(null);
    setReleased(null);
    try {
      const value = await request<DebriefOptions>(base + "/debrief-options");
      if (!alive.current) return;
      if (
        value.engagement_id !== e.id ||
        value.revision !== e.revision ||
        !debriefPin(value.key_manifest_sha256)
      )
        throw Error(
          "Debrief options changed. Reload the engagement before continuing.",
        );
      setOptions(value);
    } catch (err) {
      if (alive.current) {
        setError((err as Error).message);
        setOptions(null);
      }
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  async function makePreview() {
    if (!options) return;
    setError("");
    setBusy(true);
    setPreview(null);
    setReleased(null);
    try {
      const input = validateDebriefDraft(draft, options);
      const p = await request<DebriefPreview>(
        base + "/debrief-preview",
        "POST",
        input,
      );
      if (!alive.current) return;
      if (!debriefPreviewMatches(p, input, options, e.id, actor))
        throw Error(
          "Preview does not match the exact selected debrief. Reload choices.",
        );
      setPreview(p);
    } catch (err) {
      if (alive.current) {
        setError((err as Error).message);
        if (err instanceof ApiError && [401, 403, 409].includes(err.status))
          setOptions(null);
      }
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  async function confirm() {
    if (
      !preview ||
      !options ||
      (!pending.current &&
        !debriefPreviewMatches(preview, draft, options, e.id, actor))
    )
      return;
    const body = pending.current ?? {
      preview_id: preview.preview.id,
      preview_sha256: preview.preview_sha256,
      command_id: crypto.randomUUID(),
    };
    pending.current = body;
    setBusy(true);
    setError("");
    try {
      const value = await request<{
        release_id: string;
        release_sha256: string;
        status: string;
        delivered: boolean;
      }>(base, "POST", body);
      if (!alive.current) return;
      if (
        !value.release_id ||
        !debriefPin(value.release_sha256) ||
        value.status !== "RELEASED" ||
        value.delivered !== false
      )
        throw Error(
          "Release receipt differs. Inspect release history before retrying.",
        );
      pending.current = null;
      setRetry(false);
      setReleased(value);
      setPreview(null);
      setNotice(
        "Selected explanation released to the named learner. Opening records delivery separately.",
      );
    } catch (err) {
      if (alive.current) {
        setError((err as Error).message);
        if (err instanceof ApiError && err.status >= 400 && err.status < 500) {
          pending.current = null;
          setRetry(false);
          setPreview(null);
          if ([401, 403, 409].includes(err.status)) setOptions(null);
        } else setRetry(true);
      }
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  return (
    <details className="instructor-assistance">
      <summary>Prepare a selected explanation debrief</summary>
      <p>
        Choose issues and evidence for one named learner. Review the complete
        document before releasing it.
      </p>
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}
      <button disabled={busy || retry} onClick={() => void load()}>
        Load debrief choices
      </button>
      {options && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void makePreview();
          }}
        >
          <fieldset disabled={busy || retry}>
            <legend>Selected explanation</legend>
            <label>
              Debrief recipient
              <select
                aria-label="Debrief recipient"
                required
                value={draft.recipient_id}
                onChange={(ev) =>
                  edit({ ...draft, recipient_id: ev.target.value })
                }
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
              Debrief title
              <input
                required
                maxLength={200}
                value={draft.title}
                onChange={(ev) => edit({ ...draft, title: ev.target.value })}
              />
            </label>
            <label>
              Learner history revision
              <input
                type="number"
                min={0}
                max={e.revision}
                required
                value={draft.learner_revision}
                onChange={(ev) =>
                  edit({ ...draft, learner_revision: Number(ev.target.value) })
                }
              />
            </label>
            <p>
              This revision is a historical snapshot, not an inferred
              submission.
            </p>
            <label>
              Prior explanation release ID (optional correction)
              <input
                maxLength={128}
                value={draft.predecessor_release_id ?? ""}
                onChange={(ev) =>
                  edit({
                    ...draft,
                    predecessor_release_id: ev.target.value || null,
                  })
                }
              />
            </label>
            <p>
              A correction preserves its predecessor; it does not revoke or
              rewrite earlier delivery.
            </p>
            {draft.sections.map((s, index) => (
              <fieldset key={index}>
                <legend>Section {index + 1}</legend>
                <label>
                  Section {index + 1} issues
                  <select
                    aria-label={`Section ${index + 1} issues`}
                    multiple
                    value={s.issue_ids}
                    onChange={(ev) => {
                      const ids = Array.from(
                        ev.target.selectedOptions,
                        (x) => x.value,
                      );
                      section(index, {
                        issue_ids: ids,
                        expectation_ids: s.expectation_ids.filter((id) =>
                          options.expectations
                            .find((x) => x.id === id)
                            ?.issue_ids.every((i) => ids.includes(i)),
                        ),
                      });
                    }}
                  >
                    {options.issues.map((i) => (
                      <option key={i.id} value={i.id}>
                        {i.title} · {i.id}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Section {index + 1} expectations
                  <select
                    aria-label={`Section ${index + 1} expectations`}
                    multiple
                    value={s.expectation_ids}
                    onChange={(ev) =>
                      section(index, {
                        expectation_ids: Array.from(
                          ev.target.selectedOptions,
                          (x) => x.value,
                        ),
                      })
                    }
                  >
                    {options.expectations
                      .filter((x) =>
                        x.issue_ids.every((id) => s.issue_ids.includes(id)),
                      )
                      .map((i) => (
                        <option key={i.id} value={i.id}>
                          {i.title} · {i.id}
                        </option>
                      ))}
                  </select>
                </label>
                <label>
                  Section {index + 1} explanation
                  <textarea
                    required
                    maxLength={4000}
                    value={s.explanation}
                    onChange={(ev) =>
                      section(index, { explanation: ev.target.value })
                    }
                  />
                </label>
                <label>
                  Section {index + 1} limitations
                  <textarea
                    required
                    maxLength={4000}
                    value={s.limitations}
                    onChange={(ev) =>
                      section(index, { limitations: ev.target.value })
                    }
                  />
                </label>
                {s.prompts.map((p, j) => (
                  <label key={j}>
                    Section {index + 1} prompt {j + 1}
                    <textarea
                      required
                      maxLength={1000}
                      aria-label={`Section ${index + 1} prompt ${j + 1}`}
                      value={p}
                      onChange={(ev) =>
                        section(index, {
                          prompts: s.prompts.map((v, k) =>
                            k === j ? ev.target.value : v,
                          ),
                        })
                      }
                    />
                    <button
                      type="button"
                      onClick={() =>
                        section(index, {
                          prompts: s.prompts.filter((_, k) => k !== j),
                        })
                      }
                    >
                      Remove prompt {j + 1}
                    </button>
                  </label>
                ))}
                <button
                  type="button"
                  disabled={s.prompts.length >= 8}
                  onClick={() =>
                    section(index, { prompts: [...s.prompts, ""] })
                  }
                >
                  Add prompt to section {index + 1}
                </button>
                <label>
                  Annotate original in section {index + 1}
                  <select
                    aria-label={`Annotate original in section ${index + 1}`}
                    value=""
                    onChange={(ev) => {
                      const a = options.artifacts.find(
                        (x) => x.id === ev.target.value,
                      );
                      if (a)
                        section(index, {
                          annotations: [
                            ...s.annotations,
                            {
                              artifact_id: a.id,
                              sha256: a.sha256,
                              note: "",
                              locator: null,
                              attach: false,
                            },
                          ],
                        });
                    }}
                  >
                    <option value="">Choose exact retained original</option>
                    {options.artifacts
                      .filter(
                        (a) =>
                          !s.annotations.some((x) => x.artifact_id === a.id),
                      )
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.title} · {a.id}
                        </option>
                      ))}
                  </select>
                </label>
                {s.annotations.map((a, j) => (
                  <fieldset key={a.artifact_id}>
                    <legend>Original {a.artifact_id}</legend>
                    <p>SHA256 {a.sha256}</p>
                    <label>
                      Annotation {index + 1}.{j + 1}
                      <textarea
                        required
                        maxLength={1000}
                        value={a.note}
                        onChange={(ev) =>
                          section(index, {
                            annotations: s.annotations.map((v, k) =>
                              k === j ? { ...v, note: ev.target.value } : v,
                            ),
                          })
                        }
                      />
                    </label>
                    <label>
                      Locator type for {a.artifact_id}
                      <select
                        aria-label={`Locator type for ${a.artifact_id}`}
                        value={a.locator?.kind ?? ""}
                        onChange={(ev) =>
                          section(index, {
                            annotations: s.annotations.map((v, k) =>
                              k === j
                                ? {
                                    ...v,
                                    locator: ev.target.value
                                      ? {
                                          kind: ev.target.value as
                                            | "PAGE"
                                            | "LINE"
                                            | "CELL"
                                            | "TIME"
                                            | "OTHER",
                                          value: v.locator?.value ?? "",
                                        }
                                      : null,
                                  }
                                : v,
                            ),
                          })
                        }
                      >
                        <option value="">No locator</option>
                        {["PAGE", "LINE", "CELL", "TIME", "OTHER"].map((v) => (
                          <option key={v} value={v}>
                            {v}
                          </option>
                        ))}
                      </select>
                    </label>
                    {a.locator && (
                      <label>
                        Locator value for {a.artifact_id}
                        <input
                          required
                          maxLength={200}
                          value={a.locator.value}
                          onChange={(ev) =>
                            section(index, {
                              annotations: s.annotations.map((v, k) =>
                                k === j && v.locator
                                  ? {
                                      ...v,
                                      locator: {
                                        ...v.locator,
                                        value: ev.target.value,
                                      },
                                    }
                                  : v,
                              ),
                            })
                          }
                        />
                      </label>
                    )}
                    <p>
                      Locators are instructor-supplied references, not
                      independently verified matches.
                    </p>
                    <label>
                      <input
                        type="checkbox"
                        checked={a.attach}
                        onChange={(ev) =>
                          section(index, {
                            annotations: s.annotations.map((v, k) =>
                              k === j ? { ...v, attach: ev.target.checked } : v,
                            ),
                          })
                        }
                      />
                      Include these original bytes in portable export
                    </label>
                    <button
                      type="button"
                      onClick={() =>
                        section(index, {
                          annotations: s.annotations.filter((_, k) => k !== j),
                        })
                      }
                    >
                      Remove original {a.artifact_id}
                    </button>
                  </fieldset>
                ))}
                <button
                  type="button"
                  disabled={draft.sections.length === 1}
                  onClick={() =>
                    edit({
                      ...draft,
                      sections: draft.sections.filter((_, i) => i !== index),
                    })
                  }
                >
                  Remove section {index + 1}
                </button>
              </fieldset>
            ))}
            <button
              type="button"
              disabled={draft.sections.length >= 10}
              onClick={() =>
                edit({
                  ...draft,
                  sections: [...draft.sections, emptyDebriefSection()],
                })
              }
            >
              Add section
            </button>
            <button type="submit">Preview selected debrief</button>
          </fieldset>
        </form>
      )}
      {preview && options && (
        <section aria-label="Exact debrief release preview">
          <h3>Complete preview for {preview.preview.recipient_id}</h3>
          <DebriefDocument
            document={preview.preview.content.document}
            engagement={e}
          />
          <details>
            <summary>Release preview pins</summary>
            <p>{preview.preview_sha256}</p>
            <p>Expires {preview.preview.expires_at}</p>
          </details>
          <button
            disabled={
              busy ||
              (!retry &&
                !debriefPreviewMatches(preview, draft, options, e.id, actor))
            }
            onClick={() => void confirm()}
          >
            {retry
              ? "Retry exact debrief confirmation"
              : "Confirm selected debrief release"}
          </button>
          {retry && (
            <button
              disabled={busy}
              onClick={() => {
                pending.current = null;
                setRetry(false);
                setPreview(null);
                setNotice(
                  "Pending confirmation discarded locally. Inspect release history before preparing another release.",
                );
              }}
            >
              Discard pending confirmation
            </button>
          )}
        </section>
      )}
      {released && (
        <DebriefExport
          engagement={e}
          viewerId={actor}
          releaseId={released.release_id}
          releaseSha256={released.release_sha256}
        />
      )}
    </details>
  );
}
