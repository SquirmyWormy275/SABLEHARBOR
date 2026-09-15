import { human, str, type Engagement, type Row } from "./api";
import {
  recordedFeedback,
  reviewFeedbackTarget,
  humanResolutionTarget,
} from "./reviewFeedback";
export function ReviewFeedback({
  engagement,
  review,
  supported,
  busy,
  onRespond,
  onResolveHuman,
  viewerId,
  resolutionSupported = false,
}: {
  engagement: Engagement;
  review: Row;
  supported: boolean;
  busy: boolean;
  onRespond: (payload: Record<string, unknown>) => void;
  onResolveHuman?: (payload: Record<string, unknown>) => void;
  viewerId?: string;
  resolutionSupported?: boolean;
}) {
  const target = reviewFeedbackTarget(engagement, review.id, supported),
    entries = recordedFeedback(review);
  return (
    <section aria-label="Recorded review feedback">
      <h3>Review feedback</h3>
      <p>
        Review status: {human(str(review.status))}. Feedback status:{" "}
        {review.feedback_status
          ? human(str(review.feedback_status))
          : "None recorded"}
        .
      </p>
      {Boolean(review.latest_response_disposition) && (
        <p>
          Latest response: {human(str(review.latest_response_disposition))}.
        </p>
      )}
      <p>
        Feedback does not close a human review or change an experimental
        suggestion. Reviewer resolution is a separate action.
      </p>
      {entries.length === 0 ? (
        <p>No response history is recorded.</p>
      ) : (
        <ol>
          {entries.map((entry, i) => (
            <li key={i}>
              <article aria-label={`Recorded response ${i + 1}`}>
                <h4>
                  {entry.disposition
                    ? human(str(entry.disposition))
                    : "Recorded reviewer resolution"}
                </h4>
                <p>{str(entry.response)}</p>
                <p>
                  Recorded by {str(entry.actor)} ·{" "}
                  {str(entry.recorded_at ?? entry.simulated_at)}
                </p>
                {entry.response_workpaper_version !== undefined && (
                  <p>
                    Response workpaper version{" "}
                    {str(entry.response_workpaper_version)} · exact digest{" "}
                    <code>{str(entry.response_workpaper_version_digest)}</code>.
                  </p>
                )}
                {Boolean(entry.input_digest) && (
                  <p>
                    Original review input digest:{" "}
                    <code>{str(entry.input_digest)}</code>.
                  </p>
                )}
                {Boolean(entry.review_result_digest) && (
                  <p>
                    Original suggestion digest:{" "}
                    <code>{str(entry.review_result_digest)}</code>.
                  </p>
                )}
                {Array.isArray(entry.response_workpaper_versions) && (
                  <ul>
                    {(entry.response_workpaper_versions as Row[]).map(
                      (version, j) => (
                        <li key={j}>
                          {str(version.workpaper_id)} · version{" "}
                          {str(version.version)} ·{" "}
                          <code>{str(version.digest)}</code>
                        </li>
                      ),
                    )}
                  </ul>
                )}
              </article>
            </li>
          ))}
        </ol>
      )}
      {target.payload ? (
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            const current = reviewFeedbackTarget(
              engagement,
              review.id,
              supported,
            );
            if (current.payload) onRespond(current.payload);
          }}
        >
          Record feedback
        </button>
      ) : (
        <p>{target.reason}</p>
      )}
      {onResolveHuman &&
        humanResolutionTarget(
          engagement,
          review.id,
          viewerId,
          resolutionSupported,
        ) && (
          <div>
            <p>
              After checking the current workpaper, an independent reviewer can
              explicitly resolve this human comment. The original comment and
              responses remain recorded.
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                const payload = humanResolutionTarget(
                  engagement,
                  review.id,
                  viewerId,
                  resolutionSupported,
                );
                if (payload) onResolveHuman(payload);
              }}
            >
              Resolve human review
            </button>
          </div>
        )}
    </section>
  );
}
