import { useState } from "react";
import { request, str, type Engagement, type Row } from "./api";
export default function CustomAuthoring({
  engagement: e,
  busy,
  onCommand,
}: {
  engagement: Engagement;
  busy: boolean;
  onCommand: (kind: string, payload: Record<string, unknown>) => void;
}) {
  const configuration = e.configuration as { selections?: Row[] } | undefined;
  const selections = (configuration?.selections ?? []).filter(
    (s) => s.authoring_mode === "CUSTOM",
  );
  const [selected, setSelected] = useState(0),
    [text, setText] = useState(""),
    [control, setControl] = useState(""),
    [detail, setDetail] = useState<Record<string, unknown> | null>(null),
    [editedJSON, setEditedJSON] = useState(""),
    [error, setError] = useState(""),
    [consent, setConsent] = useState(false);
  if (!selections.length || e.phase !== "CONFIGURING") return null;
  const drafts = (e.custom_drafts ?? []) as Row[];
  return (
    <section className="panel">
      <h2>Custom scenario workbench</h2>
      <p>
        Describe the case in ordinary language. The local model produces private
        evidence recipes and playable paths; deterministic checks and a separate
        critic precede explicit instructor acceptance. The rubric remains
        professionally unvalidated.
      </p>
      {!e.permissions?.includes("instruct") ? (
        <p>
          An instructor must author and accept these custom options before
          generation.
        </p>
      ) : (
        <>
          <label>
            Custom option
            <select
              value={selected}
              onChange={(v) => {
                setSelected(Number(v.target.value));
                setText("");
              }}
            >
              {selections.map((s, i) => (
                <option key={i} value={i}>
                  {str(s.selector_id)} / {str(s.option_id)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Bound control
            <select
              value={control}
              onChange={(v) => setControl(v.target.value)}
            >
              <option value="">Select scoped control</option>
              {e.controls.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} — {str(c.title)}
                </option>
              ))}
            </select>
          </label>
          <label>
            Case intent / correction to the inspected draft
            <textarea
              value={text || str(selections[selected]?.custom_text)}
              onChange={(v) => setText(v.target.value)}
              maxLength={8000}
            />
          </label>
          <button
            disabled={busy || !control || !e.capabilities.custom_authoring}
            onClick={() =>
              onCommand("scenario.custom.author", {
                selector_id: selections[selected].selector_id,
                option_id: selections[selected].option_id,
                control_id: control,
                text: text || str(selections[selected].custom_text),
                prior_draft_id: detail
                  ? (detail.variant as Row)?.id
                  : undefined,
              })
            }
          >
            {busy
              ? "Authoring and checking…"
              : "Author and validate private draft revision"}
          </button>
          <p>
            Generation may take several minutes. Failed validation preserves a
            reviewable draft and does not install it.
          </p>
          {drafts.map((d) => (
            <div key={d.id}>
              <strong>{d.id}</strong> · {str(d.status)} · engineering{" "}
              {str(d.bounded_validation)} · critic observations{" "}
              {str(d.critic_observations)}{" "}
              <button
                disabled={busy}
                onClick={async () => {
                  try {
                    setDetail(
                      await request(
                        `/api/engagements/${e.id}/custom-drafts/${d.id}`,
                      ),
                    );
                    setEditedJSON("");
                    setConsent(false);
                    setError("");
                  } catch (ex) {
                    setError((ex as Error).message);
                  }
                }}
              >
                Inspect private draft
              </button>
              {detail && (detail.variant as Row)?.id === d.id && (
                <>
                  <details open>
                    <summary>Private draft, bindings and validation</summary>
                    <pre className="json-preview">
                      {JSON.stringify(detail, null, 2)}
                    </pre>
                  </details>
                  <details>
                    <summary>Instructor structured correction</summary>
                    <p>
                      Optional direct editing preserves a new private revision.
                      It still requires fresh deterministic checks, model
                      criticism and explicit acceptance. Describe the correction
                      in the case-intent box above.
                    </p>
                    <textarea
                      aria-label="Private scenario JSON correction"
                      rows={16}
                      value={
                        editedJSON || JSON.stringify(detail.variant, null, 2)
                      }
                      onChange={(v) => setEditedJSON(v.target.value)}
                    />
                    <button
                      disabled={busy || !control || !text.trim()}
                      onClick={() => {
                        try {
                          const variant = JSON.parse(
                            editedJSON || JSON.stringify(detail.variant),
                          );
                          onCommand("scenario.custom.edit", {
                            selector_id: d.selector_id,
                            option_id: d.option_id,
                            prior_draft_id: d.id,
                            control_id: control,
                            text,
                            variant,
                          });
                          setError("");
                        } catch (ex) {
                          setError((ex as Error).message);
                        }
                      }}
                    >
                      Validate corrected private revision
                    </button>
                  </details>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={consent}
                      onChange={(v) => setConsent(v.target.checked)}
                    />
                    I reviewed the evidence, actor/date coherence, playable
                    paths and alternatives. Accept for this scoped training
                    engagement, without professional rubric validation.
                  </label>
                  <button
                    disabled={
                      busy ||
                      !consent ||
                      d.status === "ACCEPTED" ||
                      d.bounded_validation !== "PASS" ||
                      d.critic_observations !== 0
                    }
                    onClick={() =>
                      onCommand("scenario.custom.accept", {
                        draft_id: d.id,
                        accept: true,
                      })
                    }
                  >
                    Accept scoped draft
                  </button>
                </>
              )}
            </div>
          ))}
          {error && <p role="alert">{error}</p>}
        </>
      )}
    </section>
  );
}
