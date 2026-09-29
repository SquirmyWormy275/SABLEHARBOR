import { useState } from "react";
import type { Bootstrap, Engagement, Row } from "./api";
import { str } from "./api";
import { Modal, Table } from "./components";
export default function ReviewDialog({
  engagement: e,
  bootstrap,
  busy,
  onCommand,
  onClose,
}: {
  engagement: Engagement;
  bootstrap: Bootstrap;
  busy: boolean;
  onCommand: (
    kind: string,
    payload: Record<string, unknown>,
  ) => Promise<Engagement | undefined>;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<string[]>(
      e.workpapers.slice(0, 20).map((w) => w.id),
    ),
    [inputID, setInputID] = useState(""),
    [consent, setConsent] = useState(false),
    [error, setError] = useState("");
  const input = e.reviews.find((r) => r.id === inputID);
  const sources = Array.isArray(input?.sources) ? (input.sources as Row[]) : [];
  const provider = bootstrap.providers?.inference;
  return (
    <Modal
      title="Experimental AI review · inspect the inputs"
      onClose={onClose}
    >
      <div className="experimental">
        <strong>
          Human review remains primary. No whole-audit grade is produced.
        </strong>
        <p>
          The local model may misread evidence or make unsupported judgments. It
          produces two separate reviews: a private instructor review using five
          scoped reference layers, and learner feedback using only the listed
          observable sources. Private facts and reviewer prose are never sent to
          the learner-feedback pass. No feedback is used for training automatically.
        </p>
        <p>
          Provider: {str(provider?.model ?? "Local model")} ·{" "}
          {str(provider?.data_destination ?? "Local process only")}
        </p>
      </div>
      {error && <p role="alert">{error}</p>}
      {!input ? (
        <>
          <fieldset>
            <legend>Select up to 20 submitted workpapers</legend>
            {e.workpapers.map((w) => (
              <label className="check" key={w.id}>
                <input
                  type="checkbox"
                  checked={selected.includes(w.id)}
                  disabled={!selected.includes(w.id) && selected.length >= 20}
                  onChange={(event) =>
                    setSelected(
                      event.target.checked
                        ? [...selected, w.id]
                        : selected.filter((id) => id !== w.id),
                    )
                  }
                />
                {str(w.title)} · {w.id}
              </label>
            ))}
          </fieldset>
          <button
            disabled={busy || !selected.length}
            onClick={async () => {
              setError("");
              try {
                const state = await onCommand("review.prepare", {
                  workpaper_ids: selected,
                });
                const record = state?.reviews
                  .filter((r) => r.kind === "EXPERIMENTAL_INPUT")
                  .at(-1);
                if (record) setInputID(record.id);
              } catch (err) {
                setError((err as Error).message);
              }
            }}
          >
            Prepare exact source list
          </button>
        </>
      ) : (
        <>
          <p>
            {sources.length} source locations included;{" "}
            {str(input.omitted_source_locations)} omitted by the context limit.
            Unsupported file formats remain available for human review.
            The instructor channel uses authority, policy, scenario, rubric and
            observable-work layers. Context omissions remain recorded with the
            consent-bound private input digest; omitted material is not claimed reviewed.
          </p>
          <Table
            rows={sources}
            columns={[
              { key: "id", label: "Source reference" },
              { key: "locator", label: "Original location" },
              { key: "text", label: "Text sent to the local model" },
            ]}
          />
          <h3>Factual checks · separate from AI judgments</h3>
          <p>These compare explicit recorded inputs. A supported calculation or
            identifier does not establish population completeness or control
            effectiveness. Missing inputs remain not observable.</p>
          <Table
            rows={(Array.isArray(input.checks) ? input.checks as Row[] : []).map(
              (check, index) => ({...check, id: `${check.id}:${check.check}:${index}`})
            )}
            columns={[
              {key: "check", label: "Factual check"},
              {key: "status", label: "Result"},
              {key: "detail", label: "Inputs and limits"},
            ]}
          />
          <label className="check">
            <input
              type="checkbox"
              checked={consent}
              onChange={(event) => setConsent(event.target.checked)}
            />
            I reviewed this source list and understand that the suggestions are
            experimental and require human judgment.
          </label>
          <div className="actions">
            <button
              onClick={() => {
                setInputID("");
                setConsent(false);
              }}
              disabled={busy}
            >
              Change workpapers
            </button>
            <button
              className="primary"
              disabled={!consent || busy || !e.capabilities.experimental_review}
              onClick={async () => {
                setError("");
                try {
                  await onCommand("review.experimental", {
                    experimental_consent: true,
                    input_digest: input.input_digest,
                    workpaper_ids: input.workpaper_ids,
                  });
                  onClose();
                } catch (err) {
                  setError((err as Error).message);
                }
              }}
            >
              Request experimental review
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
