import { str, type Engagement, type Row } from "./api";
import type { SourcePin } from "./meetingSources";
import { retainedPinArtifacts } from "./conversationProvenance";
export function ConversationProvenance({
  engagement: e,
  message: m,
  onPreview,
}: {
  engagement: Engagement;
  message: Row;
  onPreview: (kind: string, row: Row) => void;
}) {
  const pins = Array.isArray(m.source_records)
    ? (m.source_records as SourcePin[])
    : [];
  const citations = Array.isArray(m.source_refs)
    ? (m.source_refs.filter((x) => typeof x === "string") as string[])
    : [];
  const actions = Array.isArray(m.action_receipts)
    ? (m.action_receipts as Row[])
    : [];
  return (
    <>
      {pins.length > 0 && (
        <details>
          <summary>
            Exact source records selected for this question ({pins.length})
          </summary>
          <p>
            These are the original selected versions. They do not automatically
            follow later source changes.
          </p>
          <ul>
            {pins.map((pin, i) => {
              const artifacts = retainedPinArtifacts(e, pin);
              return (
                <li key={i}>
                  {pin.system_id} / {pin.record_id} · Version {pin.version} ·
                  SHA256 <code>{pin.sha256}</code>
                  {artifacts.map((a) => (
                    <button
                      type="button"
                      key={a.id}
                      onClick={() => onPreview("artifact", a)}
                    >
                      Open retained original {a.id}
                    </button>
                  ))}
                  {!artifacts.length && (
                    <p>
                      No matching retained original is available in this
                      workspace. A source citation does not itself collect
                      evidence.
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </details>
      )}
      {citations.length > 0 && (
        <details>
          <summary>
            Source references recorded with this reply ({citations.length})
          </summary>
          <p>
            References identify the source context used for this reply; they are
            not an assessment of evidence sufficiency.
          </p>
          <ul>
            {citations.map((id) => (
              <li key={id}>
                <code>{id}</code>
              </li>
            ))}
          </ul>
        </details>
      )}
      {actions.map((receipt, index) => {
        const linked = e.requests.find((r) => r.id === receipt.request_id);
        return (
          <div className="action-receipt" key={index}>
            <p>
              {receipt.executed === true
                ? "Executed scoped action"
                : receipt.executed === false
                  ? "Action not executed"
                  : "Recorded action"}
              : {str(receipt.kind)} · {str(receipt.status)}
            </p>
            <p>Authority: {str(receipt.authority) || "Not recorded"}</p>
            {Boolean(receipt.reason) && (
              <p>Recorded reason: {str(receipt.reason)}</p>
            )}
            {linked ? (
              <button
                type="button"
                onClick={() => onPreview("request", linked)}
              >
                Open affected request {linked.id}
              </button>
            ) : (
              Boolean(receipt.request_id) && (
                <p>
                  Request {str(receipt.request_id)} is unavailable in this
                  workspace.
                </p>
              )
            )}
          </div>
        );
      })}
    </>
  );
}
