import { useEffect, useRef, useState } from "react";
import type { Engagement } from "./api";
import {
  consultationAuthority,
  consultationInputs,
  eligibleQuestions,
  validConsultation,
} from "./companyConsultation";
import type { Consultation } from "./companyConsultation";
type Props = {
  engagement: Engagement;
  viewerId: string;
  targetMeetingId: string;
  value: Consultation | null;
  onChange: (value: Consultation | null) => void;
  disabled?: boolean;
};
export function MeetingConsultation(props: Props) {
  const key = consultationAuthority(
    props.engagement,
    props.viewerId,
    props.targetMeetingId,
  );
  const prior = useRef(key);
  useEffect(() => {
    if (prior.current !== key) {
      prior.current = key;
      props.onChange(null);
    }
  }, [key]);
  return (
    <Picker
      key={key}
      {...props}
      value={prior.current === key ? props.value : null}
    />
  );
}
function Picker({
  engagement: e,
  targetMeetingId,
  value,
  onChange,
  disabled,
}: Props) {
  const [kind, setKind] = useState<Consultation["kind"]>(
      value?.kind ?? "REFERRAL",
    ),
    [search, setSearch] = useState(""),
    [questionId, setQuestionId] = useState(""),
    [responseId, setResponseId] = useState("");
  const inputs = consultationInputs(e),
    questions = eligibleQuestions(e, targetMeetingId, kind);
  const current = value && validConsultation(e, targetMeetingId, value);
  useEffect(() => {
    if (value && !current) onChange(null);
  }, [e.revision, inputs.status, value, current]);
  const matches = questions.filter((q) =>
    [q.content, q.meeting_title, q.person_id, q.ref.message_id].some((t) =>
      t.toLowerCase().includes(search.toLowerCase()),
    ),
  );
  const chosen = questions.find(
    (q) => q.ref.meeting_id + ":" + q.ref.message_id === questionId,
  );
  const displayed = matches.slice(0, 40);
  if (chosen && !displayed.includes(chosen)) displayed.unshift(chosen);
  const response = chosen?.responses.find(
    (r) => r.ref.message_id === responseId,
  );
  return (
    <details className="panel">
      <summary>Refer an earlier question or request a correction</summary>
      <p>
        You author the request in the question box. Selecting a prior exchange
        supplies exact references; it does not contact anyone until you send the
        question.
      </p>
      {inputs.status !== "AVAILABLE" && (
        <p role="status">
          Earlier conversation references unavailable: {inputs.status}.
        </p>
      )}
      {value && current && (
        <div>
          <p>
            Selected{" "}
            {value.kind === "REFERRAL" ? "referral" : "correction request"}:{" "}
            {value.question_ref.message_id}
            {value.response_ref
              ? ` / reply ${value.response_ref.message_id}`
              : ""}
          </p>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onChange(null)}
          >
            Remove consultation reference
          </button>
        </div>
      )}
      <fieldset disabled={disabled || inputs.status !== "AVAILABLE"}>
        <legend>Choose an existing exchange</legend>
        <label>
          Request type
          <select
            aria-label="Consultation request type"
            value={kind}
            onChange={(ev) => {
              setKind(ev.target.value as Consultation["kind"]);
              setQuestionId("");
              setResponseId("");
            }}
          >
            <option value="REFERRAL">Ask a different company contact</option>
            <option value="CORRECTION_REQUEST">
              Request correction of an earlier reply
            </option>
          </select>
        </label>
        <label>
          Find earlier question
          <input
            aria-label="Find earlier question"
            value={search}
            onChange={(ev) => setSearch(ev.target.value)}
          />
        </label>
        <p>
          {matches.length} matching questions; showing up to 40.{" "}
          {kind === "REFERRAL"
            ? "Questions from this contact are excluded."
            : "Choose the exact earlier reply to challenge."}
        </p>
        <label>
          Earlier question
          <select
            aria-label="Earlier consultation question"
            value={questionId}
            onChange={(ev) => {
              setQuestionId(ev.target.value);
              setResponseId("");
            }}
          >
            <option value="">Choose a question</option>
            {displayed.map((q) => (
              <option
                key={q.ref.meeting_id + q.ref.message_id}
                value={q.ref.meeting_id + ":" + q.ref.message_id}
              >
                {q.meeting_title} · {q.ref.message_id} ·{" "}
                {q.content.slice(0, 110)}
              </option>
            ))}
          </select>
        </label>
        {chosen && (
          <>
            <blockquote>{chosen.content}</blockquote>
            <p>
              Original contact: {chosen.person_id} · question SHA256{" "}
              <code>{chosen.ref.sha256}</code>
            </p>
            <label>
              Earlier company reply
              <select
                aria-label="Earlier consultation response"
                value={responseId}
                onChange={(ev) => setResponseId(ev.target.value)}
              >
                <option value="">
                  {kind === "REFERRAL"
                    ? "No reply reference (optional)"
                    : "Choose a reply (required)"}
                </option>
                {chosen.responses.map((r) => (
                  <option key={r.ref.message_id} value={r.ref.message_id}>
                    {r.ref.message_id} · {r.content.slice(0, 110)}
                  </option>
                ))}
              </select>
            </label>
            {response && (
              <>
                <blockquote>{response.content}</blockquote>
                <p>
                  Statement by {response.person_id} · reply SHA256{" "}
                  <code>{response.ref.sha256}</code>
                </p>
              </>
            )}
          </>
        )}
        <button
          type="button"
          disabled={!chosen || (kind === "CORRECTION_REQUEST" && !response)}
          onClick={() => {
            if (chosen)
              onChange({
                kind,
                question_ref: chosen.ref,
                response_ref: response?.ref ?? null,
              });
          }}
        >
          Use exact consultation references
        </button>
      </fieldset>
      <p>
        The recipient uses their existing authorized source context. A referral
        does not expand their knowledge or collect new evidence.
      </p>
    </details>
  );
}
